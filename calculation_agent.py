# calculation_agent.py
import asyncio
import logging
import json
import time
from datetime import datetime
from collections import deque
import numpy as np
import pandas as pd
import tensorflow as tf
from keras.models import Sequential, load_model
from keras.layers import LSTM, Dense, Dropout
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
import joblib
import os
import zmq.asyncio
import sys
from functools import partial
import shap
import matplotlib.pyplot as plt


# Set up logging for CalculationAgent
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the SalpSwarmOptimizer from its dedicated file
from salp_swarm_optimizer import SalpSwarmOptimizer

# Configuration
CONFIG_FILE = "calculation_config.json"
MODEL_DIR = "lstm_model"
# SCALER_PATH and LSTM_MODEL_PATH will now be per-node
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
    def __init__(self, input_size=None, hidden_size=None, num_layers=2, dropout_rate=0.2, sequence_length=None, **kwargs):
        # Pop custom arguments from kwargs or assign them if explicitly passed
        # This makes sure they are consumed as keyword args during loading
        _input_size = kwargs.pop('input_size', input_size)
        _hidden_size = kwargs.pop('hidden_size', hidden_size)
        _num_layers = kwargs.pop('num_layers', num_layers)
        _dropout_rate = kwargs.pop('dropout_rate', dropout_rate)
        _sequence_length = kwargs.pop('sequence_length', sequence_length)

        # Ensure required args are provided either explicitly or via kwargs
        if _input_size is None or _hidden_size is None or _sequence_length is None:
            raise ValueError("input_size, hidden_size, and sequence_length must be provided to LSTMAnomalyModel.")

        # Store these arguments as attributes
        self.input_size = _input_size
        self.hidden_size = _hidden_size
        self.num_layers = _num_layers
        self.dropout_rate = _dropout_rate
        self.sequence_length = _sequence_length

        super(LSTMAnomalyModel, self).__init__(**kwargs)

        # The Input layer correctly allows for a flexible batch size (None)
        self.add(tf.keras.layers.Input(shape=(self.sequence_length, self.input_size)))

        # Add LSTM layers
        for i in range(self.num_layers):
            return_sequences = (i < self.num_layers - 1) # Return sequences for all but the last LSTM layer
            self.add(LSTM(self.hidden_size, activation='relu', return_sequences=return_sequences))
        
        self.add(Dropout(self.dropout_rate))
        self.add(Dense(self.input_size)) # Output layer for reconstruction

    def get_config(self):
        config = super(LSTMAnomalyModel, self).get_config()
        config.update({
            'input_size': self.input_size,
            'hidden_size': self.hidden_size,
            'num_layers': self.num_layers,
            'dropout_rate': self.dropout_rate,
            'sequence_length': self.sequence_length,
        })
        return config

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
        self.feature_names = None # Stores actual feature names from training data
        self.save_shap_plots = save_shap_plots
        self.plot_dir = os.path.join(plot_dir, node_id)
        self.shap_background_data = None # Store background data for SHAP base_values

        # Corrected: Change model file extension to .keras
        self.model_path = os.path.join(MODEL_DIR, f"{node_id}_lstm_model.keras")
        self.scaler_path = os.path.join(MODEL_DIR, f"{node_id}_scaler.pkl")

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
        # Using Adam optimizer with a custom learning rate
        optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)
        self.model.compile(optimizer=optimizer, loss='mse')
        logger.info(f"Node {self.node_id}: LSTM model built with hidden_size={hidden_size}, lr={learning_rate}, layers={num_layers}")

    def save_model(self):
        """Saves the trained LSTM model and scaler."""
        os.makedirs(MODEL_DIR, exist_ok=True)
        try:
            if self.model:
                # Keras automatically saves custom objects if get_config is implemented
                # Will save as .keras due to self.model_path extension
                self.model.save(self.model_path)
                logger.info(f"Node {self.node_id}: Saved LSTM model to {self.model_path}")
            if self.scaler:
                joblib.dump(self.scaler, self.scaler_path)
                logger.info(f"Node {self.node_id}: Saved scaler to {self.scaler_path}")
        except Exception as e:
            logger.error(f"Node {self.node_id}: Error saving model or scaler: {e}")

    def load_model(self):
        """Loads the pre-trained LSTM model and scaler."""
        # Will load .keras due to self.model_path extension
        if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
            try:
                # Use custom_object_scope to recognize LSTMAnomalyModel
                # Keras uses the get_config method to reconstruct the model
                self.model = load_model(self.model_path, custom_objects={'LSTMAnomalyModel': LSTMAnomalyModel})
                self.scaler = joblib.load(self.scaler_path)
                self.is_trained = True
                logger.info(f"Node {self.node_id}: Successfully loaded model from {self.model_path}")
                return True
            except Exception as e:
                logger.error(f"Node {self.node_id}: Error loading model: {e}")
                return False
        else:
            logger.warning(f"Node {self.node_id}: No saved model or scaler found.")
            return False

    def train_model(self, X_train, y_train, epochs=50, batch_size=32, verbose=0):
        """Trains the LSTM model using the provided training data."""
        if X_train.size == 0 or y_train.size == 0:
            logger.warning(f"Node {self.node_id}: Skipping training, X_train or y_train is empty.")
            self.is_trained = False
            return

        # Fit scaler if not already fitted (e.g., if loading a new model or first training)
        # Ensure scaler is fitted on 2D data (all samples, all features)
        if not hasattr(self.scaler, 'min_') or not hasattr(self.scaler, 'scale_'):
            # Concatenate X_train sequences and y_train targets to fit scaler on all feature distributions
            # This ensures the scaler covers the full range of data
            combined_data_for_scaler_fit = np.vstack([X_train.reshape(-1, self.input_features_count), y_train])
            self.scaler.fit(combined_data_for_scaler_fit)
            logger.info(f"Node {self.node_id}: Scaler fitted on training data.")

        # Scale X_train and y_train
        X_train_scaled = self.scaler.transform(X_train.reshape(-1, self.input_features_count)).reshape(X_train.shape)
        y_train_scaled = self.scaler.transform(y_train)

        logger.info(f"Node {self.node_id}: Training LSTM with {X_train_scaled.shape[0]} sequences...")
        history = self.model.fit(X_train_scaled, y_train_scaled, epochs=epochs, batch_size=batch_size, verbose=verbose)

        self.is_trained = True
        logger.info(f"Node {self.node_id}: Training complete. Last loss: {history.history['loss'][-1]:.4f}")

        # Initialize SHAP explainer after model training
        try:
            # Use a sample of the scaled training data as background
            num_background_samples = min(100, X_train_scaled.shape[0])
            background_indices = np.random.choice(X_train_scaled.shape[0], num_background_samples, replace=False)
            self.shap_background_data = X_train_scaled[background_indices] # Store for base_values

            # SHAP explainer for reconstruction task (multi-output model)
            # The explainer will compute SHAP values for each output feature
            self.shap_explainer = shap.GradientExplainer(self.model, self.shap_background_data)
            logger.info(f"Node {self.node_id}: SHAP GradientExplainer initialized with background data shape {self.shap_background_data.shape}.")
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
            self.feature_names = feature_names # Set feature names once from training data

        # Ensure data consistency, handle missing features with 0.0 or a sensible default
        numerical_input = np.array([new_data_point_raw.get(f, 0.0) for f in feature_names], dtype=np.float32)

        self.data_buffer.append(numerical_input)

        if len(self.data_buffer) < self.sequence_length:
            return None

        current_sequence = np.array(list(self.data_buffer))

        # Scale the entire sequence using the fitted scaler
        # Reshape current_sequence to 2D for scaling (num_timesteps * num_features)
        scaled_sequence_flat = self.scaler.transform(current_sequence.reshape(-1, self.input_features_count))

        # Reshape back to 3D (sequence_length, input_features_count)
        return scaled_sequence_flat.reshape(self.sequence_length, self.input_features_count)

    async def generate_shap_plots(self, shap_values_1d, base_value_scalar, data_1d, feature_names, plot_suffix):
        """
        Generates and saves SHAP plots for a single prediction.
        - Waterfall plot
        - Force plot
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("Matplotlib not found. Skipping SHAP plot generation.")
            return

        if not self.save_shap_plots:
            logger.info(f"Node {self.node_id}: SHAP plot saving disabled.")
            return

        try:
            os.makedirs(self.plot_dir, exist_ok=True)

            # Ensure data_1d and shap_values_1d are 1D arrays and have the same length as feature_names
            if len(data_1d) != len(feature_names) or len(shap_values_1d) != len(feature_names):
                logger.error(f"Node {self.node_id}: Mismatch in lengths for SHAP plotting. "
                             f"data_1d length: {len(data_1d)}, shap_values_1d length: {len(shap_values_1d)}, "
                             f"feature_names length: {len(feature_names)}")
                return

            # Create Explanation object for single sample
            # Ensure values and data are 1D arrays for single sample explanation
            plot_explanation = shap.Explanation(
                values=shap_values_1d,
                base_values=base_value_scalar,
                data=data_1d,
                feature_names=feature_names
            )

            # Waterfall plot
            try:
                waterfall_path = os.path.join(self.plot_dir, f"waterfall_{plot_suffix}.png")
                plt.clf() # Clear current figure to avoid overlaying plots
                # shap.plots.waterfall expects a single explanation object, not an array of them.
                # If plot_explanation was created as a list of explanations, you'd iterate.
                # Here, plot_explanation is already for a single instance.
                shap.plots.waterfall(plot_explanation, show=False)
                plt.title(f"Waterfall Plot - Node {self.node_id} - {plot_suffix}")
                plt.tight_layout() # Adjust layout to prevent labels overlapping
                plt.savefig(waterfall_path, bbox_inches='tight')
                plt.close() # Close the plot to free memory
                logger.info(f"Node {self.node_id}: Saved Waterfall plot to {waterfall_path}")
            except Exception as e:
                logger.error(f"Node {self.node_id}: Error saving Waterfall plot: {e}", exc_info=True)

            # Force plot
            try:
                force_path = os.path.join(self.plot_dir, f"force_{plot_suffix}.html")
                # Force plot also expects a single explanation instance or its components
                shap.save_html(force_path, shap.force_plot(
                    base_value=plot_explanation.base_values, # Should be a scalar
                    shap_values=plot_explanation.values,     # Should be 1D array
                    features=plot_explanation.data,          # Should be 1D array
                    feature_names=plot_explanation.feature_names,
                    show=False
                ))
                logger.info(f"Node {self.node_id}: Saved Force plot to {force_path}")
            except Exception as e:
                logger.error(f"Node {self.node_id}: Error saving Force plot: {e}", exc_info=True)

            logger.info(f"Node {self.node_id}: Skipping Dependence plot (requires multiple samples).")

        except Exception as e:
            logger.error(f"Node {self.node_id}: Error in generate_shap_plots wrapper: {e}", exc_info=True)


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

        # Ensure input for prediction has a batch dimension (1, sequence_length, features)
        input_for_prediction = processed_sequence[np.newaxis, :, :] # Shape (1, 10, 21)

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

        # Extract actual metrics in original scale (last timestep of the sequence)
        actual_scaled_last_step = processed_sequence[-1] # Shape (features,)
        actual_metrics_original_scale = self.scaler.inverse_transform(actual_scaled_last_step.reshape(1, -1))[0]
        actual_metrics_dict = {self.feature_names[i]: float(actual_metrics_original_scale[i]) for i in range(len(self.feature_names))}


        try:
            predicted_scaled_next_step = self.model.predict(input_for_prediction, verbose=0)[0] # Shape (features,)

            predicted_metrics_original_scale = self.scaler.inverse_transform(predicted_scaled_next_step.reshape(1, -1))[0]
            predicted_metrics_dict = {self.feature_names[i]: float(predicted_metrics_original_scale[i]) for i in range(len(self.feature_names))}

            reconstruction_error = np.mean(np.square(predicted_scaled_next_step - actual_scaled_last_step))

            # A conceptual max error to normalize the anomaly score, needs tuning for specific datasets
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
                        # raw_shap_output_from_explainer will be a list of arrays, one for each output feature
                        # Each array shape: (batch_size, sequence_length, input_features_count)
                        raw_shap_output_from_explainer = self.shap_explainer.shap_values(input_for_prediction)
                        
                        # Process SHAP values for a multi-output autoencoder
                        # We need to aggregate SHAP values across the output neurons to get a single importance per input feature.
                        # For a single prediction (batch_size=1), we're interested in the last timestep.
                        
                        # Stack all output SHAP value arrays, then take absolute values
                        # stacked_shap_abs shape: (num_outputs, batch_size, sequence_length, input_features)
                        # Example: (21, 1, 10, 21)
                        stacked_shap_abs = np.stack([np.abs(s) for s in raw_shap_output_from_explainer if isinstance(s, np.ndarray)])
                        
                        # Sum across the output features dimension (axis=0) to get overall importance
                        # overall_shap_values_per_output_feature shape: (batch_size, sequence_length, input_features)
                        # Example: (1, 10, 21)
                        overall_shap_values_per_output_feature = np.sum(stacked_shap_abs, axis=0)
                        
                        # Get SHAP values for the LAST TIMESTEP of the sequence for the FIRST (and only) sample
                        # This should be a 1D array of shape (input_features_count,)
                        shap_values_for_last_timestep = overall_shap_values_per_output_feature[0, -1, :].astype(float)
                        
                        # The data for explanation should be the actual input data point (last timestep)
                        # Ensure this is a 1D array of floats matching the feature names
                        data_for_explanation_original_scale = self.scaler.inverse_transform(actual_scaled_last_step.reshape(1, -1))[0].astype(float)
                        
                        # The base value for an "anomaly impact" explanation could conceptually be 0.0
                        # as we are explaining the deviation from normality.
                        base_value_for_anomaly_impact = 0.0

                        # Check for shape consistency before plotting
                        if len(shap_values_for_last_timestep) != len(self.feature_names) or \
                           len(data_for_explanation_original_scale) != len(self.feature_names):
                            logger.error(f"Node {self.node_id}: SHAP values/data length mismatch with feature names before plotting. "
                                         f"SHAP len: {len(shap_values_for_last_timestep)}, Data len: {len(data_for_explanation_original_scale)}, "
                                         f"Feature names len: {len(self.feature_names)}")
                            # Fallback to no detailed root causes if shapes are wrong
                            root_cause_indicators.append({"error": "SHAP explanation failed due to shape mismatch", "details": "Cannot generate explanation."})
                        else:
                            plot_suffix = f"{int(time.time())}"
                            asyncio.create_task(self.generate_shap_plots(
                                shap_values_for_last_timestep,
                                base_value_for_anomaly_impact,
                                data_for_explanation_original_scale,
                                self.feature_names, # Use self.feature_names, which is correctly populated
                                plot_suffix
                            ))

                            # Populate root_cause_indicators based on SHAP values
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
                                # Optionally, include the raw SHAP values per output neuron if needed for deeper analysis
                                # "raw_shap_values_per_output": [s[0,-1,:].tolist() for s in raw_shap_output_from_explainer]
                            }

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

        # CORRECTED LINE: Access 'lstm_sequence_length' directly from config
        self.sequence_length = self.config.get('lstm_sequence_length', sequence_length)

        self.node_detectors = {}

        self.all_features = self.config.get('lstm_features', [])
        self.numerical_features_for_lstm = [] # Will be populated after loading training data
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
            "training_data_file": "baseline_network_metrics.csv", # NEW: For training
            "testing_data_file": "rural_network_metrics.csv",     # NEW: For pre-live testing
            "monitor_ns3_metrics_file": "rural_network_metrics.csv" # Kept for general reference, but training/testing explicitly defined
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
                sequence_length=self.sequence_length,
                anomaly_threshold=self.config.get('anomaly_threshold', 0.05)
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
            node_id=f"temp_opt_{node_id}", # type: ignore
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
            # Ensure scaler is fitted for the temporary detector
            if not hasattr(temp_detector.scaler, 'min_') or not hasattr(temp_detector.scaler, 'scale_'):
                combined_data_for_scaler_fit = np.vstack([X_train.reshape(-1, self.input_features_count), y_train])
                temp_detector.scaler.fit(combined_data_for_scaler_fit)

            X_train_scaled = temp_detector.scaler.transform(X_train.reshape(-1, self.input_features_count)).reshape(X_train.shape)
            y_train_scaled = temp_detector.scaler.transform(y_train)

            temp_detector.train_model(X_train_scaled, y_train_scaled, epochs=5, verbose=0) # Pass scaled data

            if not temp_detector.is_trained:
                return float('inf')

            predictions = temp_detector.model.predict(X_train_scaled, verbose=0)
            loss = mean_squared_error(y_train_scaled, predictions)
        except Exception as e:
            logger.error(f"Node {node_id}: Error during SSA objective function: {e}", exc_info=True)
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
        Loads initial training data for all nodes from the specified CSV.
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

            # Filter for numerical features that are actually present in the dataframe
            self.numerical_features_for_lstm = [
                f for f in self.config['lstm_features'] if f in df_renamed.columns and f not in ['operational', 'node_type', 'current_time']
            ]

            if not self.numerical_features_for_lstm:
                logger.error("No numerical features found for LSTM training after mapping. Check config 'lstm_features' and CSV columns.")
                sys.exit(1)

            self.input_features_count = len(self.numerical_features_for_lstm)
            self.all_features = self.numerical_features_for_lstm # Update all_features for consistency

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
            logger.error(f"Error: Initial training data file not found at {file_path}. Please ensure '{file_path}' exists.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error loading and preparing initial training data: {e}", exc_info=True)
            sys.exit(1)

    async def perform_pre_live_testing(self):
        """
        Performs a pre-live testing phase using a separate CSV file
        to evaluate SHAP and anomaly detection.
        """
        testing_file = self.config['testing_data_file']
        logger.info("=" * 80)
        logger.info(f"STARTING PRE-LIVE TESTING PHASE (SHAP & ANOMALY DETECTION) from {testing_file}")
        logger.info("=" * 80)

        try:
            df = pd.read_csv(testing_file)
            df['NodeId'] = df['NodeId'].apply(lambda x: f"node_{int(x):02d}")
            # Map columns to match the features used by LSTM
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

            test_anomalies_detected = 0
            total_test_samples = 0

            # Ensure self.all_features is correctly set before processing test data
            # This should have been set during load_and_prepare_initial_training_data
            if not self.all_features:
                logger.error("Features not initialized. Cannot perform pre-live testing. Exiting.")
                return

            for index, row in df_renamed.iterrows():
                total_test_samples += 1
                node_id = row['NodeId']

                detector = self.node_detectors.get(node_id)
                if not detector or not detector.is_trained:
                    logger.debug(f"No trained detector for {node_id} or model not loaded. Skipping test data point.")
                    continue

                # Prepare the raw data point dictionary for the detector, using numerical_features_for_lstm
                raw_data_point = {feature: row.get(feature, 0.0) for feature in self.numerical_features_for_lstm}

                anomaly_results = await detector.predict_anomaly(raw_data_point, self.numerical_features_for_lstm)

                if anomaly_results["status"] == "Anomaly detected":
                    test_anomalies_detected += 1
                    logger.warning(
                        f"PRE-LIVE TEST Anomaly detected for {node_id} at sim_time "
                        f"{row.get('current_time', 'N/A')}. Score: {anomaly_results['anomaly_score']:.4f}. "
                        f"Root Causes: {anomaly_results['root_cause_indicators']}"
                    )
                else:
                    logger.debug(f"PRE-LIVE TEST: No anomaly for {node_id} at sim_time {row.get('current_time', 'N/A')}.")

                # Simulate processing time for realism
                await asyncio.sleep(0.001)

            logger.info("=" * 80)
            logger.info(f"PRE-LIVE TESTING COMPLETE. Total Samples Processed: {total_test_samples}, Anomalies Detected: {test_anomalies_detected}")
            logger.info("=" * 80)

        except FileNotFoundError:
            logger.error(f"Pre-live testing data file not found: {testing_file}. Skipping pre-live testing.")
        except Exception as e:
            logger.error(f"Error during pre-live testing phase: {e}", exc_info=True)


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
                description=anomaly_results.get('explanation', f"Anomaly detected for node {node_id}"), # Use .get()
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
                "source_agent": anomaly_alert.source_agent,
                "severity_classification": anomaly_results.get("severity_classification", "N/A"),
                "root_cause_indicators": anomaly_results.get("root_cause_indicators", []),
                "recommended_actions": anomaly_results.get("recommended_actions", [])
            }
            try:
                await self.a2a_publisher_socket.send_json(message_to_healing)
                logger.info(f"Node {node_id}: A2A: Published anomaly alert (Status: {anomaly_results['status']}, Score: {anomaly_results['anomaly_score']:.4f})")
            except Exception as e:
                logger.error(f"Node {node_id}: Failed to send alert to Healing Agent: {e}", exc_info=True) # Added exc_info
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
                                                # Ensure node_id_from_msg is correctly formatted (e.g., 'node_00')
                                                if node_id_from_msg.startswith('node_'):
                                                    # Make sure 'current_time' is available for logging and alerts
                                                    if 'simulation_time' in msg['content']:
                                                        node_metrics_data['current_time'] = msg['content']['simulation_time']
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
        1. Loads initial training data for all nodes from specified training_data_file.
        2. Builds and trains/loads LSTM models for each node.
        3. Optimizes hyperparameters using SSA for each node if training.
        4. Performs pre-live testing using testing_data_file.
        5. Enters a loop to receive live data from Monitor Agent's file and perform predictions.
        """
        logger.info("Calculation Agent started. Performing initial setup (training/loading models for all nodes)...")

        # Load initial training data from the specified training file
        node_training_data = await self.load_and_prepare_initial_training_data(self.config['training_data_file'])

        if self.input_features_count == 0 or not self.numerical_features_for_lstm:
            logger.error("No numerical features identified from training data. Cannot initialize detectors. Exiting.")
            sys.exit(1)

        self._initialize_detectors(self.input_features_count, self.numerical_features_for_lstm)

        training_tasks = []
        for node_id in self.node_ids:
            detector = self.node_detectors[node_id]
            if not self.config['train_on_startup'] and detector.load_model():
                logger.info(f"Node {node_id}: Loaded existing model. Skipping retraining.")
            else:
                X_train_np, y_train_np = node_training_data.get(node_id, (np.array([]), np.array([])))

                if X_train_np.size > 0:
                    training_tasks.append(
                        asyncio.create_task(
                            self.optimize_lstm_with_ssa(node_id, X_train_np, y_train_np)
                        )
                    )
                else:
                    logger.warning(f"Node {node_id}: No sufficient training data available. Detector for this node will not be trained.")
                    # Mark as not trained if data is insufficient for initial setup
                    detector.is_trained = False

        if training_tasks:
            results = await asyncio.gather(*training_tasks, return_exceptions=True)
            for i, result in enumerate(results):
                # We need to map the result back to the correct node_id.
                # A more robust way might be to pass node_id with the task, or ensure order.
                # For simplicity, assuming training_tasks order matches node_ids order here.
                # If a task failed, its detector might not have been trained, check .is_trained
                # after the gather.
                current_node_id = self.node_ids[i] # This relies on `training_tasks` order
                if isinstance(result, Exception):
                    logger.error(f"Error during training/optimization for node {current_node_id}: {result}", exc_info=True)
                else:
                    detector = self.node_detectors[current_node_id]
                    if detector.is_trained: # Only save if training was successful
                        detector.save_model()
        else:
            logger.warning("No nodes had sufficient training data or models were loaded. Skipping mass training phase.")


        logger.info("Calculation Agent: Initial setup complete for all monitored nodes.")

        # --- Perform pre-live testing phase ---
        await self.perform_pre_live_testing()


        logger.info("Calculation Agent: Entering live data monitoring phase. Waiting for data from Monitor Agent...")

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
            "training_data_file": "baseline_network_metrics.csv",
            "testing_data_file": "rural_network_metrics.csv",
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
