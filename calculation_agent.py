# calculation_agent.py
import asyncio
import logging
import json
import time
from datetime import datetime
from collections import deque
import numpy as np
import pandas as pd
import tensorflow as tf # Re-import tensorflow for tf.keras.layers.Input and optimizers
from keras.models import Sequential, load_model # Using 'keras' directly
from keras.layers import LSTM, Dense, Dropout # Using 'keras' directly
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
import joblib
import os
import zmq.asyncio
import sys
from functools import partial
import shap 

# Set up logging for CalculationAgent
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the SalpSwarmOptimizer from its dedicated file
from salp_swarm_optimizer import SalpSwarmOptimizer

# Configuration
CONFIG_FILE = "calculation_config.json"
MODEL_DIR = "lstm_model"
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.pkl")
LSTM_MODEL_PATH = os.path.join(MODEL_DIR, "lstm_model.h5")
LSTM_TRAINING_DATA_PATH = os.path.join(MODEL_DIR, "lstm_training_data.json")

# ZeroMQ Addresses (Must match Healing and MCP Agent configs)
CALC_HEAL_PUB_SUB_ADDRESS = "tcp://127.0.0.1:5556"
CALC_MCP_PUSH_PULL_ADDRESS = "tcp://127.0.0.1:5557"

MONITOR_DATA_STREAM_FILE = "calculation_agent_data_stream.json"

# --- Dataclasses ---
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional

@dataclass
class DataStreamMessageContent:
    simulation_time: float
    data_classification: str
    anomaly_level: float
    fault_progression_stage: str
    network_health_summary: Dict[str, Any]
    lstm_training_features: Dict[str, Any]
    node_count: int
    metrics: Dict[str, Any]

@dataclass
class AnomalyAlert:
    alert_id: str
    node_id: str
    detection_time: datetime
    simulation_time: float
    anomaly_score: float
    threshold: float
    description: str
    predicted_metrics: Dict[str, float]
    actual_metrics: Dict[str, float]
    source_agent: str = "calculation_agent"

# --- LSTM Model for Anomaly Detection (Keras Sequential Model) ---
class LSTMAnomalyModel(Sequential): 
    def __init__(self, input_size, hidden_size, num_layers=2, dropout_rate=0.2, sequence_length=None):
        super(LSTMAnomalyModel, self).__init__()
        # Explicitly add an Input layer to ensure model.inputs is defined for SHAP
        if sequence_length is None:
            raise ValueError("sequence_length must be provided to LSTMAnomalyModel for the Input layer.")
        
        # This is the crucial change: Define the input layer with the correct shape
        self.add(tf.keras.layers.Input(shape=(sequence_length, input_size))) 
        
        # Now, the first LSTM layer does NOT need input_shape as it infers from the Input layer
        self.add(LSTM(hidden_size, activation='relu', return_sequences=(num_layers > 1)))
        for i in range(1, num_layers):
            self.add(LSTM(hidden_size, activation='relu', return_sequences=(i < num_layers - 1)))
        self.add(Dropout(dropout_rate))
        self.add(Dense(input_size)) # Output layer for reconstruction

# --- LSTM Anomaly Detector for a Single Node ---
class LSTMAnomalyDetector:
    """
    Manages the LSTM model, data preprocessing, training, and anomaly prediction
    for a single network node.
    """
    def __init__(self, node_id, input_features_count, sequence_length=5, anomaly_threshold=0.05, save_shap_plots=True, plot_dir="shap_plots"):
        self.node_id = node_id
        self.input_features_count = input_features_count
        self.sequence_length = sequence_length
        self.anomaly_threshold = anomaly_threshold
        self.model = None
        self.scaler = MinMaxScaler()
        self.data_buffer = deque(maxlen=sequence_length)
        self.shap_explainer = None
        self.is_trained = False
        self.feature_names = None
        self.save_shap_plots = save_shap_plots
        self.plot_dir = os.path.join(plot_dir, node_id)
        self.shap_background_data = None # Store background data for SHAP base_values

        if self.save_shap_plots:
            os.makedirs(self.plot_dir, exist_ok=True)
            logger.info(f"Node {self.node_id}: SHAP plots will be saved to {self.plot_dir}")

    def build_model(self, hidden_size=64, learning_rate=0.001, num_layers=2, dropout_rate=0.2):
        """Builds and compiles the LSTM model."""
        if self.input_features_count == 0:
            raise ValueError("input_features_count must be set before building the model.")

        self.model = LSTMAnomalyModel(
            input_size=self.input_features_count,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout_rate=dropout_rate,
            sequence_length=self.sequence_length # Pass sequence_length here
        )
        self.model.compile(optimizer='adam', loss='mse') 
        logger.info(f"Node {self.node_id}: LSTM model built with hidden_size={hidden_size}, lr={learning_rate}, layers={num_layers}")

    def train_model(self, X_train, y_train, epochs=50, batch_size=32, verbose=0):
        """Trains the LSTM model using the provided training data."""
        if X_train.size == 0 or y_train.size == 0:
            logger.warning(f"Node {self.node_id}: Skipping training, X_train or y_train is empty.")
            self.is_trained = False
            return

        if not hasattr(self.scaler, 'min_') or not hasattr(self.scaler, 'scale_'): 
            flat_X_train = X_train.reshape(-1, self.input_features_count)
            self.scaler.fit(flat_X_train)
            logger.info(f"Node {self.node_id}: Scaler fitted on training data.")
        
        X_train_reshaped_for_scaler = X_train.reshape(-1, X_train.shape[-1])
        X_train_scaled_flat = self.scaler.transform(X_train_reshaped_for_scaler)
        X_train_scaled = X_train_scaled_flat.reshape(X_train.shape) 

        y_train_scaled = self.scaler.transform(y_train)

        logger.info(f"Node {self.node_id}: Training LSTM with {X_train_scaled.shape[0]} sequences...")
        history = self.model.fit(X_train_scaled, y_train_scaled, epochs=epochs, batch_size=batch_size, verbose=verbose)
        
        self.is_trained = True
        logger.info(f"Node {self.node_id}: Training complete. Last loss: {history.history['loss'][-1]:.4f}")

        # Initialize SHAP explainer after model training
        try: 
            num_background_samples = min(100, X_train_scaled.shape[0])
            background_indices = np.random.choice(X_train_scaled.shape[0], num_background_samples, replace=False)
            self.shap_background_data = X_train_scaled[background_indices] # Store for base_values

            # --- CRITICAL CHANGE: Use shap.GradientExplainer instead of DeepExplainer ---
            # GradientExplainer is generally more compatible with TensorFlow 2.x eager execution
            # and custom Keras models. It also takes the model and background data.
            self.shap_explainer = shap.GradientExplainer(self.model, self.shap_background_data)
            logger.info(f"Node {self.node_id}: SHAP GradientExplainer initialized.")
        except Exception as e:
            logger.error(f"Node {self.node_id}: Error initializing SHAP GradientExplainer: {e}", exc_info=True)
            self.shap_explainer = None


    def preprocess_input(self, new_data_point_raw: Dict[str, Any], feature_names: List[str]):
        """
        Adds a new raw data point to the internal buffer and scales the current sequence.
        
        Args:
            new_data_point_raw (dict): A dictionary of raw feature values for a single timestamp.
            feature_names (list): List of all feature names in their expected order (numerical features only).

        Returns:
            np.array or None: The scaled input sequence if buffer is full, otherwise None.
        """
        if self.feature_names is None:
            self.feature_names = feature_names 

        numerical_input = np.array([new_data_point_raw.get(f, 0.0) for f in feature_names], dtype=np.float32)

        self.data_buffer.append(numerical_input)

        if len(self.data_buffer) < self.sequence_length:
            return None

        current_sequence = np.array(list(self.data_buffer))

        scaled_sequence = self.scaler.transform(current_sequence.reshape(-1, self.input_features_count))
        
        return scaled_sequence.reshape(self.sequence_length, self.input_features_count)

    async def generate_shap_plots(self, explanation_for_plotting, plot_suffix):
        """
        Generates and saves various SHAP plots for a single prediction.
        This function is designed to be called as an async task to avoid blocking.
        Requires matplotlib to be imported.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("Matplotlib not found. Skipping SHAP plot generation. Install with 'pip install matplotlib'.")
            return

        if not self.save_shap_plots:
            return

        try:
            os.makedirs(self.plot_dir, exist_ok=True)

            waterfall_path = os.path.join(self.plot_dir, f"waterfall_{plot_suffix}.png")
            plt.clf() 
            if explanation_for_plotting.data.ndim == 2 and explanation_for_plotting.data.shape[0] == 1:
                shap.plots.waterfall(shap.Explanation(
                    values=explanation_for_plotting.values,
                    base_values=explanation_for_plotting.base_values,
                    data=explanation_for_plotting.data.flatten(), 
                    feature_names=explanation_for_plotting.feature_names
                ), show=False)
            else: 
                shap.plots.waterfall(explanation_for_plotting, show=False)
            plt.title(f"Waterfall Plot - {self.node_id} - {plot_suffix}")
            plt.savefig(waterfall_path, bbox_inches='tight')
            plt.close() 
            logger.info(f"Node {self.node_id}: Saved Waterfall plot to {waterfall_path}")
        except Exception as e:
            logger.error(f"Node {self.node_id}: Error saving Waterfall plot: {e}")

        try:
            force_path = os.path.join(self.plot_dir, f"force_{plot_suffix}.html")
            data_for_force_plot = explanation_for_plotting.data.flatten() if explanation_for_plotting.data.ndim == 2 and explanation_for_plotting.data.shape[0] == 1 else explanation_for_plotting.data

            shap.save_html(force_path, shap.force_plot(
                explanation_for_plotting.base_values,
                explanation_for_plotting.values,
                data_for_force_plot,
                feature_names=explanation_for_plotting.feature_names,
                show=False
            ))
            logger.info(f"Node {self.node_id}: Saved Force plot to {force_path}")
        except Exception as e:
            logger.error(f"Node {self.node_id}: Error saving Force plot: {e}")

        try:
            if explanation_for_plotting.values is not None and len(explanation_for_plotting.values) > 0:
                most_impactful_feature_idx = np.argmax(np.abs(explanation_for_plotting.values))
                most_impactful_feature_name = explanation_for_plotting.feature_names[most_impactful_feature_idx]
                
                dependence_path = os.path.join(self.plot_dir, f"dependence_{most_impactful_feature_name}_{plot_suffix}.png")
                plt.clf()
                shap.plots.scatter(explanation_for_plotting[:, most_impactful_feature_idx], show=False)
                plt.title(f"Dependence Plot - {self.node_id} - {most_impactful_feature_name}")
                plt.savefig(dependence_path, bbox_inches='tight')
                plt.close()
                logger.info(f"Node {self.node_id}: Saved Dependence plot for {most_impactful_feature_name} to {dependence_path}")
            else:
                logger.warning(f"Node {self.node_id}: Skipping Dependence plot: No SHAP values to determine impactful feature.")
        except Exception as e:
            logger.error(f"Node {self.node_id}: Error saving Dependence plot: {e}")

    async def predict_anomaly(self, input_data_raw: Dict[str, Any], all_feature_names: List[str]):
        """
        Predicts anomaly score for a new incoming data point.
        Triggers SHAP explanation if an anomaly is detected.
        """
        # Initialize default return values
        default_return = {
            "anomaly_score": 0.0, "confidence_level": 0.0, "affected_components": [],
            "severity_classification": "N/A", "time_to_failure": "N/A",
            "root_cause_indicators": [], "recommended_actions": [],
            "shap_explanation": None,
            "status": "Unknown Error", # Default status
            "predicted_metrics": {}, # Always include, even if empty
            "actual_metrics": {} # Always include, even if empty
        }

        if not self.is_trained:
            default_return["status"] = "Model not trained"
            default_return["actual_metrics"] = {f: input_data_raw.get(f, 0.0) for f in all_feature_names}
            return default_return

        processed_sequence = self.preprocess_input(input_data_raw, all_feature_names)

        if processed_sequence is None:
            default_return["status"] = "Insufficient data for prediction"
            default_return["actual_metrics"] = {f: input_data_raw.get(f, 0.0) for f in all_feature_names}
            return default_return

        input_for_prediction = processed_sequence[np.newaxis, :, :]

        anomaly_score = 0.0
        confidence_level = 0.0
        is_anomaly = False
        affected_components = []
        root_cause_indicators = []
        severity_classification = "N/A"
        time_to_failure = "N/A"
        recommended_actions = []
        shap_values_output = None
        status = "Normal" 
        
        # Extract actual metrics in original scale
        actual_scaled_last_step = processed_sequence[-1]
        actual_metrics_original_scale = self.scaler.inverse_transform(actual_scaled_last_step.reshape(1, -1))[0]
        actual_metrics_dict = {self.feature_names[i]: float(actual_metrics_original_scale[i]) for i in range(len(self.feature_names))}


        try:
            predicted_scaled_next_step = self.model.predict(input_for_prediction, verbose=0)[0]

            predicted_metrics_original_scale = self.scaler.inverse_transform(predicted_scaled_next_step.reshape(1, -1))[0]
            predicted_metrics_dict = {self.feature_names[i]: float(predicted_metrics_original_scale[i]) for i in range(len(self.feature_names))}

            reconstruction_error = np.mean(np.square(predicted_scaled_next_step - actual_scaled_last_step))
            
            conceptual_max_error = 0.005
            anomaly_score = min(1.0, reconstruction_error / conceptual_max_error)

            confidence_level = 100 * (1 - anomaly_score)

            is_anomaly = anomaly_score > self.anomaly_threshold

            if is_anomaly:
                status = "Anomaly detected"
                logger.debug(f"Node {self.node_id}: Anomaly detected with score: {anomaly_score:.4f}. Generating SHAP explanation...")
                if self.shap_explainer is None:
                    logger.warning(f"Node {self.node_id}: SHAP explainer not initialized. Skipping SHAP explanation.")
                    root_cause_indicators = [{"error": "SHAP explainer not initialized", "details": "Cannot generate explanation."}]
                    affected_components = ["Unknown"]
                    severity_classification = "Low"
                    recommended_actions = ["Investigate manually."]
                else:
                    try:
                        raw_shap_output_from_explainer = self.shap_explainer.shap_values(input_for_prediction)
                        
                        # For GradientExplainer on a single-output autoencoder, shap_values_output is usually a list of arrays,
                        # where each array corresponds to the SHAP values for one output feature.
                        # To get overall feature importance, we can sum the absolute SHAP values across output features.
                        if isinstance(raw_shap_output_from_explainer, list):
                            # Stack and sum absolute values to get overall feature importance for each timestep
                            # Resulting shape: (batch_size, sequence_length, features)
                            stacked_shap_abs = np.stack([np.abs(s) for s in raw_shap_output_from_explainer if isinstance(s, np.ndarray)])
                            # Sum across the output features dimension (axis=0) to get a single (batch_size, sequence_length, features) array
                            overall_shap_values = np.sum(stacked_shap_abs, axis=0) 
                        elif isinstance(raw_shap_output_from_explainer, np.ndarray):
                            # If it's a single array (e.g., (batch_size, sequence_length, features)), take absolute values
                            overall_shap_values = np.abs(raw_shap_output_from_explainer)
                        else:
                            logger.warning(f"Node {self.node_id}: SHAP values raw format from GradientExplainer is unexpected: {type(raw_shap_output_from_explainer)}")
                            overall_shap_values = None

                        if overall_shap_values is not None and overall_shap_values.shape[1] > 0:
                            # We are interested in the SHAP values for the *last* timestep of the input sequence
                            # as that's what directly precedes the prediction.
                            shap_values_for_last_timestep = overall_shap_values[0, -1, :]
                            
                            # --- FIX: Calculate base_values from background data predictions ---
                            # The base_values for GradientExplainer are the average model output on the background data.
                            # We need to predict on the background data and then average those predictions.
                            if self.shap_background_data is not None and self.shap_background_data.shape[0] > 0:
                                background_predictions = self.model.predict(self.shap_background_data, verbose=0)
                                # For autoencoder, base_values should be the average of the reconstructed background data.
                                base_values_for_explanation = np.mean(background_predictions, axis=0) # Average across samples
                            else:
                                logger.warning(f"Node {self.node_id}: SHAP background data not available for base_values. Using zero.")
                                base_values_for_explanation = np.zeros(self.input_features_count)
                            
                            # The data for explanation should be the actual input data point (last timestep)
                            data_for_explanation_original_scale = self.scaler.inverse_transform(processed_sequence[-1:].reshape(1, -1))[0]
                            
                            explanation_for_plotting = shap.Explanation(
                                values=shap_values_for_last_timestep,
                                base_values=base_values_for_explanation, # Use the computed base values
                                data=data_for_explanation_original_scale,
                                feature_names=self.feature_names
                            )

                            plot_suffix = f"{int(time.time())}"
                            asyncio.create_task(self.generate_shap_plots(explanation_for_plotting, plot_suffix))

                            sorted_features_by_impact = sorted(zip(self.feature_names, shap_values_for_last_timestep), key=lambda x: np.abs(x[1]), reverse=True)

                            top_n = 5
                            for feature, importance in sorted_features_by_impact[:top_n]:
                                if np.abs(importance) > 1e-6: # Only include features with significant impact
                                    root_cause_indicators.append({"feature": feature, "importance": f"{importance:.4f}"})
                                    # Categorize affected components based on feature names
                                    if any(k in feature.lower() for k in ['throughput', 'latency', 'packet_loss', 'signal_strength', 'neighbor_count', 'link_utilization', 'jitter']):
                                        if "Network" not in affected_components: affected_components.append("Network")
                                    elif any(k in feature.lower() for k in ['cpu_usage', 'memory_usage', 'buffer_occupancy']):
                                        if "Equipment" not in affected_components: affected_components.append("Equipment")
                                    elif any(k in feature.lower() for k in ['voltage_level', 'power_stability', 'energy_level']):
                                         if "Power_System" not in affected_components: affected_components.append("Power_System")
                                    elif 'position' in feature.lower():
                                        if "Location/Environmental" not in affected_components: affected_components.append("Location/Environmental")
                                    elif 'operational' in feature.lower():
                                        if "Node_State" not in affected_components: affected_components.append("Node_State")
                                    elif 'load' in feature.lower():
                                        if "Load_Management" not in affected_components: affected_components.append("Load_Management")
                                    elif 'degradation_level' in feature.lower() or 'fault_severity' in feature.lower():
                                        if "System_Health" not in affected_components: affected_components.append("System_Health")
                            
                            if not root_cause_indicators and is_anomaly:
                                root_cause_indicators.append({"feature": "Unknown/General Anomaly", "importance": "N/A"})

                            # Determine severity based on anomaly score and affected components
                            if anomaly_score > 0.75 and ("Network" in affected_components or "Equipment" in affected_components or "Node_State" in affected_components):
                                severity_classification = "Critical"
                            elif anomaly_score > 0.5:
                                severity_classification = "High"
                            elif anomaly_score > 0.25:
                                severity_classification = "Medium"
                            else:
                                severity_classification = "Low"

                            # Provide recommended actions based on severity
                            if severity_classification == "Critical":
                                time_to_failure = "Immediate (0-5 min)"
                                recommended_actions.append("Initiate emergency failover/redundancy switch.")
                                recommended_actions.append("Isolate affected node for deep diagnostics.")
                                recommended_actions.append("Dispatch field technicians for urgent on-site inspection.")
                            elif severity_classification == "High":
                                time_to_failure = "Short (5-30 min)"
                                recommended_actions.append("Execute automated diagnostics and health checks.")
                                recommended_actions.append("Prepare for traffic rerouting/load shedding.")
                                recommended_actions.append("Alert network operations center (NOC) for close monitoring.")
                            elif severity_classification == "Medium":
                                time_to_failure = "Medium (30-120 min)"
                                recommended_actions.append("Monitor closely and review recent configuration changes.")
                                recommended_actions.append("Schedule proactive maintenance if trend continues.")
                                recommended_actions.append("Review logs for pre-failure indicators.")
                            else:
                                time_to_failure = "Long (>120 min)"
                                recommended_actions.append("Log for trend analysis and historical anomaly patterns.")
                                recommended_actions.append("No immediate action required, but keep under observation.")
                                recommended_actions.append("Consider a routine health check during next maintenance window.")


                            shap_values_output = {
                                "feature_names": self.feature_names,
                                "importances": shap_values_for_last_timestep.tolist(),
                                "raw_shap_values_for_last_timestep": overall_shap_values[0, -1, :].tolist()
                            }

                        else:
                            logger.warning(f"Node {self.node_id}: Final SHAP values array is invalid or empty. Cannot generate detailed explanation.")
                            root_cause_indicators = [{"error": "SHAP explanation failed", "details": "SHAP values array invalid or empty after processing."}]
                            affected_components = ["Unknown"]
                            severity_classification = "Low"
                            recommended_actions = ["Investigate manually."]
                            shap_values_output = None

                    except Exception as e:
                        logger.error(f"Node {self.node_id}: SHAP explanation failed: {e}", exc_info=True)
                        root_cause_indicators = [{"error": "SHAP explanation failed", "details": str(e)}]
                        affected_components = ["Unknown"]
                        severity_classification = "Low"
                        recommended_actions = ["Investigate manually."]
                        shap_values_output = None

            return {
                "anomaly_score": round(anomaly_score, 4),
                "confidence_level": round(confidence_level, 2),
                "affected_components": affected_components,
                "severity_classification": severity_classification,
                "time_to_failure": time_to_failure,
                "root_cause_indicators": root_cause_indicators,
                "recommended_actions": recommended_actions,
                "shap_explanation": shap_values_output,
                "status": status,
                "predicted_metrics": predicted_metrics_dict, # Always include
                "actual_metrics": actual_metrics_dict # Always include
            }
            
        except Exception as e:
            logger.error(f"Error processing LSTM for node {self.node_id} at time {input_data_raw.get('current_time', 'N/A')}s: {e}", exc_info=True)
            default_return["status"] = "Error during prediction"
            default_return["root_cause_indicators"] = [{"error": "Prediction failed", "details": str(e)}]
            default_return["actual_metrics"] = {f: input_data_raw.get(f, 0.0) for f in all_feature_names}
            return default_return

# --- Calculation Agent (Main Class) ---
class CalculationAgent:
    """
    The main Calculation Agent responsible for managing anomaly detectors for multiple nodes,
    receiving data, triggering predictions, and communicating with other agents (Healing, MCP).
    """
    def __init__(self, node_ids: List[str], pub_socket_address_a2a: str, push_socket_address_mcp: str, sequence_length: int = 10):
        """
        Initializes the Calculation Agent.

        Args:
            node_ids (list): A list of unique identifiers for all network nodes to monitor.
            pub_socket_address_a2a (str): ZeroMQ address for publishing A2A anomaly alerts to the Healing Agent.
            push_socket_address_mcp (str): ZeroMQ address for pushing status updates to the MCP.
            sequence_length (int): The length of the time series sequence for LSTM.
        """
        self.config = self.load_config() 
        self.node_ids = node_ids 

        self.sequence_length = self.config.get('lstm_sequence_length', sequence_length) 
        self.node_detectors = {} 
        
        self.all_features = self.config.get('lstm_features', []) 
        self.numerical_features_for_lstm = [] 
        self.input_features_count = 0 

        self.context = zmq.asyncio.Context()
        
        self.a2a_publisher_socket = self.context.socket(zmq.PUB)
        self.a2a_publisher_socket.bind(pub_socket_address_a2a)
        logger.info(f"Calculation Agent: A2A Publisher bound to {pub_socket_address_a2a}")

        self.mcp_push_socket = self.context.socket(zmq.PUSH)
        self.mcp_push_socket.bind(push_socket_address_mcp) 
        logger.info(f"Calculation Agent: MCP PUSH bound to {push_socket_address_mcp}")

        self.monitor_data_file_path = MONITOR_DATA_STREAM_FILE 
        self.last_read_file_position = 0 
        self.is_running = False 

    def load_config(self) -> Dict[str, Any]:
        """Loads configuration from JSON file."""
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            logger.info(f"Calculation Agent configuration loaded from {CONFIG_FILE}")
            return config
        except FileNotFoundError:
            logger.warning(f"Configuration file {CONFIG_FILE} not found. Using default configuration.")
            return self.get_default_config()
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from {CONFIG_FILE}. Using default configuration.")
            return self.get_default_config()

    def get_default_config(self) -> Dict[str, Any]:
        """Returns a default configuration for the Calculation Agent."""
        return {
            "lstm_sequence_length": 10,
            "lstm_epochs": 20,
            "anomaly_threshold": 0.05,
            "alert_debounce_interval": 10,
            "model_training_batch_size": 32,
            "train_on_startup": True,
            "training_data_limit": 10000,
            "lstm_features": [ 
                'throughput', 'latency', 'packet_loss', 'jitter', 
                'signal_strength', 'cpu_usage', 'memory_usage', 'buffer_occupancy',
                'active_links', 'neighbor_count', 'link_utilization', 'critical_load',
                'normal_load', 'energy_level', 'x_position', 'y_position', 'z_position',
                'degradation_level', 'fault_severity', 'power_stability', 'voltage_level' 
            ],
            "prediction_horizon": 1,
            "monitor_ns3_metrics_file": "rural_network_metrics.csv" 
        }

    def _initialize_detectors(self, input_features_count: int, numerical_feature_names: List[str]):
        """
        Initializes an LSTM anomaly detector instance for each configured node.
        """
        self.input_features_count = input_features_count
        self.numerical_features_for_lstm = numerical_feature_names 

        for node_id in self.node_ids:
            self.node_detectors[node_id] = LSTMAnomalyDetector(
                node_id=node_id,
                input_features_count=self.input_features_count,
                sequence_length=self.sequence_length
            )

    async def _objective_function(self, params, node_id, X_train, y_train):
        """
        Objective function for SSA to optimize LSTM hyperparameters.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            pass

        hidden_size, learning_rate, num_layers, dropout_rate = \
            int(params[0]), float(params[1]), int(params[2]), float(params[3])
        
        hidden_size = max(16, min(hidden_size, 256))
        learning_rate = max(1e-5, min(learning_rate, 1e-2))
        num_layers = max(1, min(num_layers, 5))
        dropout_rate = max(0.0, min(dropout_rate, 0.5))

        temp_detector = LSTMAnomalyDetector(
            node_id=f"temp_opt_{node_id}",
            input_features_count=self.input_features_count,
            sequence_length=self.sequence_length,
            save_shap_plots=False 
        )
        temp_detector.build_model(
            hidden_size=hidden_size,
            learning_rate=learning_rate,
            num_layers=num_layers,
            dropout_rate=dropout_rate
        )

        try:
            temp_detector.train_model(X_train, y_train, epochs=5, verbose=0)
            
            if not temp_detector.is_trained:
                return float('inf')

            X_train_reshaped_for_scaler = X_train.reshape(-1, X_train.shape[-1])
            X_train_scaled_flat = temp_detector.scaler.transform(X_train_reshaped_for_scaler)
            X_train_scaled = X_train_scaled_flat.reshape(X_train.shape)

            predictions = temp_detector.model.predict(X_train_scaled, verbose=0)
            
            y_train_scaled = temp_detector.scaler.transform(y_train)
            
            loss = mean_squared_error(y_train_scaled, predictions)
        except Exception as e:
            logger.error(f"Node {node_id}: Error during SSA objective function: {e}")
            loss = float('inf')

        return loss

    async def optimize_lstm_with_ssa(self, node_id, X_train_data, y_train_data):
        """
        Optimizes LSTM hyperparameters for a specific node using the Salp Swarm Algorithm (SSA).
        """
        logger.info(f"Node {node_id}: Starting SSA optimization for LSTM hyperparameters...")
        lower_bounds = [32, 0.0001, 2, 0.0]
        upper_bounds = [128, 0.005, 3, 0.3]

        obj_func_with_data = partial(self._objective_function, node_id=node_id, X_train=X_train_data, y_train=y_train_data)

        ssa = SalpSwarmOptimizer(
            obj_func=obj_func_with_data,
            n_salps=2, 
            n_iterations=1, 
            lower_bounds=lower_bounds,
            upper_bounds=upper_bounds
        )

        best_params, best_loss = await ssa.optimize()
        logger.info(f"Node {node_id}: SSA Optimization complete. Best params: {best_params}, Best Loss: {best_loss:.4f}")

        optimized_hidden_size = int(best_params[0])
        optimized_lr = float(best_params[1])
        optimized_num_layers = int(best_params[2])
        optimized_dropout = float(best_params[3])

        detector = self.node_detectors[node_id]
        detector.build_model(
            hidden_size=optimized_hidden_size,
            learning_rate=optimized_lr,
            num_layers=optimized_num_layers,
            dropout_rate=optimized_dropout
        )
        detector.train_model(X_train_data, y_train_data, epochs=self.config['lstm_epochs'], batch_size=self.config['model_training_batch_size'])
        logger.info(f"Node {node_id}: LSTM model updated with optimized parameters and fully retrained.")


    async def load_and_prepare_initial_training_data(self, file_path):
        """
        Loads initial training data for all nodes from the NS3 metrics CSV.
        This data is used to train each node's detector once at startup.
        """
        logger.info(f"Calculation Agent: Loading initial training data from {file_path}...")
        try:
            df = pd.read_csv(file_path)
            
            df['NodeId'] = df['NodeId'].apply(lambda x: f"node_{int(x):02d}")
            
            column_mapping = {
                'Time': 'current_time', 
                'Throughput_Mbps': 'throughput',
                'Latency_ms': 'latency',
                'PacketLoss_Rate': 'packet_loss',
                'Jitter_ms': 'jitter',
                'SignalStrength_dBm': 'signal_strength',
                'CPU_Usage': 'cpu_usage',
                'Memory_Usage': 'memory_usage',
                'Buffer_Occupancy': 'buffer_occupancy',
                'Active_Links': 'active_links',
                'Neighbor_Count': 'neighbor_count',
                'Link_Utilization': 'link_utilization',
                'Critical_Load': 'critical_load',
                'Normal_Load': 'normal_load',
                'Energy_Level': 'energy_level',
                'X_Position': 'x_position',
                'Y_Position': 'y_position',
                'Z_Position': 'z_position',
                'Degradation_Level': 'degradation_level',
                'Fault_Severity': 'fault_severity',
                'Power_Stability': 'power_stability',
                'Voltage_Level': 'voltage_level', 
                'Operational_Status': 'operational', 
                'NodeType': 'node_type' 
            }
            df_renamed = df.rename(columns=column_mapping)

            self.numerical_features_for_lstm = [
                f for f in self.config['lstm_features'] if f in df_renamed.columns and f not in ['operational', 'node_type', 'current_time']
            ]
            
            if not self.numerical_features_for_lstm:
                logger.error("No numerical features found for LSTM training after mapping. Check config 'lstm_features' and CSV columns.")
                sys.exit(1)

            self.input_features_count = len(self.numerical_features_for_lstm)
            self.all_features = self.numerical_features_for_lstm 

            logger.info(f"Calculation Agent: Identified {self.input_features_count} numerical features for models: {self.numerical_features_for_lstm}")
            
            node_training_data = {}
            
            for node_id_formatted in self.node_ids: 
                node_df = df_renamed[df_renamed['NodeId'] == node_id_formatted].sort_values(by='current_time')
                
                node_features_df = node_df[self.numerical_features_for_lstm].astype(float)

                if len(node_features_df) < self.sequence_length + 1:
                    logger.warning(f"Node {node_id_formatted}: Not enough data points ({len(node_features_df)}) for initial training with sequence length {self.sequence_length}. Skipping training for this node.")
                    node_training_data[node_id_formatted] = (np.array([]), np.array([]))
                    continue

                X_train_list, y_train_list = [], []
                num_sequences = len(node_features_df) - self.sequence_length
                
                for i in range(num_sequences):
                    sequence = node_features_df.iloc[i : i + self.sequence_length].values
                    target = node_features_df.iloc[i + self.sequence_length].values
                    X_train_list.append(sequence)
                    y_train_list.append(target)
                
                node_training_data[node_id_formatted] = (
                    np.array(X_train_list, dtype=np.float32),
                    np.array(y_train_list, dtype=np.float32)
                )
                logger.info(f"Node {node_id_formatted}: Prepared {num_sequences} training sequences.")
            
            return node_training_data

        except FileNotFoundError:
            logger.error(f"Error: NS3 metrics file not found at {file_path}. Please ensure 'rural_network_metrics.csv' exists.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error loading and preparing initial training data: {e}", exc_info=True)
            sys.exit(1)


    async def process_data_point(self, node_id: str, raw_data_point_dict: Dict[str, Any]):
        """
        Receives a single raw data point for a node, processes it,
        triggers anomaly detection, and sends alerts/status updates.
        """
        detector = self.node_detectors.get(node_id)
        if not detector:
            logger.warning(f"Error: No detector found for node {node_id}. Skipping data point.")
            return

        # Ensure detector is trained before attempting prediction
        if not detector.is_trained:
            logger.debug(f"Node {node_id}: Detector not trained yet. Skipping processing this data point.")
            # Still push status to MCP for "Insufficient data" or "No model"
            await self.push_mcp_status(
                node_id, "Insufficient data for prediction" if len(detector.data_buffer) < detector.sequence_length else "No model available",
                0.0, raw_data_point_dict.get('current_time', 0.0)
            )
            return

        anomaly_results = await detector.predict_anomaly(raw_data_point_dict, self.numerical_features_for_lstm)

        # Send alert to Healing Agent (via PUB/SUB)
        if anomaly_results["status"] == "Anomaly detected":
            simulation_time_for_alert = raw_data_point_dict.get('current_time', 0.0)
            
            anomaly_alert = AnomalyAlert(
                alert_id=f"ANOMALY_{int(time.time())}_{node_id}",
                node_id=node_id,
                detection_time=datetime.now(),
                simulation_time=simulation_time_for_alert,
                anomaly_score=anomaly_results['anomaly_score'],
                threshold=detector.anomaly_threshold,
                description=anomaly_results['explanation'] if 'explanation' in anomaly_results else f"Anomaly detected for node {node_id}",
                predicted_metrics=anomaly_results.get('predicted_metrics', {}), # Use .get()
                actual_metrics=anomaly_results.get('actual_metrics', {}) # Use .get()
            )
            
            message_to_healing = {
                "type": "anomaly_alert",
                "alert_id": anomaly_alert.alert_id,
                "node_id": anomaly_alert.node_id,
                "simulation_time": anomaly_alert.simulation_time,
                "anomaly_score": anomaly_alert.anomaly_score,
                "description": anomaly_alert.description,
                "actual_metrics": anomaly_alert.actual_metrics,
                "predicted_metrics": anomaly_alert.predicted_metrics,
                "source_agent": anomaly_alert.source_agent
            }
            try:
                await self.a2a_publisher_socket.send_json(message_to_healing)
                logger.info(f"Node {node_id}: A2A: Published anomaly alert (Status: {anomaly_results['status']}, Score: {anomaly_results['anomaly_score']:.4f})")
            except Exception as e:
                logger.error(f"Node {node_id}: Failed to send alert to Healing Agent: {e}")

        # Send status update to MCP Agent (always send status, not just anomalies)
        mcp_message = {
            "source": "CalculationAgent",
            "type": "status_update",
            "node_id": node_id,
            "timestamp": datetime.now().isoformat(), 
            "simulation_time": raw_data_point_dict.get('current_time', 0.0), 
            "status": anomaly_results["status"],
            "details": anomaly_results
        }
        try:
            await self.mcp_push_socket.send_json(mcp_message)
            logger.info(f"Node {node_id}: MCP: Pushed status update (Status: {anomaly_results['status']}, Score: {anomaly_results['anomaly_score']:.4f}).")
        except Exception as e:
            logger.error(f"Node {node_id}: Failed to push status to MCP: {e}", exc_info=True)


    async def data_processing_loop(self):
        """
        Continuously reads and processes new data batches from the Monitor Agent's file.
        """
        logger.info(f"Starting data processing loop, reading from {self.monitor_data_file_path}...")
        
        if not os.path.exists(self.monitor_data_file_path):
            with open(self.monitor_data_file_path, 'w') as f:
                f.write('') 
            logger.info(f"Created empty data stream file: {self.monitor_data_file_path}")

        while True:
            try:
                with open(self.monitor_data_file_path, 'r') as f:
                    f.seek(self.last_read_file_position)
                    
                    new_lines = f.readlines()
                    
                    if new_lines:
                        for line in new_lines:
                            try:
                                batch_data = json.loads(line.strip())
                                
                                if 'messages' in batch_data and isinstance(batch_data['messages'], list):
                                    for msg in batch_data['messages']:
                                        if 'content' in msg and 'metrics' in msg['content']:
                                            for node_id_from_msg, node_metrics_data in msg['content']['metrics'].items():
                                                if node_id_from_msg.startswith('node_'):
                                                    asyncio.create_task(self.process_data_point(node_id_from_msg, node_metrics_data))
                                                else:
                                                    logger.warning(f"Malformed node_id in metrics data: {node_id_from_msg}. Skipping.")
                                        else:
                                            logger.warning(f"Message content missing 'metrics' key: {msg}. Skipping.")
                                else:
                                    logger.warning(f"Batch data missing 'messages' key or not a list: {batch_data}. Skipping.")
                            except json.JSONDecodeError as e:
                                logger.error(f"Error decoding JSON from line: {line.strip()}. Error: {e}")
                            except Exception as e:
                                logger.error(f"Error processing message from file: {e}", exc_info=True)
                        
                        self.last_read_file_position = f.tell()
                    else:
                        await asyncio.sleep(self.config['alert_debounce_interval']) 
            except FileNotFoundError:
                logger.error(f"Data stream file not found: {self.monitor_data_file_path}. Waiting for it to be created by Monitor Agent.")
                await asyncio.sleep(5) 
            except Exception as e:
                logger.error(f"Error in data processing loop (file read): {e}", exc_info=True)
                await asyncio.sleep(1) 

    async def start(self):
        """
        Starts the Calculation Agent:
        1. Loads initial training data for all nodes from NS3_METRICS_PATH.
        2. Builds and trains LSTM models for each node.
        3. Optimizes hyperparameters using SSA for each node.
        4. Enters a loop to receive live data from Monitor Agent's file and perform predictions.
        """
        logger.info("Calculation Agent started. Performing initial setup (training models for all nodes)...")
        
        # Use the monitor_ns3_metrics_file from config for initial training data source
        node_training_data = await self.load_and_prepare_initial_training_data(self.config['monitor_ns3_metrics_file'])
        
        if self.input_features_count == 0 or not self.numerical_features_for_lstm:
            logger.error("No numerical features identified from training data. Cannot initialize detectors. Exiting.")
            sys.exit(1)
        
        self._initialize_detectors(self.input_features_count, self.numerical_features_for_lstm)

        training_tasks = []
        for node_id in self.node_ids:
            X_train_np, y_train_np = node_training_data.get(node_id, (np.array([]), np.array([])))
            
            if X_train_np.size > 0:
                training_tasks.append(
                    asyncio.create_task(
                        self.optimize_lstm_with_ssa(node_id, X_train_np, y_train_np)
                    )
                )
            else:
                logger.warning(f"Node {node_id}: No sufficient training data available. Detector for this node will not be trained.")

        if training_tasks:
            results = await asyncio.gather(*training_tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error during training/optimization for node {self.node_ids[i]}: {result}", exc_info=True)
        else:
            logger.error("No nodes had sufficient training data to train any detector. Calculation Agent will not perform anomaly detection.")
            
        logger.info("Calculation Agent: Initial setup complete for all monitored nodes. Waiting for data from Monitor Agent...")

        self.is_running = True
        await self.data_processing_loop()

    async def stop(self):
        """
        Stops the Calculation Agent and cleans up resources.
        """
        logger.info("Calculation Agent: Stopping...")
        self.is_running = False
        self.a2a_publisher_socket.close()
        self.mcp_push_socket.close()
        self.context.term()
        logger.info("Calculation Agent: Stopped.")


if __name__ == "__main__":
    logger.info("Running standalone test for Calculation Agent...")

    test_pub_address_a2a = CALC_HEAL_PUB_SUB_ADDRESS
    test_push_address_mcp = CALC_MCP_PUSH_PULL_ADDRESS

    test_node_ids = [f"node_{i:02d}" for i in range(50)] 

    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "lstm_sequence_length": 10,
            "lstm_epochs": 20,
            "anomaly_threshold": 0.05,
            "alert_debounce_interval": 5,
            "model_training_batch_size": 32,
            "train_on_startup": True,
            "training_data_limit": 950,
            "lstm_features": [
                'throughput', 'latency', 'packet_loss', 'voltage_level',
                'operational', 'node_type', 'current_time', 'jitter', 
                'signal_strength', 'cpu_usage', 'memory_usage', 'buffer_occupancy',
                'active_links', 'neighbor_count', 'link_utilization', 'critical_load',
                'normal_load', 'energy_level', 'x_position', 'y_position', 'z_position',
                'degradation_level', 'fault_severity', 'power_stability'
            ],
            "prediction_horizon": 1,
            "monitor_ns3_metrics_file": "rural_network_metrics.csv"
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(default_config, f, indent=2)
        logger.info(f"Created default {CONFIG_FILE} for testing.")

    calc_agent = CalculationAgent(
        node_ids=test_node_ids,
        pub_socket_address_a2a=test_pub_address_a2a,
        push_socket_address_mcp=test_push_address_mcp
    )

    try:
        asyncio.run(calc_agent.start())
    except KeyboardInterrupt:
        logger.info("\nCalculation Agent standalone test stopped.")
    except Exception as e:
        logger.exception("An error occurred during standalone Calculation Agent run:")
    finally:
        if 'calc_agent' in locals() and hasattr(calc_agent, 'is_running') and calc_agent.is_running:
            asyncio.run(calc_agent.stop())