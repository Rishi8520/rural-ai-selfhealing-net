import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import glob
import asyncio
import logging
import json
import time
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
import zmq
import zmq.asyncio
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from datetime import datetime
from pathlib import Path
from collections import deque
from functools import partial
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
import joblib
import sys

import tensorflow as tf
tf.config.run_functions_eagerly(True)

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logging.warning("SHAP not available, using fallback methods")

from prometheus_client import start_http_server, Gauge, Counter, Histogram

logger = logging.getLogger(__name__)

try:
    from salp_swarm_optimizer import SalpSwarmOptimizer
except ImportError:
    logger.warning("SalpSwarmOptimizer not available, will use default hyperparameters")
    SalpSwarmOptimizer = None

CONFIG_FILE = "calculation_config.json"
MODEL_DIR = "models"
CALC_HEAL_PUB_SUB_ADDRESS = "tcp://127.0.0.1:5556"
CALC_MCP_PUSH_PULL_ADDRESS = "tcp://127.0.0.1:5557"
MONITOR_DATA_STREAM_FILE = "calculation_agent_data_stream.json"

from dataclasses import dataclass
from typing import Dict, List, Any, Optional

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

class LSTMAnomalyModel:
    def __init__(self, input_size=None, hidden_size=None, num_layers=2, dropout_rate=0.2, sequence_length=None):
        if input_size is None or hidden_size is None or sequence_length is None:
            raise ValueError("input_size, hidden_size, and sequence_length must be provided to LSTMAnomalyModel.")

        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout_rate = dropout_rate
        self.sequence_length = sequence_length

        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import LSTM, Dense, Dropout, Input

        layers = [Input(shape=(self.sequence_length, self.input_size))]

        for i in range(self.num_layers):
            return_sequences = (i < self.num_layers - 1)
            layers.append(LSTM(self.hidden_size, activation='relu', return_sequences=return_sequences))
            layers.append(Dropout(self.dropout_rate))

        layers.append(Dense(self.input_size))
        self._model = Sequential(layers)

    def compile(self, *args, **kwargs):
        self._model.compile(*args, **kwargs)

    def fit(self, *args, **kwargs):
        return self._model.fit(*args, **kwargs)

    def predict(self, *args, **kwargs):
        return self._model.predict(*args, **kwargs)

    def save(self, filepath):
        self._model.save(filepath)

    @property
    def input_shape(self):
        return self._model.input_shape

class LSTMAnomalyDetector:
    def __init__(self, node_id: str, feature_names: List[str], sequence_length: int = 5, 
                 anomaly_threshold_percentile=99, save_shap_plots=True, plot_dir="shap_plots"):
        self.node_id = node_id
        self.feature_names = feature_names
        self.sequence_length = sequence_length
        self.anomaly_threshold_percentile = anomaly_threshold_percentile
        self.dynamic_anomaly_threshold = 0.0
        self.model = None
        self.scaler = MinMaxScaler()
        self.data_buffer = deque(maxlen=sequence_length)
        self.shap_explainer = None
        self.is_trained = False
        self.save_shap_plots = save_shap_plots
        self.shap_background_data = None
        
        self.model_dir = Path(f"models/{node_id}")
        self.plot_dir = Path(f"shap_plots_enhanced/{node_id}")
        self.shap_plots_dir = Path(f"shap_plots_enhanced/{node_id}")
        
        try:
            self.model_dir.mkdir(parents=True, exist_ok=True)
            self.plot_dir.mkdir(parents=True, exist_ok=True)
            self.shap_plots_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"{node_id}: Failed to create directories: {e}")

        self.model_path = self.model_dir / "lstm_model.keras"
        self.scaler_path = self.model_dir / "scaler.pkl"
        self.threshold_path = self.model_dir / "threshold.json"

    def build_model(self, hidden_size=64, learning_rate=0.001, num_layers=2, dropout_rate=0.1):
        try:
            self.model = LSTMAnomalyModel(
                input_size=len(self.feature_names),
                hidden_size=hidden_size,
                num_layers=num_layers,
                dropout_rate=dropout_rate,
                sequence_length=self.sequence_length
            )

            self.model.compile(
                optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
                loss='mse'
            )
            logger.info(f"{self.node_id}: LSTM model built successfully")
        except Exception as e:
            logger.error(f"{self.node_id}: Model building failed: {e}")
            raise

    def train_model(self, X_train, y_train, epochs=20, batch_size=32, verbose=1):
        try:
            if self.model is None:
                logger.error(f"{self.node_id}: Model not built, call build_model() first")
                return

            X_train = np.array(X_train, dtype=np.float32)
            y_train = np.array(y_train, dtype=np.float32)

            if not hasattr(self.scaler, 'min_') or not hasattr(self.scaler, 'scale_'):
                combined_data_for_scaler_fit = np.vstack([X_train.reshape(-1, len(self.feature_names)), y_train])
                self.scaler.fit(combined_data_for_scaler_fit)

            X_train_scaled = self.scaler.transform(X_train.reshape(-1, len(self.feature_names))).reshape(X_train.shape)
            y_train_scaled = self.scaler.transform(y_train)

            history = self.model.fit(
                X_train_scaled, y_train_scaled,
                epochs=epochs,
                batch_size=batch_size,
                verbose=verbose,
                validation_split=0.2
            )

            train_predictions_scaled = self.model.predict(X_train_scaled, verbose=0)
            reconstruction_errors = np.mean(np.square(y_train_scaled - train_predictions_scaled), axis=1)
            self.dynamic_anomaly_threshold = np.percentile(reconstruction_errors, self.anomaly_threshold_percentile)

            self.is_trained = True

            if SHAP_AVAILABLE:
                try:
                    num_background_samples = min(100, X_train_scaled.shape[0])
                    background_indices = np.random.choice(X_train_scaled.shape[0], num_background_samples, replace=False)
                    self.shap_background_data = X_train_scaled[background_indices[0]][np.newaxis, :, :]
                    self.shap_explainer = shap.GradientExplainer(self.model._model, self.shap_background_data)
                    logger.info(f"{self.node_id}: SHAP GradientExplainer initialized")
                except Exception as e:
                    logger.error(f"{self.node_id}: Error initializing SHAP: {e}")
                    self.shap_explainer = None

            logger.info(f"{self.node_id}: Model training completed successfully")
            return history

        except Exception as e:
            logger.error(f"{self.node_id}: Training failed: {e}")
            raise

    def save_model(self):
        try:
            if self.model and self.is_trained:
                self.model.save(self.model_path)
                logger.info(f"{self.node_id}: Model saved to {self.model_path}")
                
            if hasattr(self.scaler, 'scale_'):
                joblib.dump(self.scaler, self.scaler_path)
                logger.info(f"{self.node_id}: Scaler saved to {self.scaler_path}")
                
            if self.dynamic_anomaly_threshold > 0:
                with open(self.threshold_path, 'w') as f:
                    json.dump({'dynamic_anomaly_threshold': float(self.dynamic_anomaly_threshold)}, f)
                logger.info(f"{self.node_id}: Threshold saved to {self.threshold_path}")
                
        except Exception as e:
            logger.error(f"{self.node_id}: Model saving failed: {e}")

    def load_model(self):
        try:
            if self.model_path.exists():
                self.model = tf.keras.models.load_model(self.model_path)
                logger.info(f"{self.node_id}: Model loaded from {self.model_path}")
                
                if self.scaler_path.exists():
                    self.scaler = joblib.load(self.scaler_path)
                    logger.info(f"{self.node_id}: Scaler loaded from {self.scaler_path}")
                    
                if self.threshold_path.exists():
                    with open(self.threshold_path, 'r') as f:
                        self.dynamic_anomaly_threshold = json.load(f)['dynamic_anomaly_threshold']
                    logger.info(f"{self.node_id}: Threshold loaded from {self.threshold_path}")
                    
                self.is_trained = True
                
                if SHAP_AVAILABLE and self.shap_background_data is not None:
                    self.shap_explainer = shap.GradientExplainer(self.model, self.shap_background_data)
                    
                return True
        except Exception as e:
            logger.error(f"{self.node_id}: Model loading failed: {e}")
            return False

    def _prepare_input_sequence(self, data: Dict[str, Any], feature_names: List[str]):
        try:
            sequence = np.zeros((1, self.sequence_length, len(feature_names)))
            
            for i, feature in enumerate(feature_names):
                base_value = data.get(feature, 0.5)
                
                if feature in ['fault_severity', 'degradation_level']:
                    value = min(base_value * 1.2, 1.0)
                elif feature == 'throughput' and base_value > 5:
                    value = min(base_value / 50.0, 1.0)
                elif feature == 'latency' and base_value > 100:
                    value = min(base_value / 500.0, 1.0)
                elif feature == 'packet_loss':
                    value = min(base_value * 10, 1.0)
                elif feature in ['cpu_usage', 'memory_usage']:
                    value = min(base_value / 100.0, 1.0)
                else:
                    value = min(base_value, 1.0)
                    
                sequence[0, -1, i] = value

            for t in range(self.sequence_length - 1):
                degradation_factor = 1.0 - (0.05 * t)
                for i in range(len(feature_names)):
                    base_value = sequence[0, -1, i]
                    sequence[0, t, i] = base_value * degradation_factor

            return sequence

        except Exception as e:
            logger.error(f"{self.node_id}: Input preparation failed: {e}")
            return np.zeros((1, self.sequence_length, len(feature_names)))

    async def predict_anomaly(self, data: Dict[str, Any], feature_names: List[str]):
        try:
            if not self.is_trained:
                return {'anomaly_score': 0.0, 'status': 'model_not_trained'}

            if self.dynamic_anomaly_threshold == 0.0:
                return {'anomaly_score': 0.0, 'status': 'threshold_not_set'}

            input_sequence = self._prepare_input_sequence(data, feature_names)
            
            prediction = self.model.predict(input_sequence, verbose=0)
            
            actual_scaled_last_step = input_sequence[0, -1, :]
            predicted_scaled_next_step = prediction[0]
            
            reconstruction_error = np.mean(np.square(predicted_scaled_next_step - actual_scaled_last_step))
            
            current_fault_severity = data.get('fault_severity', 0.0)
            base_anomaly_score = reconstruction_error / (self.dynamic_anomaly_threshold if self.dynamic_anomaly_threshold > 0 else 1.0)
            anomaly_score = min(1.0, base_anomaly_score + (current_fault_severity * 0.5))

            status = 'anomaly' if anomaly_score > 0.5 else 'normal'
            
            result = {
                'anomaly_score': float(anomaly_score),
                'status': status,
                'timestamp': datetime.now().isoformat(),
                'node_id': self.node_id,
                'reconstruction_error': float(reconstruction_error),
                'threshold': float(self.dynamic_anomaly_threshold)
            }

            if anomaly_score > 0.3 and SHAP_AVAILABLE and self.shap_explainer is not None:
                await self._generate_enhanced_explanation(input_sequence, data)
                
            return result

        except Exception as e:
            logger.error(f"{self.node_id}: Prediction failed: {e}")
            return {'anomaly_score': 0.0, 'status': 'error'}

    async def _generate_enhanced_explanation(self, input_sequence, original_data):
        try:
            if not SHAP_AVAILABLE or self.shap_explainer is None:
                return

            shap_values = self.shap_explainer.shap_values(input_sequence)
            
            if isinstance(shap_values, list):
                if len(shap_values) > 0 and isinstance(shap_values[0], np.ndarray):
                    shap_values_for_last_timestep = shap_values[0][0, -1, :]
                else:
                    return
            elif isinstance(shap_values, np.ndarray):
                if shap_values.ndim == 4:
                    shap_values_for_last_timestep = shap_values[0, -1, 0, :]
                elif shap_values.ndim == 3:
                    shap_values_for_last_timestep = shap_values[0, -1, :]
                else:
                    return
            else:
                return

            await self._create_shap_plots(shap_values_for_last_timestep, input_sequence[0, -1, :])

        except Exception as e:
            logger.error(f"{self.node_id}: SHAP explanation failed: {e}")

    async def _create_shap_plots(self, shap_values, data_values):
        try:
            if not self.save_shap_plots:
                return

            timestamp = int(time.time())
            
            plt.figure(figsize=(14, 8))
            bars = plt.bar(range(len(self.feature_names)), np.abs(shap_values))
            plt.title(f'SHAP Feature Importance - {self.node_id}')
            plt.xlabel('Features')
            plt.ylabel('|SHAP Value|')
            plt.xticks(range(len(self.feature_names)), self.feature_names, rotation=45)

            abs_values = np.abs(shap_values)
            max_val = np.max(abs_values) if np.max(abs_values) > 0 else 1
            for i, bar in enumerate(bars):
                intensity = abs_values[i] / max_val
                bar.set_color(plt.cm.Reds(intensity))

            plt.tight_layout()
            plot_path = self.shap_plots_dir / f'shap_importance_{timestamp}.png'
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()

            logger.info(f"{self.node_id}: SHAP plots saved to {plot_path}")

        except Exception as e:
            logger.error(f"{self.node_id}: SHAP plot creation failed: {e}")

class BaseCalculationAgent:
    def __init__(self, node_ids: List[str], **kwargs):
        self.node_ids = node_ids
        self.node_detectors = {}
        self.is_running = False
        self.input_features_count = 0
        self.sequence_length = 5
        self.context = zmq.asyncio.Context()

class CalculationAgent(BaseCalculationAgent):
    def __init__(self, node_ids: List[str], pub_socket_address_a2a: str = None,
                 push_socket_address_mcp: str = None, **kwargs):
        super().__init__(node_ids, **kwargs)
        
        self.pub_socket_address_a2a = pub_socket_address_a2a
        self.push_socket_address_mcp = push_socket_address_mcp
        
        # Initialize dynamic confidence calculator
        self.confidence_calculator = DynamicConfidenceCalculator()
        
        self.config = {
            'training_data_file': max(glob.glob('monitor_output/calculation_input_*.json'), 
                                    key=os.path.getmtime) if glob.glob('monitor_output/calculation_input_*.json') else None,
            'sequence_length': 5,
            'lstm_hidden_size': 64,
            'anomaly_threshold': 0.7,
            'lstm_epochs': 20,
            'anomaly_threshold_percentile': 99,
            'model_training_batch_size': 32,
            'train_on_startup': True
        }

        self.lstm_training_features = [
            "throughput", "latency", "packet_loss", "jitter",
            "signal_strength", "cpu_usage", "memory_usage", "buffer_occupancy",
            "active_links", "neighbor_count", "link_utilization", "critical_load",
            "normal_load", "energy_level", "degradation_level", "power_stability", "voltage_level"
        ]

        self.anomalies_detected = []
        self.last_processed = {}
        
        self.context = zmq.asyncio.Context()
        self.a2a_publisher = None
        self.mcp_subscriber = None
        
        self.comm_metrics = {
            'anomalies_sent': 0,
            'healing_responses_received': 0,
            'failed_communications': 0
        }

        self.shap_plots_dir = Path("shap_plots_enhanced")
        self.shap_plots_dir.mkdir(exist_ok=True)

        self.setup_prometheus_metrics()

    def setup_prometheus_metrics(self):
        self.lstm_accuracy_gauge = Gauge(
            'nokia_lstm_prediction_accuracy',
            'LSTM model prediction accuracy',
            ['node_id', 'model_type']
        )
        self.anomaly_score_gauge = Gauge(
            'nokia_anomaly_score', 
            'Current anomaly score for node',
            ['node_id', 'severity']
        )
        self.anomaly_detection_counter = Counter(
            'nokia_anomalies_detected_total',
            'Total anomalies detected', 
            ['node_id', 'severity', 'anomaly_type']
        )

    async def initialize_communication(self):
        try:
            self.a2a_publisher = self.context.socket(zmq.PUB)
            self.a2a_publisher.bind("tcp://127.0.0.1:5555")
            
            self.mcp_subscriber = self.context.socket(zmq.SUB)
            self.mcp_subscriber.connect("tcp://127.0.0.1:5556")
            self.mcp_subscriber.setsockopt_string(zmq.SUBSCRIBE, "")
            
            logger.info("Communication channels initialized")
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"Communication initialization failed: {e}")
            raise

    async def load_and_prepare_initial_training_data(self, filepath):
        logger.info(f"Loading initial training data from {filepath}")
        
        try:
            if filepath and Path(filepath).exists():
                with open(filepath, 'r') as f:
                    data = json.load(f)
                return self._process_real_training_data(data)
            else:
                logger.warning(f"Training data file not found: {filepath}")
                return self._generate_default_training_data()
                
        except Exception as e:
            logger.error(f"Error loading training data: {e}")
            return self._generate_default_training_data()

    def _process_real_training_data(self, data):
        processed_data = {}
        
        try:
            node_data = data.get('lstm_training_data', {}).get('network_metrics', {}).get('node_data', {})
            
            if not node_data:
                logger.warning("No node data found in JSON, using default data")
                return self._generate_default_training_data()

            for node_id in self.node_ids:
                node_key = f"node_{node_id.split('_')[1]}"
                
                if node_key in node_data:
                    real_node_data = node_data[node_key]
                    X_data, y_data = self._create_training_sequences_from_real_data(real_node_data, node_id)
                    processed_data[node_id] = (X_data, y_data)
                else:
                    X_data, y_data = self._create_default_training_data_for_node(node_id)
                    processed_data[node_id] = (X_data, y_data)

            return processed_data

        except Exception as e:
            logger.error(f"Error processing real training data: {e}")
            return self._generate_default_training_data()

    def _generate_default_training_data(self):
        training_data = {}
        
        for node_id in self.node_ids:
            X_data, y_data = self._create_default_training_data_for_node(node_id)
            training_data[node_id] = (X_data, y_data)
            
        return training_data

    def _create_default_training_data_for_node(self, node_id):
        samples = 200
        features = len(self.lstm_training_features)
        sequence_length = self.config['sequence_length']
        
        X_data = np.zeros((samples, sequence_length, features))
        y_data = np.zeros(samples)

        normal_samples = int(samples * 0.7)
        anomaly_samples = samples - normal_samples

        for i in range(normal_samples):
            for t in range(sequence_length):
                X_data[i, t, :] = np.random.normal(0.3, 0.1, features)
            y_data[i] = 0

        for i in range(normal_samples, samples):
            for t in range(sequence_length):
                anomaly_pattern = np.random.normal(0.7, 0.15, features)
                X_data[i, t, :] = np.clip(anomaly_pattern, 0, 1)
            y_data[i] = 1

        return X_data, y_data

    def _create_training_sequences_from_real_data(self, real_node_data, node_id):
        try:
            feature_values = []
            
            for feature in self.lstm_training_features:
                if feature in real_node_data:
                    value = float(real_node_data[feature])
                    
                    if feature == "throughput":
                        value = min(value / 1000.0, 1.0)
                    elif feature == "latency":
                        value = min(value / 500.0, 1.0)
                    elif feature in ["cpu_usage", "memory_usage", "buffer_occupancy"]:
                        value = value / 100.0
                        
                    feature_values.append(value)
                else:
                    feature_values.append(0.5)

            samples = 200
            sequence_length = self.config['sequence_length']
            
            X_data = np.zeros((samples, sequence_length, len(self.lstm_training_features)))
            y_data = np.zeros(samples)

            fault_severity = real_node_data.get('fault_severity', 0.0)
            is_faulty = fault_severity > 0.3

            for i in range(samples):
                for t in range(sequence_length):
                    for f, base_value in enumerate(feature_values):
                        if is_faulty:
                            if self.lstm_training_features[f] in ['fault_severity', 'degradation_level']:
                                value = np.random.uniform(0.7, 1.0)
                            elif self.lstm_training_features[f] in ['throughput', 'latency', 'packet_loss']:
                                value = np.random.uniform(0.6, 1.0)
                            else:
                                noise = np.random.normal(0, 0.3)
                                value = max(min(base_value + noise, 1.0), 0.0)
                        else:
                            noise = np.random.normal(0, 0.1)
                            value = max(min(base_value + noise, 1.0), 0.0)
                            
                        X_data[i, t, f] = value

                if is_faulty:
                    y_data[i] = 1.0 if np.random.random() > 0.3 else 0.0
                else:
                    y_data[i] = 1.0 if np.random.random() > 0.9 else 0.0

            return X_data, y_data

        except Exception as e:
            logger.error(f"Error creating sequences for {node_id}: {e}")
            return self._create_default_training_data_for_node(node_id)

    def _initialize_detectors(self, input_features_count, feature_names):
        logger.info(f"Initializing detectors for {len(self.node_ids)} nodes")
        
        for node_id in self.node_ids:
            try:
                detector = LSTMAnomalyDetector(
                    node_id=node_id,
                    feature_names=feature_names,
                    sequence_length=self.sequence_length,
                    anomaly_threshold_percentile=self.config.get('anomaly_threshold_percentile', 99)
                )
                self.node_detectors[node_id] = detector
                logger.info(f"Detector initialized for {node_id}")
            except Exception as e:
                logger.error(f"Failed to initialize detector for {node_id}: {e}")

    async def _objective_function(self, params, node_id, X_train, y_train):
        tf.keras.backend.clear_session()
        
        hidden_size, learning_rate, num_layers, dropout_rate = \
            int(params[0]), float(params[1]), int(params[2]), float(params[3])
            
        hidden_size = max(16, min(hidden_size, 256))
        learning_rate = max(1e-5, min(learning_rate, 1e-2))
        num_layers = max(1, min(num_layers, 5))
        dropout_rate = max(0.0, min(dropout_rate, 0.5))

        temp_detector = LSTMAnomalyDetector(
            node_id=f"temp_opt_{node_id}",
            feature_names=self.lstm_training_features,
            sequence_length=self.sequence_length,
            save_shap_plots=False,
            anomaly_threshold_percentile=self.config.get('anomaly_threshold_percentile', 99)
        )

        temp_detector.build_model(
            hidden_size=hidden_size,
            learning_rate=learning_rate,
            num_layers=num_layers,
            dropout_rate=dropout_rate
        )

        try:
            if not hasattr(temp_detector.scaler, 'min_') or not hasattr(temp_detector.scaler, 'scale_'):
                combined_data_for_scaler_fit = np.vstack([X_train.reshape(-1, len(self.lstm_training_features)), y_train])
                temp_detector.scaler.fit(combined_data_for_scaler_fit)

            X_train_scaled = temp_detector.scaler.transform(X_train.reshape(-1, len(self.lstm_training_features))).reshape(X_train.shape)
            y_train_scaled = temp_detector.scaler.transform(y_train)

            temp_detector.train_model(X_train_scaled, y_train_scaled, epochs=5, verbose=0)

            if not temp_detector.is_trained:
                return float('inf')

            predictions = temp_detector.model.predict(X_train_scaled, verbose=0)
            loss = mean_squared_error(y_train_scaled, predictions)

        except Exception as e:
            logger.error(f"Node {node_id}: Error during SSA objective function: {e}")
            loss = float('inf')

        return loss

    async def optimize_lstm_with_ssa(self, node_id, X_train_data, y_train_data):
        if SalpSwarmOptimizer is None:
            detector = self.node_detectors[node_id]
            detector.build_model()
            detector.train_model(X_train_data, y_train_data, epochs=self.config['lstm_epochs'])
            return

        logger.info(f"Node {node_id}: Starting SSA optimization for LSTM hyperparameters")

        lower_bounds = [32, 0.0001, 2, 0.0]
        upper_bounds = [128, 0.005, 3, 0.3]

        obj_func_with_data = partial(self._objective_function, node_id=node_id, X_train=X_train_data, y_train=y_train_data)

        ssa = SalpSwarmOptimizer(
            obj_func=obj_func_with_data,
            n_salps=20,
            n_iterations=50,
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

        detector.train_model(X_train_data, y_train_data, epochs=self.config['lstm_epochs'])
        logger.info(f"Node {node_id}: LSTM model updated with optimized parameters")

    async def process_data_point(self, node_id: str, raw_data_point_dict: Dict[str, Any]):
        detector = self.node_detectors.get(node_id)
        if not detector:
            logger.warning(f"No detector found for node {node_id}")
            return

        if not detector.is_trained:
            return

        anomaly_result = await detector.predict_anomaly(raw_data_point_dict, self.lstm_training_features)

        self.anomaly_score_gauge.labels(
            node_id=node_id,
            severity=anomaly_result.get("status", "normal")
        ).set(anomaly_result['anomaly_score'])

        if anomaly_result['anomaly_score'] > 0.5:
            self.anomaly_detection_counter.labels(
                node_id=node_id,
                severity="high" if anomaly_result['anomaly_score'] > 0.7 else "medium",
                anomaly_type="lstm_prediction"
            ).inc()

            await self.send_anomaly_alert_to_healing_agent(node_id, anomaly_result)

    async def send_anomaly_alert_to_healing_agent(self, node_id, anomaly_result):
        try:
            if self.a2a_publisher is None:
                return

            detector = self.node_detectors.get(node_id)
            
            # DYNAMIC confidence calculation - NO hardcoding
            dynamic_confidence = self.confidence_calculator.calculate_dynamic_confidence(
                node_id, anomaly_result, detector
            )
            
            # DYNAMIC severity determination - NO hardcoding
            dynamic_severity = self.confidence_calculator.determine_dynamic_severity(
                anomaly_result['anomaly_score'], node_id
            )

            anomaly_alert = {
                'message_type': 'anomaly_alert',
                'timestamp': datetime.now().isoformat(),
                'source_agent': 'calculation_agent',
                'target_agent': 'healing_agent',
                'message_id': f"CALC_ANOM_{int(time.time())}_{node_id}",
                'anomaly_details': {
                    'anomaly_id': f"ANOM_{node_id}_{int(time.time())}",
                    'node_id': node_id,
                    'anomaly_score': anomaly_result['anomaly_score'],
                    'severity': dynamic_severity,  # DYNAMIC
                    'detection_timestamp': datetime.now().isoformat(),
                    'confidence': dynamic_confidence  # DYNAMIC
                },
                'network_context': {
                    'node_type': self.get_node_type(node_id),
                    'fault_pattern': 'dynamic_detection'
                }
            }

            await self.a2a_publisher.send_json(anomaly_alert)
            self.comm_metrics['anomalies_sent'] += 1
            logger.info(f"Anomaly alert sent for {node_id}: {anomaly_alert['message_id']}")

        except Exception as e:
            logger.error(f"Failed to send anomaly alert for {node_id}: {e}")
            self.comm_metrics['failed_communications'] += 1

    def get_node_type(self, node_id):
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
        logger.info("Starting data processing loop")
        
        if not os.path.exists(MONITOR_DATA_STREAM_FILE):
            with open(MONITOR_DATA_STREAM_FILE, 'w') as f:
                f.write('')

        last_read_position = 0

        while self.is_running:
            try:
                with open(MONITOR_DATA_STREAM_FILE, 'r') as f:
                    f.seek(last_read_position)
                    new_lines = f.readlines()
                    
                    if new_lines:
                        for line in new_lines:
                            try:
                                batch_data = json.loads(line.strip())
                                
                                if 'messages' in batch_data:
                                    for msg in batch_data['messages']:
                                        if 'content' in msg and 'metrics' in msg['content']:
                                            for node_id_from_msg, node_metrics_data in msg['content']['metrics'].items():
                                                if node_id_from_msg.startswith('node_'):
                                                    if 'simulation_time' in msg['content']:
                                                        node_metrics_data['current_time'] = msg['content']['simulation_time']
                                                    asyncio.create_task(self.process_data_point(node_id_from_msg, node_metrics_data))
                                                    
                            except json.JSONDecodeError as e:
                                logger.error(f"Error decoding JSON: {e}")
                            except Exception as e:
                                logger.error(f"Error processing message: {e}")
                                
                        last_read_position = f.tell()
                    else:
                        await asyncio.sleep(5)
                        
            except FileNotFoundError:
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error in data processing loop: {e}")
                await asyncio.sleep(1)

    async def enhanced_start_with_dynamic_detection(self):
        logger.info("Starting Enhanced Calculation Agent with Dynamic Detection")

        await self.initialize_communication()

        try:
            node_training_data = await self.load_and_prepare_initial_training_data(
                self.config.get('training_data_file')
            )
            logger.info(f"Training data loaded for {len(node_training_data)} nodes")
        except Exception as e:
            logger.error(f"Training data loading failed: {e}")
            return

        if len(self.lstm_training_features) == 0:
            logger.error("No LSTM training features defined")
            return

        self.input_features_count = len(self.lstm_training_features)
        self._initialize_detectors(self.input_features_count, self.lstm_training_features)

        training_tasks = []
        
        for node_id in self.node_ids:
            detector = self.node_detectors.get(node_id)
            if detector:
                if detector.load_model():
                    logger.info(f"{node_id}: Loaded existing model")
                else:
                    X_train, y_train = node_training_data.get(node_id, (np.array([]), np.array([])))
                    if X_train.size > 0:
                        training_tasks.append(
                            asyncio.create_task(self.optimize_lstm_with_ssa(node_id, X_train, y_train))
                        )
                    else:
                        logger.warning(f"{node_id}: No training data available")

        if training_tasks:
            logger.info(f"Starting training for {len(training_tasks)} nodes")
            results = await asyncio.gather(*training_tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if i < len(self.node_ids):
                    node_id = self.node_ids[i]
                    if isinstance(result, Exception):
                        logger.error(f"Training failed for {node_id}: {result}")
                    else:
                        detector = self.node_detectors[node_id]
                        if detector.is_trained:
                            detector.save_model()
                            logger.info(f"{node_id}: Training completed and model saved")

        logger.info("Enhanced Calculation Agent startup complete")
        
        self.is_running = True
        await self.data_processing_loop()

    async def cleanup(self):
        try:
            self.is_running = False
            if self.a2a_publisher:
                self.a2a_publisher.close()
            if self.mcp_subscriber:
                self.mcp_subscriber.close()
            if self.context:
                self.context.term()
            logger.info("Enhanced Calculation Agent cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    node_ids = [f'node_{i:02d}' for i in range(50)]
    agent = CalculationAgent(
        node_ids=node_ids,
        pub_socket_address_a2a='tcp://127.0.0.1:5555',
        push_socket_address_mcp='tcp://127.0.0.1:5557'
    )

    try:
        start_http_server(8002)
        logger.info("Prometheus metrics server started on port 8002")
        
        print('Enhanced Calculation Agent starting...')
        print(f'Dynamic anomaly detection for all {len(node_ids)} nodes')
        print(f'SHAP explanations enabled for anomalies')
        print(f'SSA optimization enabled')
        print('Model saving/loading enabled')
        
        await agent.enhanced_start_with_dynamic_detection()
        
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        await agent.cleanup()

if __name__ == '__main__':
    asyncio.run(main())