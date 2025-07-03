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
import sqlite3
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout, InputLayer
from tensorflow.keras.optimizers import Adam
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
import joblib
import os
import zmq.asyncio
import sys
from functools import partial
import shap
import matplotlib.pyplot as plt # Keep this import here for general availability in module scope
import glob


# Set up logging for CalculationAgent
# This must be at the top, immediately after imports, to ensure 'logger' is defined.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configure TensorFlow to use only CPU, to avoid potential GPU conflicts in certain environments
# This must be done BEFORE any TensorFlow operation or Keras model creation.
try:
    tf.config.set_visible_devices([], 'GPU')
    logger.info("TensorFlow configured to use CPU only.")
except Exception as e:
    logger.warning(f"Could not configure TensorFlow to use CPU only. May proceed with default device settings. Error: {e}")


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

def convert_numpy_types(obj):
    """Convert numpy types to Python native types for JSON serialization."""
    if isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    return obj

def find_existing_anomaly_id(node_id, detection_timestamp, db_path='rag_knowledge_base.db'):
    """
    Searches for an existing anomaly in the database within a time window.
    Returns the anomaly_id if found, None otherwise.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
                
               # Search for anomalies within ±10 seconds of detection time
        query = """
        SELECT anomaly_id FROM Anomalies
        WHERE node_id = ? AND ABS(timestamp - ?) < 10
        ORDER BY ABS(timestamp - ?) ASC LIMIT 1;
        """
        cursor.execute(query, (node_id, detection_timestamp, detection_timestamp))
        result = cursor.fetchone()
        conn.close()
                
        if result:
            logger.info(f"Found existing anomaly_id: {result[0]} for node {node_id} at timestamp {detection_timestamp}")
            return result[0]
        else:
            logger.debug(f"No existing anomaly found for node {node_id} at timestamp {detection_timestamp}")
            return None
                    
    except sqlite3.Error as e:
        logger.error(f"Database error while searching for existing anomaly: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error while searching for existing anomaly: {e}")
        return None

def insert_new_anomaly_to_database(anomaly_id, node_id, timestamp, anomaly_results, db_path='rag_knowledge_base.db'):
    """
    Inserts a newly detected anomaly into the database.
    Returns True if successful, False otherwise.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
                
                # Insert new anomaly record
        cursor.execute("""
            INSERT OR REPLACE INTO Anomalies (anomaly_id, timestamp, node_id, severity, description)
            VALUES (?, ?, ?, ?, ?)
            """, (
                    anomaly_id,
                    timestamp,
                    node_id,
                    anomaly_results.get('severity_classification', 'Unknown'),
                    anomaly_results.get('description', f"Real-time anomaly detected for {node_id}")
        ))
                
        conn.commit()
        conn.close()
        logger.info(f"Successfully inserted new anomaly {anomaly_id} into database")
        return True
                
    except sqlite3.Error as e:
        logger.error(f"Database error while inserting new anomaly: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error while inserting new anomaly: {e}")
        return False

def generate_database_compatible_anomaly_id(node_id, timestamp):
    """
    Generates an anomaly_id in the format expected by the healing agent database.
    Format: ANOM_<timestamp>_<node_id>_<random_suffix>
    """
    import uuid
    random_suffix = uuid.uuid4().hex[:6]
    return f"ANOM_{int(timestamp)}_{node_id}_{random_suffix}"
        # Send alert to Healing Agent (via PUB/SUB)
        # Send alert to Healing Agent (via PUB/SUB) - ONLY for anomalies

# --- LSTM Model for Anomaly Detection (Robust Keras Sequential Model) ---
# This class will encapsulate a Keras Sequential model, ensuring its input shape is defined.
class LSTMAnomalyModel:
    def __init__(self, input_size=None, hidden_size=None, num_layers=2, dropout_rate=0.2, sequence_length=None):
        if input_size is None or hidden_size is None or sequence_length is None:
            raise ValueError("input_size, hidden_size, and sequence_length must be provided to LSTMAnomalyModel.")

        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout_rate = dropout_rate
        self.sequence_length = sequence_length

        # Create the model with explicit input shape
        self._model = Sequential()
        
        # Add input layer with explicit shape
        self._model.add(InputLayer(input_shape=(self.sequence_length, self.input_size)))
        
        # Add LSTM layers
        for i in range(self.num_layers):
            return_sequences = (i < self.num_layers - 1)
            self._model.add(LSTM(self.hidden_size, activation='relu', return_sequences=return_sequences))
            self._model.add(Dropout(self.dropout_rate))
        
        # Output layer
        self._model.add(Dense(self.input_size))
        
        logger.debug(f"LSTMAnomalyModel created. Input shape: {self._model.input_shape}")

    # Update predict method to handle input correctly:
    def predict(self, X, *args, **kwargs):
        # Ensure X has the correct shape (batch_size, sequence_length, features)
        if len(X.shape) == 2:
            X = X.reshape(1, X.shape[0], X.shape[1])
        elif len(X.shape) == 3 and X.shape[0] == 1:
            pass  # Already correct shape
        else:
            raise ValueError(f"Unexpected input shape: {X.shape}")
        
        return self._model.predict(X, *args, **kwargs)

    # Delegate Keras methods to the internal _model instance
    def compile(self, *args, **kwargs):
        self._model.compile(*args, **kwargs)

    def fit(self, *args, **kwargs):
        return self._model.fit(*args, **kwargs)

    def predict(self, *args, **kwargs):
        return self._model.predict(*args, **kwargs)
    
    def summary(self):
        self._model.summary()

    def save(self, filepath):
        """Saves the internal Keras model (using Keras v3 recommended API)."""
        self._model.save(filepath)

    # Property to allow external access to the Keras input_shape
    @property
    def input_shape(self):
        return self._model.input_shape


# --- LSTM Anomaly Detector for a Single Node ---
class LSTMAnomalyDetector:
    """
    Manages the LSTM model, data preprocessing, training, and anomaly prediction
    for a single network node.
    """
    def __init__(self, node_id, input_features_count, sequence_length=5, anomaly_threshold_percentile=99, save_shap_plots=True, plot_dir="shap_plots"):
        self.node_id = node_id
        self.input_features_count = input_features_count
        self.sequence_length = sequence_length
        # Changed from fixed anomaly_threshold to percentile for dynamic calculation
        self.anomaly_threshold_percentile = anomaly_threshold_percentile 
        self.dynamic_anomaly_threshold = 0.0 # This will be set after training
        self.model = None # This will be an instance of LSTMAnomalyModel
        self.scaler = MinMaxScaler()
        self.data_buffer = deque(maxlen=sequence_length)
        self.shap_explainer = None
        self._last_shap_model_version = None
        self.is_trained = False
        self.feature_names = None # Stores actual feature names from training data
        self.save_shap_plots = save_shap_plots
        self.plot_dir = os.path.join(plot_dir, node_id)
        self.shap_background_data = None # Store background data for SHAP base_values

        # Corrected: Change model file extension to .keras
        self.model_path = os.path.join(MODEL_DIR, f"{node_id}_lstm_model.weights.h5")
        self.scaler_path = os.path.join(MODEL_DIR, f"{node_id}_scaler.pkl")
        self.threshold_path = os.path.join(MODEL_DIR, f"{node_id}_threshold.json") # Path for dynamic threshold

        if self.save_shap_plots:
            os.makedirs(self.plot_dir, exist_ok=True)
            logger.info(f"Node {self.node_id}: SHAP plots will be saved to {self.plot_dir}")

    def build_model(self, hidden_size=64, learning_rate=0.001, num_layers=2, dropout_rate=0.2):
        """Builds and compiles the LSTM model."""
        if self.input_features_count == 0:
            raise ValueError("input_features_count must be set before building the model.")

        # Instantiate the LSTMAnomalyModel, which now creates a Sequential model with explicit InputLayer
        self.model = LSTMAnomalyModel(
            input_size=self.input_features_count,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout_rate=dropout_rate,
            sequence_length=self.sequence_length
        )
        
        # Revert to passing the instantiated Adam optimizer directly.
        # This is the standard way to configure the learning rate.
        self.model.compile(optimizer=Adam(learning_rate=learning_rate), loss='mse')        
        logger.info(f"Node {self.node_id}: LSTM model built and compiled with hidden_size={hidden_size}, lr={learning_rate}, layers={num_layers}")

    def save_model(self):
        """Saves the trained LSTM model, scaler, dynamic threshold, AND hyperparameters."""
        os.makedirs(MODEL_DIR, exist_ok=True)
        try:
            # Save the LSTM model weights only — safer than saving full model
            if self.model:
                self.model._model.save_weights(self.model_path)
                logger.info(f"Node {self.node_id}: Saved LSTM model weights to {self.model_path}")

            if self.scaler:
                joblib.dump(self.scaler, self.scaler_path)
                logger.info(f"Node {self.node_id}: Saved scaler to {self.scaler_path}")

        # ✅ FIXED: Save threshold AND hyperparameters with correct extraction
            if self.dynamic_anomaly_threshold is not None:
                threshold_and_hyperparams = {
                'dynamic_anomaly_threshold': float(self.dynamic_anomaly_threshold),
                'hyperparameters': {
                    'input_features_count': self.input_features_count,
                    'sequence_length': self.sequence_length,
                    'hidden_size': self.model.hidden_size if self.model else 64,  # ✅ CORRECT extraction
                    'num_layers': self.model.num_layers if self.model else 2,     # ✅ CORRECT extraction  
                    'dropout_rate': self.model.dropout_rate if self.model else 0.2  # ✅ CORRECT extraction
                }
            }

                with open(self.threshold_path, 'w') as f:
                    json.dump(threshold_and_hyperparams, f, indent=2)
                    logger.info(f"Node {self.node_id}: Saved threshold and hyperparameters: hidden_size={threshold_and_hyperparams['hyperparameters']['hidden_size']}")

        except Exception as e:
            logger.error(f"Node {self.node_id}: Error saving model, scaler, or threshold: {e}", exc_info=True)

    def load_model(self):
        """FIXED: Load model with hyperparameters from updated threshold file"""
        try:
        # Check if files exist
            if not (os.path.exists(self.model_path) and 
                    os.path.exists(self.scaler_path) and 
                    os.path.exists(self.threshold_path)):
                logger.info(f"Node {self.node_id}: Model files missing")
                return False

        # ✅ LOAD HYPERPARAMETERS from fixed threshold file
            with open(self.threshold_path, 'r') as f:
                threshold_data = json.load(f)

            if 'hyperparameters' not in threshold_data:
                logger.error(f"Node {self.node_id}: No hyperparameters in threshold file - run fix_all_models.py first")
                return False

            hyperparams = threshold_data['hyperparameters']
            hidden_size = hyperparams['hidden_size']
            num_layers = hyperparams['num_layers'] 
            dropout_rate = hyperparams['dropout_rate']

            logger.info(f"Node {self.node_id}: Loading with hidden_size={hidden_size}, layers={num_layers}")

        # ✅ CREATE MODEL with correct hyperparameters
            self.model = LSTMAnomalyModel(
            input_size=self.input_features_count,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout_rate=dropout_rate,
            sequence_length=self.sequence_length
            )

        # Compile and load weights
            self.model.compile(optimizer=Adam(learning_rate=0.001), loss='mse')
            self.model._model.load_weights(self.model_path)

        # Load scaler and threshold
            self.scaler = joblib.load(self.scaler_path)
            self.dynamic_anomaly_threshold = threshold_data['dynamic_anomaly_threshold']

            self.is_trained = True
            logger.info(f"Node {self.node_id}: ✅ Model loaded successfully!")
            return True

        except Exception as e:
            logger.error(f"Node {self.node_id}: ❌ Failed to load model: {e}")
            return False


    def _extract_actual_hyperparams_from_weights(self):
        """ENHANCED: Extract actual hyperparameters from weights file with comprehensive search"""
        try:
            import h5py
        
            with h5py.File(self.model_path, 'r') as f:
            # ✅ COMPREHENSIVE weight inspection
                def find_all_lstm_weights(group, path="", weights_info=None):
                    if weights_info is None:
                        weights_info = {'kernels': [], 'biases': [], 'recurrent_kernels': []}
                
                    for key in group.keys():
                        current_path = f"{path}/{key}" if path else key
                    
                        if isinstance(group[key], h5py.Group):
                            find_all_lstm_weights(group[key], current_path, weights_info)
                        elif isinstance(group[key], h5py.Dataset):
                            dataset = group[key]
                            shape = dataset.shape
                        
                        # Categorize weight types
                            if 'kernel' in key.lower() and 'recurrent' not in key.lower():
                                weights_info['kernels'].append({'path': current_path, 'shape': shape})
                            elif 'recurrent_kernel' in key.lower():
                                weights_info['recurrent_kernels'].append({'path': current_path, 'shape': shape})
                            elif 'bias' in key.lower():
                                weights_info['biases'].append({'path': current_path, 'shape': shape})
                
                    return weights_info

                weights_info = find_all_lstm_weights(f)
            
                logger.info(f"Node {self.node_id}: Found {len(weights_info['kernels'])} kernels, "
                            f"{len(weights_info['recurrent_kernels'])} recurrent kernels, "
                            f"{len(weights_info['biases'])} biases")

            # ✅ EXTRACT hyperparameters from first LSTM kernel
                if weights_info['kernels']:
                    first_kernel = weights_info['kernels'][0]
                    kernel_shape = first_kernel['shape']
                
                    if len(kernel_shape) == 2 and kernel_shape[0] == self.input_features_count:
                    # LSTM kernel shape: [input_size, hidden_size * 4]
                        hidden_times_4 = kernel_shape[1]
                        inferred_hidden_size = hidden_times_4 // 4
                    
                    # ✅ DETERMINE number of layers from number of kernels
                        num_layers = len([k for k in weights_info['kernels'] if 'lstm' in k['path'].lower()])
                        if num_layers == 0:
                            num_layers = max(1, len(weights_info['kernels']) // 2)  # Estimate
                    
                        hyperparams = {
                        'hidden_size': inferred_hidden_size,
                        'num_layers': num_layers,
                        'dropout_rate': 0.2  # Default, can't be inferred from weights
                        }
                    
                        logger.info(f"Node {self.node_id}: ✅ Successfully extracted: "
                                    f"hidden_size={inferred_hidden_size}, layers={num_layers}")
                        return hyperparams
                    else:
                        logger.warning(f"Node {self.node_id}: Unexpected kernel shape: {kernel_shape}")
            
            # ✅ FALLBACK: Try recurrent kernels
                if weights_info['recurrent_kernels']:
                    first_recurrent = weights_info['recurrent_kernels'][0]
                    recurrent_shape = first_recurrent['shape']
                
                    if len(recurrent_shape) == 2:
                    # Recurrent kernel shape: [hidden_size, hidden_size * 4]
                        hidden_size = recurrent_shape[0]
                        num_layers = len(weights_info['recurrent_kernels'])
                    
                        hyperparams = {
                        'hidden_size': hidden_size,
                        'num_layers': num_layers,
                        'dropout_rate': 0.2
                        }
                    
                        logger.info(f"Node {self.node_id}: ✅ Extracted from recurrent: "
                                    f"hidden_size={hidden_size}, layers={num_layers}")
                        return hyperparams

                logger.warning(f"Node {self.node_id}: Could not extract hyperparameters from any weights")
                return None

        except Exception as e:
            logger.error(f"Node {self.node_id}: Error extracting hyperparameters: {e}")
            return None

    def _infer_hidden_size_from_weights_enhanced(self):
        """Enhanced method to infer hidden_size from saved weight file shapes."""
        try:
            import h5py
            with h5py.File(self.model_path, 'r') as f:
            # More comprehensive search for LSTM kernels
                def find_lstm_kernel_recursive(group, path=""):
                    for key in group.keys():
                        current_path = f"{path}/{key}" if path else key
                        if isinstance(group[key], h5py.Group):
                            result = find_lstm_kernel_recursive(group[key], current_path)
                            if result is not None:
                                return result
                        elif isinstance(group[key], h5py.Dataset):
                        # Look for LSTM kernel patterns (more comprehensive)
                            key_lower = key.lower()
                            path_lower = current_path.lower()
                        
                            if (('lstm' in path_lower or 'rnn' in path_lower) and 
                                ('kernel' in key_lower or 'weight' in key_lower) and
                                'bias' not in key_lower):
                                return group[key]
                    return None

                kernel_weights = find_lstm_kernel_recursive(f)
            
                if kernel_weights is not None:
                    kernel_shape = kernel_weights.shape
                    logger.info(f"Node {self.node_id}: Found LSTM kernel with shape {kernel_shape}")
                
                # LSTM kernel shape: [input_size, hidden_size * 4]
                    if len(kernel_shape) == 2 and kernel_shape[0] == self.input_features_count:
                        hidden_times_4 = kernel_shape[1]
                        inferred_hidden_size = hidden_times_4 // 4
                        logger.info(f"Node {self.node_id}: ✅ Inferred hidden_size={inferred_hidden_size} from shape {kernel_shape}")
                        return inferred_hidden_size
                    else:
                        logger.warning(f"Node {self.node_id}: Unexpected kernel shape: {kernel_shape}")
                        return 64
                else:
                    logger.warning(f"Node {self.node_id}: Could not find LSTM kernel in weights file")
                    return 64

        except Exception as e:
            logger.warning(f"Node {self.node_id}: Error inferring hidden size: {e}")
            return 64

    def train_model(self, X_train, y_train, epochs=1, batch_size=32, verbose=0):
        """
        Trains the LSTM model and calculates the dynamic anomaly threshold
        based on training data reconstruction errors.
        """
        if X_train.size == 0 or y_train.size == 0:
            logger.warning(f"Node {self.node_id}: Skipping training, X_train or y_train is empty.")
            self.is_trained = False
            return

        # Fit scaler if not already fitted (e.g., if loading a new model or first training)
        if not hasattr(self.scaler, 'min_') or not hasattr(self.scaler, 'scale_'):
            combined_data_for_scaler_fit = np.vstack([X_train.reshape(-1, self.input_features_count), y_train])
            self.scaler.fit(combined_data_for_scaler_fit)
            logger.info(f"Node {self.node_id}: Scaler fitted on training data of shape {combined_data_for_scaler_fit.shape}.")

        X_train_scaled = self.scaler.transform(X_train.reshape(-1, self.input_features_count)).reshape(X_train.shape)
        y_train_scaled = self.scaler.transform(y_train)

        logger.info(f"Node {self.node_id}: Training LSTM with {X_train_scaled.shape[0]} sequences...")
        history = self.model.fit(X_train_scaled, y_train_scaled, epochs=epochs, batch_size=batch_size, verbose=verbose)

        self.is_trained = True
        logger.info(f"Node {self.node_id}: Training complete. Last loss: {history.history['loss'][-1]:.4f}")

        # --- Calculate Dynamic Anomaly Threshold ---
        # Predict on training data to get reconstruction errors for "normal" data
        train_predictions_scaled = self.model.predict(X_train_scaled, verbose=0)
        
        # Calculate reconstruction error for each training sample
        # Note: mean_squared_error by default averages over all elements.
        # To get individual sample errors, you'd calculate element-wise squared difference and then mean per sample.
        
        # Reshape for element-wise comparison if necessary (should already be (N_samples, features))
        if len(y_train_scaled.shape) == 3: # If y_train_scaled is (samples, sequence_length, features)
            # Take the last timestep's target and prediction for error calculation, or adapt as needed
            # For autoencoder predicting next step, y_train_scaled should be (samples, features)
            logger.warning(f"Unexpected y_train_scaled shape in train_model for threshold: {y_train_scaled.shape}")
            # As a fallback, assume y_train_scaled is already the target for the next step.
            # If your model truly predicts sequences, this needs adjustment.
            # Assuming y_train_scaled is (num_samples, num_features) based on original problem setup
            pass

        # Calculate reconstruction errors for each training sample (element-wise squared diff, then mean per sample)
        reconstruction_errors = np.mean(np.square(y_train_scaled - train_predictions_scaled), axis=1) # Mean across features

        # Set the dynamic threshold as the specified percentile of these errors
        self.dynamic_anomaly_threshold = np.percentile(reconstruction_errors, self.anomaly_threshold_percentile)
        logger.info(f"Node {self.node_id}: Dynamic anomaly threshold set to {self.dynamic_anomaly_threshold:.6f} "
                    f"(at {self.anomaly_threshold_percentile}th percentile of training reconstruction errors).")

        # Initialize SHAP explainer after model training
        try:
            num_background_samples = min(100, X_train_scaled.shape[0])
            background_indices = np.random.choice(X_train_scaled.shape[0], num_background_samples, replace=False)
            self.shap_background_data = X_train_scaled[np.random.choice(X_train_scaled.shape[0])][np.newaxis, :, :]

            # SHAP explainer needs the actual Keras model object
            self.shap_explainer = shap.GradientExplainer(self.model._model, self.shap_background_data)
            logger.info(f"Node {self.node_id}: SHAP explainer initialized with background data shape {self.shap_background_data.shape}.")
        except Exception as e:
            logger.error(f"Node {self.node_id}: Error initializing SHAP Explainer: {e}", exc_info=True)
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
        scaled_sequence_flat = self.scaler.transform(current_sequence.reshape(-1, self.input_features_count))

        # Reshape back to 3D (sequence_length, input_features_count)
        return scaled_sequence_flat.reshape(self.sequence_length, self.input_features_count)

    async def generate_shap_plots(self, shap_values_1d: np.ndarray, base_value_scalar: float, data_1d: np.ndarray, feature_names: List[str], plot_suffix: str):
        """
        Generates SHAP plots with fallback to alternative gradient bar plot.
        """
        if not self.save_shap_plots:
            return

        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import matplotlib.colors as mcolors
            
            os.makedirs(self.plot_dir, exist_ok=True)

            # Try standard SHAP plotting first
            try:
                # Your existing SHAP plotting code here...
                plot_explanation = shap.Explanation(
                    values=shap_values_1d,
                    base_values=base_value_scalar,
                    data=data_1d,
                    feature_names=feature_names
                )
                
                # Waterfall plot
                waterfall_path = os.path.join(self.plot_dir, f"waterfall_{plot_suffix}.png")
                plt.figure(figsize=(10, 6))
                shap.plots.waterfall(plot_explanation, show=False)
                plt.title(f"Waterfall Plot - Node {self.node_id} - {plot_suffix}")
                plt.tight_layout()
                plt.savefig(waterfall_path, bbox_inches='tight', dpi=150)
                plt.close()
                
                logger.info(f"Node {self.node_id}: Successfully saved SHAP plots")
                
            except Exception as shap_error:
                logger.warning(f"Node {self.node_id}: SHAP plotting failed ({shap_error}), using alternative gradient bar plot")
                
                # **ALTERNATIVE GRADIENT BAR PLOT**
                await self.create_alternative_gradient_plot(shap_values_1d, feature_names, plot_suffix)
                
        except Exception as e:
            logger.error(f"Node {self.node_id}: Complete plotting failure: {e}", exc_info=True)

    async def create_alternative_gradient_plot(self, shap_values: np.ndarray, feature_names: List[str], plot_suffix: str):
        """
        Creates alternative gradient bar plot when SHAP plotting fails.
        Red-to-green gradient representing degree of deviation.
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib.colors as mcolors
            
            # Normalize SHAP values for color mapping
            max_abs_value = max(abs(shap_values)) if len(shap_values) > 0 else 1.0
            norm = plt.Normalize(vmin=-max_abs_value, vmax=max_abs_value)
            
            # Create red-to-green colormap
            cmap = mcolors.LinearSegmentedColormap.from_list(
                'deviation_gradient', 
                ['red', 'yellow', 'green']
            )
            
            # Map SHAP values to colors based on deviation
            colors = cmap(norm(shap_values))
            
            # Sort features by absolute importance
            sorted_indices = np.argsort(np.abs(shap_values))[::-1]
            sorted_features = [feature_names[i] for i in sorted_indices]
            sorted_values = shap_values[sorted_indices]
            sorted_colors = colors[sorted_indices]
            
            # Create alternative bar plot
            plt.figure(figsize=(12, 8))
            bars = plt.barh(range(len(sorted_features)), sorted_values, color=sorted_colors)
            
            # Customize plot
            plt.yticks(range(len(sorted_features)), sorted_features)
            plt.xlabel('Feature Impact (SHAP Value)')
            plt.ylabel('Features')
            plt.title(f'Alternative Feature Importance - Node {self.node_id} - {plot_suffix}')
            plt.grid(True, axis='x', linestyle='--', alpha=0.7)
            
            # Add value labels on bars
            for i, (bar, value) in enumerate(zip(bars, sorted_values)):
                plt.text(value + (0.01 if value >= 0 else -0.01), i, 
                        f'{value:.3f}', va='center', 
                        ha='left' if value >= 0 else 'right')
            
            # Add colorbar legend
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
            sm.set_array([])
            cbar = plt.colorbar(sm)
            cbar.set_label('Impact Direction (Red=Negative, Green=Positive)')
            
            plt.tight_layout()
            
            # Save alternative plot
            alt_plot_path = os.path.join(self.plot_dir, f"alternative_gradient_{plot_suffix}.png")
            plt.savefig(alt_plot_path, bbox_inches='tight', dpi=150)
            plt.close()
            
            logger.info(f"Node {self.node_id}: Saved alternative gradient plot to {alt_plot_path}")
            
        except Exception as e:
            logger.error(f"Node {self.node_id}: Alternative plotting also failed: {e}")




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
        
        # Ensure dynamic_anomaly_threshold is set before prediction
        if self.dynamic_anomaly_threshold == 0.0:
            logger.warning(f"Node {self.node_id}: Dynamic anomaly threshold is 0.0. Model might not have been trained correctly or threshold not calculated. Aborting prediction.")
            default_return["status"] = "Threshold not set"
            default_return["actual_metrics"] = {f: input_data_raw.get(f, 0.0) for f in all_feature_names}
            return default_return


        processed_sequence = self.preprocess_input(input_data_raw, all_feature_names)

        if processed_sequence is None:
            default_return["status"] = "Insufficient data for prediction"
            default_return["actual_metrics"] = {f: input_data_raw.get(f, 0.0) for f in all_feature_names}
            return default_return

        # Ensure input for prediction has a batch dimension (1, sequence_length, features)
        input_for_prediction = processed_sequence[np.newaxis, :, :] # Shape (1, 10, 17)

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

            # Calculate reconstruction error for the current data point
            reconstruction_error = np.mean(np.square(predicted_scaled_next_step - actual_scaled_last_step))
            # Normalize anomaly score based on dynamic threshold 
            # A simple linear scaling, capping at 1.0
            if (reconstruction_error>25) :
                reconstruction_er = np.sqrt(reconstruction_error)/100
            else:
                reconstruction_er=0
            anomaly_score = min(1.0, reconstruction_er / (self.dynamic_anomaly_threshold if self.dynamic_anomaly_threshold > 0 else 0.0))
            is_anomaly = anomaly_score> 0

            confidence_level = 100 * (1 - anomaly_score)

            if is_anomaly:
                status = "Anomaly detected"
                logger.info(f"Node {self.node_id}: Anomaly alert! Reconstruction Error: {reconstruction_error:.6f}, Threshold: {self.dynamic_anomaly_threshold:.6f}, Score: {anomaly_score:.4f}. Generating SHAP explanation...")
                if self.shap_explainer is None:
                    logger.warning(f"Node {self.node_id}: SHAP explainer not initialized. Skipping SHAP explanation.")
                    root_cause_indicators = [{"error": "SHAP explainer not initialized", "details": "Cannot generate explanation."}]
                    affected_components = ["Unknown"]
                    severity_classification = "Low"
                    recommended_actions = ["Investigate manually."]
                    
                else:
                    try:
                        if self.shap_explainer is None or self._last_shap_model_version != id(self.model._model):
                            self._last_shap_model_version = None
                            self.shap_explainer = shap.GradientExplainer(self.model._model, self.shap_background_data)
                            self._last_shap_model_version = id(self.model._model)
                            logger.info(f"Node {self.node_id}: Rebuilt SHAP explainer post-predict.")

                        raw_shap_output_from_explainer = self.shap_explainer.shap_values(input_for_prediction)

                        logger.info(f"Node {self.node_id}: SHAP raw output type: {type(raw_shap_output_from_explainer)}")

                        # ✅ Process SHAP output safely — list or array
                        if isinstance(raw_shap_output_from_explainer, list):
                            raw_shap_output_list = raw_shap_output_from_explainer
                            stacked_shap_abs = np.stack([np.abs(s) for s in raw_shap_output_list if isinstance(s, np.ndarray)])
                            overall_shap_values_per_output_feature = np.sum(stacked_shap_abs, axis=0)

                            # ✅ Defensive: Check shape
                            if overall_shap_values_per_output_feature.shape[0] == 1 and overall_shap_values_per_output_feature.ndim == 3:
                                shap_values_for_last_timestep = overall_shap_values_per_output_feature[0, -1, :]
                            else:
                                raise ValueError(f"Unexpected SHAP shape from list: {overall_shap_values_per_output_feature.shape}")

                        elif isinstance(raw_shap_output_from_explainer, np.ndarray):
                            logger.info(f"Node {self.node_id}: SHAP raw ndarray shape: {raw_shap_output_from_explainer.shape}")

                            if raw_shap_output_from_explainer.ndim == 4:
                                # Take first output class (if multiple), last timestep, all features
                                shap_values_for_last_timestep = raw_shap_output_from_explainer[0, -1, 0, :]
                            elif raw_shap_output_from_explainer.ndim == 3:
                                shap_values_for_last_timestep = raw_shap_output_from_explainer[0, -1, :]
                            elif raw_shap_output_from_explainer.ndim == 2:
                                shap_values_for_last_timestep = raw_shap_output_from_explainer[-1, :]
                            else:
                                raise ValueError(f"Unexpected SHAP ndarray shape: {raw_shap_output_from_explainer.shape}")

                        else:
                            raise ValueError("SHAP output is invalid type; must be list or ndarray.")

                        shap_values_for_last_timestep = shap_values_for_last_timestep.flatten()

                        # ✅ Log
                        logger.info(f"Node {self.node_id}: SHAP values shape: {shap_values_for_last_timestep.shape}")
                        logger.info(f"Node {self.node_id}: SHAP sample: {shap_values_for_last_timestep[:5]}")

                        # ✅ Proceed to generate plots
                        data_for_explanation_original_scale = self.scaler.inverse_transform(actual_scaled_last_step.reshape(1, -1))[0].astype(float)
                        base_value_for_anomaly_impact = 0.0
                        plot_suffix = f"{int(time.time())}" 
                        loop = asyncio.get_event_loop()
                        loop.create_task(self.generate_shap_plots(
                            shap_values_for_last_timestep,
                            base_value_for_anomaly_impact,
                            data_for_explanation_original_scale,
                            self.feature_names,
                            plot_suffix
                        ))

                        sorted_features_by_impact = sorted(zip(self.feature_names, shap_values_for_last_timestep), key=lambda x: np.abs(x[1]), reverse=True)

                        top_n = 5
                        for feature, importance in sorted_features_by_impact[:top_n]:
                            logger.info(f"Node {self.node_id}: Starting root cause loop with SHAP values: {shap_values_for_last_timestep[:5]}")
                            if np.abs(importance) > 1e-6:
                                root_cause_indicators.append({"feature": feature, "importance": f"{importance:.4f}"})
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
                                logger.info(f"Node {self.node_id}: Root cause - {feature} (Impact: {importance:.4f})")    

                        if not root_cause_indicators and is_anomaly:
                            root_cause_indicators.append({"feature": "Unknown/General Anomaly", "importance": "N/A"})

                        if anomaly_score > 0.75 and ("Network" in affected_components or "Equipment" in affected_components or "Node_State" in affected_components):
                            severity_classification = "Critical"
                        elif anomaly_score > 0.5:
                            severity_classification = "High"
                        elif anomaly_score > 0.25:
                            severity_classification = "Medium"
                        else:
                            severity_classification = "Low"

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
                        }

                    except Exception as e:
                        logger.error(f"Node {self.node_id}: SHAP explanation failed: {e}", exc_info=True)
                        root_cause_indicators = [{"error": "SHAP explanation failed", "details": str(e)}]
                        affected_components = ["Unknown"]
                        severity_classification = "Low"
                        recommended_actions = ["Investigate manually."]
                        shap_values_output = None
            else: # If not an anomaly, log reconstruction error for monitoring
                logger.debug(f"Node {self.node_id}: Normal. Reconstruction Error: {reconstruction_error:.6f}, Threshold: {self.dynamic_anomaly_threshold:.6f}, Score: {anomaly_score:.4f}.")

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
# Add the DynamicConfidenceCalculator class from calculation_agent-7.py
class DynamicConfidenceCalculator:
    def __init__(self):
        self.performance_history = {}
        self.anomaly_score_history = {}
        self.model_performance_metrics = {}

    def calculate_dynamic_confidence(self, node_id, anomaly_result, detector):
        """Calculate confidence from actual model performance and data quality"""
        try:
            # Factor 1: Model validation performance
            model_confidence = self.get_model_validation_confidence(detector)
            
            # Factor 2: Prediction consistency
            consistency_confidence = self.get_prediction_consistency_confidence(node_id, anomaly_result)
            
            # Factor 3: Data quality assessment
            data_quality_confidence = self.assess_data_quality_confidence(anomaly_result)
            
            # Factor 4: Historical accuracy
            historical_confidence = self.get_historical_accuracy_confidence(node_id)
            
            # Calculate weighted average based on available data volume
            weights = self.calculate_dynamic_weights(node_id, detector)
            confidence_components = [
                model_confidence * weights['model'],
                consistency_confidence * weights['consistency'],
                data_quality_confidence * weights['data_quality'],
                historical_confidence * weights['historical']
            ]
            
            final_confidence = sum(confidence_components) / sum(weights.values())
            return max(0.0, min(1.0, final_confidence))
            
        except Exception as e:
            logger.error(f"Error calculating dynamic confidence: {e}")
            # Return confidence based on anomaly score only as fallback
            return min(1.0, anomaly_result.get('anomaly_score', 0.0))

    def get_model_validation_confidence(self, detector):
        """Get confidence from actual model training validation"""
        if not detector.is_trained:
            return 0.1
        
        try:
            # Use validation loss if available
            if hasattr(detector, 'model') and hasattr(detector.model, '_model'):
                if hasattr(detector.model._model, 'history'):
                    history = detector.model._model.history.history
                    val_loss = history.get('val_loss', [1.0])
                    if val_loss:
                        last_val_loss = val_loss[-1]
                        # Convert loss to confidence (lower loss = higher confidence)
                        confidence = 1.0 / (1.0 + last_val_loss)
                        return min(1.0, confidence)
            
            # Use threshold reliability as backup
            if detector.dynamic_anomaly_threshold > 0:
                return min(1.0, detector.dynamic_anomaly_threshold / 10.0)
            return 0.5
        except Exception:
            return 0.5

    def get_prediction_consistency_confidence(self, node_id, anomaly_result):
        """Calculate confidence based on prediction consistency"""
        if node_id not in self.anomaly_score_history:
            self.anomaly_score_history[node_id] = []
        
        current_score = anomaly_result.get('anomaly_score', 0.0)
        self.anomaly_score_history[node_id].append(current_score)
        
        # Keep only recent scores
        recent_scores = self.anomaly_score_history[node_id][-20:]
        if len(recent_scores) < 3:
            return 0.5
        
        # Calculate consistency (lower variance = higher confidence)
        variance = np.var(recent_scores)
        consistency = 1.0 / (1.0 + variance * 10)  # Scale variance
        return min(1.0, consistency)

    def assess_data_quality_confidence(self, anomaly_result):
        """Assess data quality from reconstruction error metrics"""
        reconstruction_error = anomaly_result.get('reconstruction_error', 0.0)
        threshold = anomaly_result.get('threshold', 1.0)
        
        if threshold == 0:
            return 0.1
        
        # Signal-to-noise ratio
        signal_ratio = abs(reconstruction_error) / threshold
        # Convert to confidence (clearer signal = higher confidence)
        quality_confidence = min(1.0, signal_ratio)
        return quality_confidence

    def get_historical_accuracy_confidence(self, node_id):
        """Get confidence from historical prediction accuracy"""
        if node_id not in self.performance_history:
            self.performance_history[node_id] = {'correct': 0, 'total': 0}
        
        history = self.performance_history[node_id]
        if history['total'] == 0:
            return 0.5
        
        accuracy = history['correct'] / history['total']
        return accuracy

    def calculate_dynamic_weights(self, node_id, detector):
        """Calculate weights based on available data and model maturity"""
        # More training data = higher weight on model performance
        model_weight = 0.4 if detector.is_trained else 0.1
        
        # More historical data = higher weight on historical accuracy
        historical_count = self.performance_history.get(node_id, {}).get('total', 0)
        historical_weight = min(0.3, historical_count / 100.0)
        
        # More prediction history = higher weight on consistency
        prediction_count = len(self.anomaly_score_history.get(node_id, []))
        consistency_weight = min(0.3, prediction_count / 20.0)
        
        # Remaining weight goes to data quality
        data_quality_weight = 1.0 - (model_weight + historical_weight + consistency_weight)
        
        return {
            'model': model_weight,
            'historical': historical_weight,
            'consistency': consistency_weight,
            'data_quality': max(0.1, data_quality_weight)
        }

    def determine_dynamic_severity(self, anomaly_score, node_id):
        """Determine severity based on actual anomaly score distribution"""
        if node_id not in self.anomaly_score_history:
            # No history - use adaptive thresholds
            if anomaly_score >= 0.8:
                return 'critical'
            elif anomaly_score >= 0.6:
                return 'high'
            elif anomaly_score >= 0.4:
                return 'medium'
            else:
                return 'low'
        
        recent_scores = self.anomaly_score_history[node_id][-100:]  # Last 100 scores
        if len(recent_scores) < 10:
            # Not enough history, use simple thresholds
            return self.determine_dynamic_severity(anomaly_score, 'default')
        
        # Calculate dynamic percentiles from actual data
        try:
            percentile_95 = np.percentile(recent_scores, 95)
            percentile_80 = np.percentile(recent_scores, 80)
            percentile_60 = np.percentile(recent_scores, 60)
            
            if anomaly_score >= percentile_95:
                return 'critical'
            elif anomaly_score >= percentile_80:
                return 'high'
            elif anomaly_score >= percentile_60:
                return 'medium'
            else:
                return 'low'
        except Exception:
            return 'medium'

    def update_performance_feedback(self, node_id, was_correct):
        """Update historical performance tracking"""
        if node_id not in self.performance_history:
            self.performance_history[node_id] = {'correct': 0, 'total': 0}
        self.performance_history[node_id]['total'] += 1
        if was_correct:
            self.performance_history[node_id]['correct'] += 1



# --- Calculation Agent (Main Class) ---
class CalculationAgent:
    """
    The main Calculation Agent responsible for managing anomaly detectors for multiple nodes,
    receiving data, triggering predictions, and communicating with other agents (Healing, MCP).
    """
    def __init__(self, node_ids: List[str], pub_socket_address_a2a: str, push_socket_address_mcp: str,context=None, sequence_length: int = 10):
        """
        Initializes the Calculation Agent.

        Args:
            node_ids (list): A list of unique identifiers for all network nodes to monitor.
            pub_socket_address_a2a (str): ZeroMQ address for publishing A2A anomaly alerts to the Healing Agent.
            push_socket_address_mcp (str): ZeroMQ address for pushing status updates to the MCP.
            sequence_length (int): The length of the time series sequence for LSTM.
        """
        logger.info(f"Calculation Agent: Initializing. Current working directory: {os.getcwd()}")

        self.config = self.load_config()
        self.node_ids = node_ids

        self.sequence_length = self.config.get('lstm_sequence_length', sequence_length)
        self.anomaly_threshold_percentile_config = self.config.get('anomaly_threshold_percentile', 99) # New config for percentile

        self.node_detectors = {}

        self.all_features = self.config.get('lstm_features', [])
        self.numerical_features_for_lstm = [] # Will be populated after loading training data
        self.input_features_count = 0

        # Initialize dynamic confidence calculator
        self.confidence_calculator = DynamicConfidenceCalculator()
        
        # Initialize communication exactly like calculation_agent-7.py
        self.context = context if context else zmq.asyncio.Context()
        self.a2a_publisher = self.context.socket(zmq.PUB)
        self.a2a_publisher.bind(pub_socket_address_a2a)
        
        self._mcp_push_socket = self.context.socket(zmq.PUSH)
        self._mcp_push_socket.connect(push_socket_address_mcp)
        
        logger.info(f"Calculation Agent: A2A Publisher bound to {pub_socket_address_a2a}")
        logger.info(f"Calculation Agent: MCP PUSH socket connected to {push_socket_address_mcp}")

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
            "lstm_sequence_length": 1,
            "lstm_epochs": 1,
            "anomaly_threshold_percentile": 99, # Changed to percentile
            "alert_debounce_interval": 10,
            "model_training_batch_size": 32,
            "train_on_startup": False,
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
                anomaly_threshold_percentile=self.anomaly_threshold_percentile_config # Pass percentile
            )
            logger.info(f"Detector initialized for node: {node_id} with sequence length {self.sequence_length}")

    async def _objective_function(self, params, node_id, X_train, y_train):
        """
        Objective function for SSA to optimize LSTM hyperparameters.
        """
        # CRITICAL FIX: Clear Keras session before each trial in objective function.
        # This helps in multiprocessing environments where Keras/TensorFlow might
        # retain graph states from previous trials, leading to unexpected errors
        # when models or optimizers are re-created.
        tf.keras.backend.clear_session()

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
            save_shap_plots=True,
            anomaly_threshold_percentile=self.anomaly_threshold_percentile_config # Pass percentile
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

            # Note: For hyperparameter optimization, we usually don't need to calculate the
            # dynamic threshold here, just the model's loss.
            temp_detector.train_model(X_train_scaled, y_train_scaled, epochs=1, verbose=0)

            if not temp_detector.is_trained:
                logger.warning(f"Node {node_id} (SSA temp): Training failed, temp_detector.is_trained is False.")
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
        # Consider increasing n_salps and n_iterations for more thorough optimization
        # Current values are very low for effective optimization.
        # e.g., n_salps=30, n_iterations=100 for a more robust search.
        lower_bounds = [32, 0.0001, 2, 0.0]
        upper_bounds = [128, 0.005, 3, 0.3]

        obj_func_with_data = partial(self._objective_function, node_id=node_id, X_train=X_train_data, y_train=y_train_data)

        ssa = SalpSwarmOptimizer(
            obj_func=obj_func_with_data,
            n_salps=1, # Recommend increasing, e.g., to 30
            n_iterations=1, # Recommend increasing, e.g., to 100
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
        # Train the model with the optimized hyperparameters and calculate the dynamic threshold
        detector.train_model(X_train_data, y_train_data, epochs=self.config['lstm_epochs'], batch_size=self.config['model_training_batch_size'])
        logger.info(f"Node {node_id}: LSTM model updated with optimized parameters and fully retrained.")


    async def load_and_prepare_initial_training_data(self, file_path):
        """
        Loads initial training data for all nodes from the specified CSV.
        This data is used to train each node's detector once at startup.
        """
        absolute_file_path = os.path.abspath(file_path)
        logger.info(f"Calculation Agent: Attempting to load initial training data from {absolute_file_path}...")
        try:
            df = pd.read_csv(absolute_file_path)
            logger.info(f"Successfully loaded CSV from {absolute_file_path}. Total rows: {len(df)}, columns: {len(df.columns)}")

            df['NodeId'] = df['NodeId'].apply(lambda x: f"node_{int(x):02d}")
            unique_nodes_in_csv = df['NodeId'].unique().tolist()
            logger.info(f"Found {len(unique_nodes_in_csv)} unique nodes in training data: {unique_nodes_in_csv}")


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

            # Iterate through all nodes the agent is configured to monitor (self.node_ids)
            for node_id_formatted in self.node_ids: 
                node_df = df_renamed[df_renamed['NodeId'] == node_id_formatted].sort_values(by='current_time')
                
                # Check if the node even exists in the loaded CSV data
                if node_df.empty:
                    logger.warning(f"Node {node_id_formatted}: No data found in the training CSV file. Skipping training for this node.")
                    node_training_data[node_id_formatted] = (np.array([]), np.array([]))
                    continue

                logger.info(f"Node {node_id_formatted}: Found {len(node_df)} raw data points in training file for this specific node.")


                node_features_df = node_df[self.numerical_features_for_lstm].astype(float)

                if len(node_features_df) < self.sequence_length + 1:
                    logger.warning(f"Node {node_id_formatted}: Not enough data points ({len(node_features_df)}) "
                                   f"for initial training with sequence length {self.sequence_length} (needs at least {self.sequence_length + 1}). "
                                   f"Skipping training for this node.")
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
                logger.info(f"Node {node_id_formatted}: Prepared {num_sequences} training sequences. "
                            f"X_train shape: {node_training_data[node_id_formatted][0].shape}, "
                            f"y_train shape: {node_training_data[node_id_formatted][1].shape}")

            return node_training_data

        except FileNotFoundError:
            logger.error(f"Error: Initial training data file not found at {absolute_file_path}. Please ensure the file exists and the path is correct.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error loading and preparing initial training data from {absolute_file_path}: {e}", exc_info=True)
            sys.exit(1)

    async def perform_pre_live_testing(self):
        """
        Performs a pre-live testing phase using a separate CSV file
        to evaluate SHAP and anomaly detection.
        """
        testing_file = self.config['testing_data_file']
        absolute_testing_file_path = os.path.abspath(testing_file)
        logger.info("=" * 80)
        logger.info(f"STARTING PRE-LIVE TESTING PHASE (SHAP & ANOMALY DETECTION) from {absolute_testing_file_path}")
        logger.info("=" * 80)

        try:
            df = pd.read_csv(absolute_testing_file_path)
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

            if not self.numerical_features_for_lstm:
                logger.error("Features not initialized. Cannot perform pre-live testing. Exiting.")
                return

            for index, row in df_renamed.iterrows():
                total_test_samples += 1
                node_id = row['NodeId']

                detector = self.node_detectors.get(node_id)
                if not detector or not detector.is_trained:
                    # Log more explicitly if skipping due to untrained detector
                    if detector and not detector.is_trained:
                        logger.debug(f"Pre-live test: Skipping data for node {node_id} as its detector is not trained.")
                    else:
                        logger.debug(f"Pre-live test: No detector found for node {node_id}. Skipping data point.")
                    continue

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
                    logger.debug(f"PRE-LIVE TEST: No anomaly for {node_id} at sim_time {row.get('current_time', 'N/A')}. "
                                 f"Recon Error: {anomaly_results.get('reconstruction_error', 'N/A')},"
                                 f"Threshold: {detector.dynamic_anomaly_threshold:.6f}")

                # Simulate processing time for realism
                await asyncio.sleep(0.001)

            logger.info("=" * 80)
            logger.info(f"PRE-LIVE TESTING COMPLETE. Total Samples Processed: {total_test_samples}, Anomalies Detected: {test_anomalies_detected}")
            logger.info("=" * 80)

        except FileNotFoundError:
            logger.error(f"Pre-live testing data file not found: {absolute_testing_file_path}. Skipping pre-live testing.")
        except Exception as e:
            logger.error(f"Error during pre-live testing phase from {absolute_testing_file_path}: {e}", exc_info=True)


    # New method to handle pushing status to MCP
    async def mcp_push_status_update(self, status_data: dict):
        """
        Sends status updates to the MCP Agent via the PUSH socket.
        """
        try:
            # Ensure the data is JSON-serializable if using send_json
            await self._mcp_push_socket.send_json(status_data)
            logging.debug(f"Calculation Agent: Sent status to MCP: {status_data}")
        except Exception as e:
            logging.error(f"Calculation Agent: Error sending status to MCP: {e}")
  
    async def process_data_point(self, node_id: str, raw_data_point_dict: Dict[str, Any]):
        """
        Processes a single data point exactly like calculation_agent-7.py
        """
        detector = self.node_detectors.get(node_id)
        if not detector:
            logger.warning(f"No detector found for node {node_id}")
            return

        if not detector.is_trained:
            return

        anomaly_result = await detector.predict_anomaly(raw_data_point_dict, self.numerical_features_for_lstm)

        # Update Prometheus metrics (if available)
        if hasattr(self, 'anomaly_score_gauge'):
            self.anomaly_score_gauge.labels(
                node_id=node_id,
                severity=anomaly_result.get("status", "normal")
            ).set(anomaly_result['anomaly_score'])

        if anomaly_result['anomaly_score'] > 0.5:
            if hasattr(self, 'anomaly_detection_counter'):
                self.anomaly_detection_counter.labels(
                    node_id=node_id,
                    severity="high" if anomaly_result['anomaly_score'] > 0.7 else "medium",
                    anomaly_type="lstm_prediction"
                ).inc()

            #await self.send_anomaly_alert_to_healing_agent(node_id, anomaly_result)
            await self.process_anomaly_detection_and_alerting(node_id, anomaly_result, raw_data_point_dict)
        else:
        # For normal operation, still call the method but it will just log
            await self.process_anomaly_detection_and_alerting(node_id, anomaly_result, raw_data_point_dict)
    
    async def send_anomaly_alert_to_healing_agent(self, node_id, anomaly_result):
        try:
            if self.a2a_publisher is None:
                return

            detector = self.node_detectors.get(node_id)
            
            # DYNAMIC confidence calculation
            dynamic_confidence = self.confidence_calculator.calculate_dynamic_confidence(
                node_id, anomaly_result, detector
            )
            
            # DYNAMIC severity determination
            dynamic_severity = self.confidence_calculator.determine_dynamic_severity(
                anomaly_result['anomaly_score'], node_id
            )
            
            # CORRECTED message structure to match healing agent expectations
            anomaly_alert = {
                'type': 'anomaly_alert',  # 
                'anomaly_id': f"ANOM_{node_id}_{int(time.time())}",  
                'node_id': node_id,  
                'timestamp': datetime.now().isoformat(),
                'source_agent': 'calculation_agent',
                'target_agent': 'healing_agent',
                'message_id': f"CALC_ANOM_{int(time.time())}_{node_id}",
                'anomaly_score': anomaly_result['anomaly_score'],  #
                'severity': dynamic_severity,  
                'detection_timestamp': datetime.now().isoformat(),
                'confidence': dynamic_confidence,  
                'network_context': {
                    'node_type': self.get_node_type(node_id),
                    'fault_pattern': 'dynamic_detection'
                }
            }

            await self.a2a_publisher.send_json(anomaly_alert)
            if hasattr(self, 'comm_metrics'):
                self.comm_metrics['anomalies_sent'] += 1
            logger.info(f"Anomaly alert sent for {node_id}: {anomaly_alert['message_id']}")

        except Exception as e:
            logger.error(f"Failed to send anomaly alert for {node_id}: {e}")
            if hasattr(self, 'comm_metrics'):
                self.comm_metrics['failed_communications'] += 1

    def get_node_type(self, node_id):
        """Node type classification from calculation_agent-7.py"""
        node_num = int(node_id.split('_')[1])
        if node_num in range(0, 10):
            return "CORE"
        elif node_num in range(10, 30):
            return "DIST"
        elif node_num in range(30, 50):
            return "ACC"
        else:
            return "GENERIC"

    async def data_processing_loop(self):
        """
        Continuously looks for new JSON files every 10 seconds and processes them.
        """
        logger.info("Starting JSON file monitoring loop...")
        processed_files = set()  # Track processed files

        while True:
            try:
            # ✅ Look for JSON files in both directories
                static_files = glob.glob("calculation_agent_input/calculation_input_*.json")
                fault_files = glob.glob("calculation_agent_input/realtime_fault_*.json") 
                notification_files = glob.glob("calculation_agent_input/fault_notification_*.json")
    
                all_files = static_files + fault_files + notification_files
    
            # ✅ Debug logging only when files are found
                if all_files:
                    logger.debug(f"🔍 Found {len(all_files)} files: static={len(static_files)}, fault={len(fault_files)}, notification={len(notification_files)}")
    
            # ✅ SINGLE processing loop (removed duplicate)
                for json_file in all_files:
                    if json_file not in processed_files:
                        logger.info(f"📄 Processing new file: {json_file}")
            
                        try:
                            with open(json_file, 'r') as f:
                                file_content = f.read().strip()
                
                        # ✅ Handle malformed JSON structure
                            if file_content.startswith('"monitor_metadata"'):
                                file_content = '{' + file_content + '}'
                
                            data = json.loads(file_content)
                        
                        # ✅ DEBUG: Log all keys in file
                            logger.info(f"🔍 DEBUG {json_file}: Keys found: {list(data.keys())}")
                        
                        # ✅ DEBUG: Check for fault indicators
                            has_fault_events = 'fault_events' in data
                            has_fault_type = 'fault_type' in data
                            has_affected_nodes = 'affected_nodes' in data
                            has_lstm_training = 'lstm_training_data' in data and 'network_metrics' in data['lstm_training_data']
                            has_notification = 'notification_type' in data
                       
                            logger.info(f"🔍 DEBUG {json_file}: lstm_training={has_lstm_training}, fault_events={has_fault_events}, fault_type={has_fault_type}, affected_nodes={has_affected_nodes}, notification={has_notification}")
                
                        # ✅ STATIC DATA PROCESSING
                            if 'lstm_training_data' in data and 'network_metrics' in data['lstm_training_data']:
                                logger.info(f"📊 Processing static data from {json_file}")
                                network_metrics = data['lstm_training_data']['network_metrics']
                    
                                for node_key, node_data in network_metrics.items():
                                    if node_key.startswith('node_'):
                                        node_number = node_key.split('_')[1]
                                        formatted_node_id = f"node_{int(node_number):02d}"
                            
                                        raw_data_point = {
                                        'current_time': node_data.get('timestamp', 0.0),
                                        'throughput': node_data.get('throughput', 0.0),
                                        'latency': node_data.get('latency', 0.0),
                                        'packet_loss': node_data.get('packet_loss', 0.0),
                                        'cpu_usage': node_data.get('cpu_usage', 0.0),
                                        'memory_usage': node_data.get('memory_usage', 0.0),
                                        'jitter': node_data.get('jitter', 0.0),
                                        'signal_strength': node_data.get('signal_strength', 0.0),
                                        'buffer_occupancy': node_data.get('buffer_occupancy', 0.0),
                                        'active_links': node_data.get('active_links', 0),
                                        'neighbor_count': node_data.get('neighbor_count', 0),
                                        'link_utilization': node_data.get('link_utilization', 0.0),
                                        'critical_load': node_data.get('critical_load', 0.0),
                                        'normal_load': node_data.get('normal_load', 0.0),
                                        'energy_level': node_data.get('energy_level', 0.0),
                                        'x_position': node_data.get('x_position', 0.0),
                                        'y_position': node_data.get('y_position', 0.0),
                                        'z_position': node_data.get('z_position', 0.0),
                                        'degradation_level': node_data.get('degradation_level', 0.0),
                                        'fault_severity': node_data.get('fault_severity', 0.0),
                                        'power_stability': node_data.get('power_stability', 0.0),
                                        'voltage_level': node_data.get('voltage_level', 0.0)
                                        }
                            
                                        await self.process_data_point(formatted_node_id, raw_data_point)
                
                        # ✅ FAULT DATA PROCESSING - WRAPPED FORMAT
                            elif 'fault_events' in data:
                                logger.info(f"🚨 FAULT DATA DETECTED (wrapped) in {json_file}")
                                fault_events = data['fault_events']
                            
                                for fault_event in fault_events:
                                    fault_type = fault_event.get('fault_type', 'unknown')
                                    affected_nodes = fault_event.get('affected_nodes', [])
                                    severity = fault_event.get('severity', 0.0)
                                    timestamp = fault_event.get('timestamp', 0.0)
                                    event_id = fault_event.get('event_id', 'unknown')
                        
                                    logger.info(f"⚠️ Processing wrapped fault: {fault_type} affecting nodes {affected_nodes} with severity {severity}")
                        
                                    for node_id in affected_nodes:
                                        if isinstance(node_id, int):
                                            formatted_node_id = f"node_{node_id:02d}"
                                        else:
                                            formatted_node_id = str(node_id)
                            
                                    # Create comprehensive fault data point
                                        fault_data_point = {
                                        'current_time': timestamp,
                                        'fault_type': fault_type,
                                        'fault_severity': severity,
                                        'is_fault_event': True,
                                        'event_id': event_id,
                                        'throughput': 0.0,
                                        'latency': 0.0,
                                        'packet_loss': 0.0,
                                        'cpu_usage': 0.0,
                                        'memory_usage': 0.0,
                                        'jitter': 0.0,
                                        'signal_strength': 0.0,
                                        'buffer_occupancy': 0.0,
                                        'active_links': 0,
                                        'neighbor_count': 0,
                                        'link_utilization': 0.0,
                                        'critical_load': 0.0,
                                        'normal_load': 0.0,
                                        'energy_level': 0.0,
                                        'x_position': 0.0,
                                        'y_position': 0.0,
                                        'z_position': 0.0,
                                        'degradation_level': severity,
                                        'power_stability': 0.0,
                                        'voltage_level': 0.0
                                        }
                            
                                        await self.process_fault_event(formatted_node_id, fault_data_point)
                
                        # ✅ NEW: DIRECT FAULT EVENT DETECTION (for individual fault files like fault_20.json)
                            elif 'fault_type' in data and 'affected_nodes' in data:
                                logger.info(f"🚨 DIRECT FAULT EVENT DETECTED in {json_file}")
                            
                                fault_type = data.get('fault_type', 'unknown')
                                affected_nodes = data.get('affected_nodes', [])
                                severity = data.get('severity', 0.0)
                                timestamp = data.get('timestamp', 0.0)
                                event_id = data.get('event_id', 'unknown')
                            
                                logger.info(f"⚠️ Processing direct fault: {fault_type} affecting nodes {affected_nodes} with severity {severity}")
                            
                                for node_id in affected_nodes:
                                    if isinstance(node_id, int):
                                        formatted_node_id = f"node_{node_id:02d}"
                                    else:
                                        formatted_node_id = str(node_id)
                        
                                    fault_data_point = {
                                    'current_time': timestamp,
                                    'fault_type': fault_type,
                                    'fault_severity': severity,
                                    'is_fault_event': True,
                                    'event_id': event_id,
                                    'throughput': 0.0,
                                    'latency': 0.0,
                                    'packet_loss': 0.0,
                                    'cpu_usage': 0.0,
                                    'memory_usage': 0.0,
                                    'jitter': 0.0,
                                    'signal_strength': 0.0,
                                    'buffer_occupancy': 0.0,
                                    'active_links': 0,
                                    'neighbor_count': 0,
                                    'link_utilization': 0.0,
                                    'critical_load': 0.0,
                                    'normal_load': 0.0,
                                    'energy_level': 0.0,
                                    'x_position': 0.0,
                                    'y_position': 0.0,
                                    'z_position': 0.0,
                                    'degradation_level': severity,
                                    'power_stability': 0.0,
                                    'voltage_level': 0.0
                                    }
                        
                                    await self.process_fault_event(formatted_node_id, fault_data_point)
                
                        # ✅ NOTIFICATION FILE PROCESSING - ENHANCED
                            elif 'notification_type' in data:
                                logger.info(f"📨 FAULT NOTIFICATION DETECTED in {json_file}")
                        
                            # ✅ NEW: Handle fault notifications with affected nodes info
                                if data.get('notification_type') == 'realtime_fault_detected':
                                    fault_summary = data.get('fault_summary', {})
                                    affected_nodes = fault_summary.get('affected_nodes', [])
                                    fault_types = fault_summary.get('fault_types', [])
                                    max_severity = fault_summary.get('max_severity', 0.0)
                                    requires_action = fault_summary.get('requires_immediate_action', False)

                                # ✅ FIXED: Handle both list and integer for affected_nodes
                                    if isinstance(affected_nodes, list):
                                        node_count = len(affected_nodes)
                                        node_list = affected_nodes
                                    else:
                                    # affected_nodes is actually a count
                                        node_count = affected_nodes
                                        node_list = []

                                    logger.info(f"📋 Notification summary: {node_count} nodes affected, "
                                                f"fault types: {fault_types}, max severity: {max_severity}, "
                                                f"requires action: {requires_action}")
                            
                                # ✅ NEW: Check if we need to read the referenced fault file
                                    data_file = data.get('data_file', '')
                                    if data_file:
                                    # Construct full path
                                        if not data_file.startswith('calculation_agent_input/'):
                                            fault_file_path = f"calculation_agent_input/{data_file.split('/')[-1]}"
                                        else:
                                            fault_file_path = data_file

                                    # ✅ NEW: Read and process the referenced fault file if it exists
                                        if os.path.exists(fault_file_path) and fault_file_path not in processed_files:
                                            logger.info(f"📂 Reading referenced fault file: {fault_file_path}")
                                            try:
                                                with open(fault_file_path, 'r') as f:
                                                    fault_data = json.load(f)
                                            
                                            # ✅ NEW: Handle both wrapped and direct fault formats in referenced files
                                                if 'fault_events' in fault_data:
                                                    logger.info(f"🔄 Processing fault events from referenced file: {fault_file_path}")
                                                # Process wrapped fault events
                                                    for fault_event in fault_data['fault_events']:
                                                        fault_type = fault_event.get('fault_type', 'unknown')
                                                        affected_nodes = fault_event.get('affected_nodes', [])
                                                        severity = fault_event.get('severity', 0.0)
                                                        timestamp = fault_event.get('timestamp', 0.0)
                                                
                                                        for node_id in affected_nodes:
                                                            if isinstance(node_id, int):
                                                                formatted_node_id = f"node_{node_id:02d}"
                                                            else:
                                                                formatted_node_id = str(node_id)
                                                
                                                            fault_data_point = {
                                                            'current_time': timestamp,
                                                            'fault_type': fault_type,
                                                            'fault_severity': severity,
                                                            'is_fault_event': True,
                                                            'throughput': 0.0,
                                                            'latency': 0.0,
                                                            'packet_loss': 0.0,
                                                            'cpu_usage': 0.0,
                                                            'memory_usage': 0.0,
                                                            'jitter': 0.0,
                                                            'signal_strength': 0.0,
                                                            'buffer_occupancy': 0.0,
                                                            'active_links': 0,
                                                            'neighbor_count': 0,
                                                            'link_utilization': 0.0,
                                                            'critical_load': 0.0,
                                                            'normal_load': 0.0,
                                                            'energy_level': 0.0,
                                                            'x_position': 0.0,
                                                            'y_position': 0.0,
                                                            'z_position': 0.0,
                                                            'degradation_level': severity,
                                                            'power_stability': 0.0,
                                                            'voltage_level': 0.0
                                                            }
                                                
                                                            await self.process_fault_event(formatted_node_id, fault_data_point)
                                            
                                            # ✅ NEW: Handle direct fault format in referenced files
                                                elif 'fault_type' in fault_data and 'affected_nodes' in fault_data:
                                                    logger.info(f"🔄 Processing direct fault from referenced file: {fault_file_path}")
                                                    fault_type = fault_data.get('fault_type', 'unknown')
                                                    affected_nodes = fault_data.get('affected_nodes', [])
                                                    severity = fault_data.get('severity', 0.0)
                                                    timestamp = fault_data.get('timestamp', 0.0)
                                                    event_id = fault_data.get('event_id', 'unknown')
                                                
                                                    logger.info(f"⚠️ Processing referenced direct fault: {fault_type} affecting nodes {affected_nodes} with severity {severity}")
                                                
                                                    for node_id in affected_nodes:
                                                        if isinstance(node_id, int):
                                                            formatted_node_id = f"node_{node_id:02d}"
                                                        else:
                                                            formatted_node_id = str(node_id)
                                            
                                                        fault_data_point = {
                                                        'current_time': timestamp,
                                                        'fault_type': fault_type,
                                                        'fault_severity': severity,
                                                        'is_fault_event': True,
                                                        'event_id': event_id,
                                                        'throughput': 0.0,
                                                        'latency': 0.0,
                                                        'packet_loss': 0.0,
                                                        'cpu_usage': 0.0,
                                                        'memory_usage': 0.0,
                                                        'jitter': 0.0,
                                                        'signal_strength': 0.0,
                                                        'buffer_occupancy': 0.0,
                                                        'active_links': 0,
                                                        'neighbor_count': 0,
                                                        'link_utilization': 0.0,
                                                        'critical_load': 0.0,
                                                        'normal_load': 0.0,
                                                        'energy_level': 0.0,
                                                        'x_position': 0.0,
                                                        'y_position': 0.0,
                                                        'z_position': 0.0,
                                                        'degradation_level': severity,
                                                        'power_stability': 0.0,
                                                        'voltage_level': 0.0
                                                        }
                                            
                                                        await self.process_fault_event(formatted_node_id, fault_data_point)
                                            
                                            # Mark the referenced file as processed
                                                processed_files.add(fault_file_path)
                                            except Exception as e:
                                                logger.error(f"Error reading referenced fault file {fault_file_path}: {e}")
                                else:
                                    logger.info(f"📨 Processing other notification type: {data.get('notification_type')}")
                
                        # ✅ UNKNOWN FILE FORMAT
                            else:
                                logger.warning(f"❓ Unknown file format in {json_file}")
                                logger.warning(f"❓ File keys: {list(data.keys())}")
                                logger.warning(f"❓ Sample content: {str(data)[:200]}...")
                
                        # ✅ Mark file as processed
                            processed_files.add(json_file)
                            logger.info(f"✅ Successfully processed file: {json_file}")
                
                        except json.JSONDecodeError as e:
                            logger.error(f"❌ JSON decode error in {json_file}: {e}")
                            processed_files.add(json_file)  # Skip malformed files
                        except Exception as e:
                            logger.error(f"❌ Error processing file {json_file}: {e}", exc_info=True)
                            processed_files.add(json_file)  # Skip problematic files
    
            except Exception as e:
                logger.error(f"❌ Error in data processing loop: {e}", exc_info=True)

        # ✅ ALWAYS wait 10 seconds before next iteration
            await asyncio.sleep(10)

    async def process_fault_event(self, node_id: str, fault_data: Dict[str, Any]):
        """
        Process fault event for a specific node - FOCUSED ON DETECTION AND ALERTING ONLY
        """
        try:
            fault_type = fault_data.get('fault_type', 'unknown')
            fault_severity = fault_data.get('fault_severity', 0.0)
            timestamp = fault_data.get('current_time', 0.0)
            event_id = fault_data.get('event_id', 'unknown')
        
            logger.info(f"🚨 Node {node_id}: Processing fault event - {fault_type} (severity: {fault_severity}) at time {timestamp}, event_id: {event_id}")
        
        # ✅ Generate synthetic metrics based on fault type
            synthetic_metrics = self.generate_fault_metrics(node_id, fault_type, fault_severity)
        
        # ✅ Process through LSTM detector if available
            detector = self.node_detectors.get(node_id)
            if detector and detector.is_trained:
                logger.info(f"🔍 Node {node_id}: Processing fault through trained LSTM detector")
            
            # Run anomaly prediction on synthetic fault metrics
                anomaly_result = await detector.predict_anomaly(synthetic_metrics, self.numerical_features_for_lstm)
            
            # ✅ Force anomaly detection for fault events
                original_score = anomaly_result['anomaly_score']
                enhanced_score = max(original_score, min(1.0, fault_severity + 0.3))
            
            # Update anomaly result with fault-enhanced score
                anomaly_result['anomaly_score'] = enhanced_score
                anomaly_result['status'] = "Fault-induced Anomaly"
            
            # Add fault-specific context
                anomaly_result['fault_context'] = {
                'fault_type': fault_type,
                'fault_severity': fault_severity,
                'fault_timestamp': timestamp,
                'event_id': event_id,
                'detection_method': 'fault_event_processing'
                }
            
                logger.warning(f"🔥 Node {node_id}: Fault-based anomaly detected! "
                          f"Score: {enhanced_score:.4f} (Original: {original_score:.4f}, "
                          f"Fault Severity: {fault_severity:.4f})")
            
            # ✅ Send alert to healing agent
                await self.send_fault_alert_to_healing_agent(node_id, anomaly_result, fault_data)
            
            # ✅ Use existing pipeline for database integration
                await self.process_anomaly_detection_and_alerting(node_id, anomaly_result, synthetic_metrics)
        
            else:
            # ✅ Handle case when no trained detector is available
                logger.warning(f"⚠️ Node {node_id}: No trained detector available, sending direct fault alert")
            
            # Create basic anomaly result for non-trained nodes
                direct_anomaly_result = {
                'anomaly_score': min(1.0, fault_severity + 0.2),
                'status': 'Fault Detected (Direct)',
                'fault_context': {
                    'fault_type': fault_type,
                    'fault_severity': fault_severity,
                    'fault_timestamp': timestamp,
                    'event_id': event_id,
                    'detection_method': 'direct_fault_processing'
                }
                }
            
            # Send alert even without LSTM detector
                await self.send_fault_alert_to_healing_agent(node_id, direct_anomaly_result, fault_data)
                await self.process_anomaly_detection_and_alerting(node_id, direct_anomaly_result, synthetic_metrics)
        
            logger.info(f"✅ Node {node_id}: Fault event processing completed for {fault_type}")
        
        except Exception as e:
            logger.error(f"❌ Error processing fault event for {node_id}: {e}", exc_info=True)

    async def process_anomaly_detection_and_alerting(self, node_id, anomaly_results, raw_data_point_dict):
        """
        Process anomaly detection results and send alerts if needed.
        This handles the database integration and messaging to healing agent.
        """
    # Send alert to Healing Agent (via PUB/SUB) - ONLY for anomalies
        if anomaly_results["status"] == "Anomaly detected":
            simulation_time_for_alert = raw_data_point_dict.get('current_time', 0.0)
            detection_timestamp = int(time.time())
        
        # Step 1: Try to find existing anomaly in database
            existing_anomaly_id = find_existing_anomaly_id(node_id, detection_timestamp)
        
            if existing_anomaly_id:
            # Use existing anomaly_id from database
                anomaly_id = existing_anomaly_id
                logger.info(f"Node {node_id}: Using existing anomaly_id from database: {anomaly_id}")
            else:
            # Generate new database-compatible anomaly_id
                anomaly_id = generate_database_compatible_anomaly_id(node_id, detection_timestamp)
            
            # Insert the new anomaly into database
                insert_success = insert_new_anomaly_to_database(
                anomaly_id, 
                node_id, 
                detection_timestamp, 
                anomaly_results
                )
            
                if insert_success:
                    logger.info(f"Node {node_id}: Generated and inserted new anomaly_id: {anomaly_id}")
                else:
                    logger.warning(f"Node {node_id}: Failed to insert anomaly into database, but proceeding with ID: {anomaly_id}")

        # Create message compatible with Healing Agent expectations
            message_to_healing = {
            "type": "anomaly_alert",
            "anomaly_id": anomaly_id,  # Now uses database-consistent ID
            "node_id": node_id,
            "timestamp": datetime.now().isoformat(),
            "simulation_time": simulation_time_for_alert,
            "anomaly_score": anomaly_results['anomaly_score'],
            "severity": anomaly_results.get("severity_classification", "N/A"),
            "description": f"Anomaly detected for node {node_id}",
            "actual_metrics": anomaly_results.get('actual_metrics', {}),
            "predicted_metrics": anomaly_results.get('predicted_metrics', {}),
            "source_agent": "calculation_agent",
            "root_cause_indicators": anomaly_results.get("root_cause_indicators", []),
            "recommended_actions": anomaly_results.get("recommended_actions", [])
            }

            try:
            # ✅ FIXED: Use correct socket reference
                await self.a2a_publisher.send_json(message_to_healing)
                logger.info(f"Node {node_id}: A2A: Published anomaly alert with ID {anomaly_id} (Score: {anomaly_results['anomaly_score']:.4f})")
            except Exception as e:
                logger.error(f"Node {node_id}: Failed to send alert to Healing Agent: {e}", exc_info=True)

        # Send status update to MCP Agent - ONLY for anomalies
            mcp_message = {
            "source": "CalculationAgent",
            "type": "anomaly_status",
            "node_id": node_id,
            "timestamp": datetime.now().isoformat(),
            "simulation_time": raw_data_point_dict.get('current_time', 0.0),
            "status": anomaly_results["status"],
            "details": anomaly_results
            }

            try:
                await self.mcp_push_status_update(mcp_message)
                logger.info(f"Node {node_id}: MCP: Pushed anomaly status with ID {anomaly_id} (Score: {anomaly_results['anomaly_score']:.4f}).")
            except Exception as e:
                logger.error(f"Node {node_id}: Failed to push status to MCP: {e}", exc_info=True)
        else:
        # For non-anomalies, just log but don't send messages
            logger.debug(f"Node {node_id}: Normal operation (Score: {anomaly_results['anomaly_score']:.4f})")

    def generate_fault_metrics(self, node_id: str, fault_type: str, fault_severity: float) -> Dict[str, float]:
        """
        Generate synthetic metrics based on fault type and severity
        """
    # Base metrics (normal operation)
        base_metrics = {
        'throughput': 100.0,
        'latency': 10.0,
        'packet_loss': 0.01,
        'cpu_usage': 0.3,
        'memory_usage': 0.4,
        'jitter': 2.0,
        'signal_strength': -70.0,
        'buffer_occupancy': 0.2,
        'active_links': 4,
        'neighbor_count': 6,
        'link_utilization': 0.5,
        'critical_load': 0.1,
        'normal_load': 0.8,
        'energy_level': 0.9,
        'x_position': 0.0,
        'y_position': 0.0,
        'z_position': 0.0,
        'degradation_level': 0.1,
        'fault_severity': fault_severity,
        'power_stability': 0.95,
        'voltage_level': 12.0,
        'current_time': time.time()
        }
    
    # ✅ Modify metrics based on fault type
        if fault_type == 'power_fluctuation':
            base_metrics['power_stability'] = max(0.0, 0.95 - fault_severity)
            base_metrics['voltage_level'] = max(8.0, 12.0 - (fault_severity * 3))
            base_metrics['cpu_usage'] = min(1.0, 0.3 + fault_severity * 0.4)
            base_metrics['degradation_level'] = min(1.0, 0.1 + fault_severity * 0.6)
        
        elif fault_type == 'network_congestion':
            base_metrics['throughput'] = max(10.0, 100.0 - (fault_severity * 60))
            base_metrics['latency'] = min(100.0, 10.0 + (fault_severity * 40))
            base_metrics['packet_loss'] = min(0.5, 0.01 + fault_severity * 0.2)
            base_metrics['link_utilization'] = min(1.0, 0.5 + fault_severity * 0.4)
        
        elif fault_type == 'hardware_fault':
            base_metrics['cpu_usage'] = min(1.0, 0.3 + fault_severity * 0.5)
            base_metrics['memory_usage'] = min(1.0, 0.4 + fault_severity * 0.4)
            base_metrics['degradation_level'] = min(1.0, 0.1 + fault_severity * 0.8)
            base_metrics['signal_strength'] = max(-120.0, -70.0 - (fault_severity * 30))
        
        else:  # Generic fault
            base_metrics['degradation_level'] = min(1.0, 0.1 + fault_severity * 0.5)
            base_metrics['fault_severity'] = fault_severity
    
        logger.info(f"🔧 Node {node_id}: Generated fault metrics for {fault_type} - "
                f"power_stability: {base_metrics['power_stability']:.3f}, "
                f"degradation: {base_metrics['degradation_level']:.3f}")
    
        return base_metrics

    async def send_fault_alert_to_healing_agent(self, node_id: str, anomaly_result: Dict, fault_data: Dict):
        """
        Send fault-specific alert to healing agent
        """
        try:
        # ✅ ENHANCED: Calculate dynamic confidence for better healing decisions
            detector = self.node_detectors.get(node_id)
            dynamic_confidence = self.confidence_calculator.calculate_dynamic_confidence(
                node_id, anomaly_result, detector
            ) if hasattr(self, 'confidence_calculator') else 0.8
        
            fault_alert = {
                'message_type': 'anomaly_alert',  # Different from anomaly_alert
                'fault_id': f"FAULT_{node_id}_{int(time.time())}",
                'anomaly_id': f"ANOM_{node_id}_{int(time.time())}",  # Also include anomaly ID
                'node_id': node_id,
                'timestamp': datetime.now().isoformat(),
                'source_agent': 'calculation_agent',
                'target_agent': 'healing_agent',
                'fault_type': fault_data.get('fault_type'),
                'fault_severity': fault_data.get('fault_severity'),
                'anomaly_score': anomaly_result['anomaly_score'],
                'severity': anomaly_result.get('severity_classification', 'High'),
                'detection_method': 'fault_event_processing',
                'fault_context': anomaly_result.get('fault_context', {}),
                'network_context': {
                    'node_type': self.get_node_type(node_id),
                '   fault_pattern': 'real_time_fault'
                },
            
            # ✅ NEW: Essential fields for healing agent decision making
                'confidence': dynamic_confidence,
                'description': f"Fault detected: {fault_data.get('fault_type', 'unknown')} on {node_id} with severity {fault_data.get('fault_severity', 0.0):.3f}",
                'event_id': fault_data.get('event_id', f"evt_{node_id}_{int(time.time())}"),
                'simulation_time': fault_data.get('current_time', time.time()),
            
            # ✅ NEW: Include actual and predicted metrics for healing context
                'actual_metrics': anomaly_result.get('actual_metrics', {}),
                'predicted_metrics': anomaly_result.get('predicted_metrics', {}),
            
            # ✅ NEW: Root cause analysis for targeted healing
                'root_cause_indicators': anomaly_result.get('root_cause_indicators', []),
                'affected_components': anomaly_result.get('affected_components', ['System_Health']),
            
            # ✅ NEW: Critical for healing plan generation
                'requires_immediate_action': True,  # All faults require action
                'priority': self.determine_fault_priority(fault_data.get('fault_severity', 0.0)),
            
            # ✅ NEW: Additional context for healing decisions
                'detection_timestamp': datetime.now().isoformat(),
                'message_id': f"CALC_FAULT_{int(time.time())}_{node_id}",
            
            # ✅ NEW: Include fault-specific technical details
                'technical_details': {
                'enhanced_anomaly_score': anomaly_result['anomaly_score'],
                'original_lstm_score': anomaly_result.get('original_lstm_score', anomaly_result['anomaly_score']),
                'score_enhancement_applied': True,
                'detection_threshold': getattr(detector, 'dynamic_anomaly_threshold', 0.0) if detector else 0.0
                }
            }
        
            await self.a2a_publisher.send_json(fault_alert)
            logger.info(f"🚨 COMPREHENSIVE fault alert sent for {node_id}: {fault_alert['fault_id']} "
                    f"(Type: {fault_data.get('fault_type')}, Severity: {fault_data.get('fault_severity', 0.0):.3f}, "
                    f"Priority: {fault_alert['priority']})")
        
        except Exception as e:
            logger.error(f"Failed to send fault alert for {node_id}: {e}")

    def determine_fault_priority(self, fault_severity: float) -> str:
        """
        Determine fault priority based on severity for healing agent prioritization
        """
        if fault_severity >= 0.8:
            return 'CRITICAL'
        elif fault_severity >= 0.6:
            return 'HIGH'
        elif fault_severity >= 0.4:
            return 'MEDIUM'
        else:
            return 'LOW'

    async def start(self):
        """
        Starts the Calculation Agent - NOW WITH PRE-TRAINED MODEL LOADING
        """
        logger.info("🚀 Calculation Agent started - LOADING PRE-TRAINED MODELS...")
    
    # Load training data to get feature info (needed for model architecture)
        node_training_data = await self.load_and_prepare_initial_training_data(self.config['training_data_file'])
    
        if self.input_features_count == 0 or not self.numerical_features_for_lstm:
            logger.error("No numerical features identified from training data. Cannot initialize detectors. Exiting.")
            sys.exit(1)
    
    # Initialize detectors
        self._initialize_detectors(self.input_features_count, self.numerical_features_for_lstm)
    
    # ✅ NEW: Load pre-trained models for all nodes
        models_loaded = 0
        models_need_training = 0
    
        for node_id in self.node_ids:
            detector = self.node_detectors[node_id]
        
        # Try to load existing model
            if detector.load_model():
                models_loaded += 1
                logger.info(f"✅ Node {node_id}: Pre-trained model loaded successfully!")
            else:
                models_need_training += 1
                logger.warning(f"⚠️ Node {node_id}: No pre-trained model found or loading failed")
            # You can choose to train here or skip
                detector.is_trained = False
    
        logger.info(f"📊 MODEL LOADING SUMMARY:")
        logger.info(f"   ✅ Models loaded: {models_loaded}/{len(self.node_ids)}")
        logger.info(f"   ⚠️ Models need training: {models_need_training}")
    
        if models_loaded == 0:
            logger.error("❌ No models could be loaded! Please check the lstm_model/ directory.")
            return
    
        logger.info("🎯 Calculation Agent: Entering live data monitoring phase...")
        logger.info("👂 Waiting for data from Monitor Agent...")
    
        self.is_running = True
        await self.data_processing_loop()

    async def stop(self):
        """
        Stops the Calculation Agent and cleans up resources.
        """
        logger.info("Calculation Agent: Stopping...")
        self.is_running = False
    
    # ✅ Fix the attribute name
        if hasattr(self, 'a2a_publisher'):
            self.a2a_publisher.close()
    
        if hasattr(self, '_mcp_push_socket'):
            self._mcp_push_socket.close()
    
        if hasattr(self, 'context'):
            self.context.term()
    
        logger.info("Calculation Agent: Stopped.")


if __name__ == "__main__":
    logger.info("Running standalone test for Calculation Agent...")

    test_pub_address_a2a = CALC_HEAL_PUB_SUB_ADDRESS
    test_push_address_mcp = CALC_MCP_PUSH_PULL_ADDRESS

    test_node_ids = [f"node_{i:02d}" for i in range(50)]

    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "lstm_sequence_length": 1,
            "lstm_epochs": 1,
            "anomaly_threshold_percentile": 99, # Default percentile
            "alert_debounce_interval": 5,
            "model_training_batch_size": 32,
            "train_on_startup": True,
            "training_data_limit": 950,
            "lstm_features": [
                'throughput', 'latency', 'packet_loss', 'voltage_level',
                'operational', 'node_type', 'current_time', 'jitter',
                'signal_strength', 'cpu_usage', 'memory_usage', 'buffer_occupancy',
                'active_links', 'neighbor_count', 'link_utilization', 'critical_load',
                'normal_load', 'energy_level',
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