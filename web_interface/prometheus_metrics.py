from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
import time
import threading
from typing import Dict, Any

class HealingAgentMetrics:
    def __init__(self):
        self.registry = CollectorRegistry()
        self._setup_metrics()
        self._agent_data = {}
        
    def _setup_metrics(self):
        # SHAP metrics for Node Exporter dashboard
        self.shap_anomaly_score = Gauge(
            'shap_anomaly_score',
            'SHAP-based anomaly detection scores',
            ['node_id', 'feature_name', 'agent_source'],
            registry=self.registry
        )
        
        # LSTM prediction metrics
        self.lstm_prediction = Gauge(
            'lstm_prediction_value',
            'LSTM predicted values from calculation agent',
            ['node_id', 'metric_type', 'prediction_horizon'],
            registry=self.registry
        )
        
        self.lstm_actual = Gauge(
            'lstm_actual_value', 
            'LSTM actual observed values',
            ['node_id', 'metric_type'],
            registry=self.registry
        )
        
        # Fault classification from healing agent
        self.fault_classification = Gauge(
            'fault_classification_confidence',
            'Fault classification confidence scores',
            ['node_id', 'fault_type', 'classifier_model'],
            registry=self.registry
        )
        
        # Healing plan status from orchestrator
        self.healing_plan_status = Gauge(
            'healing_plan_application_status',
            'Status of healing plan applications',
            ['anomaly_id', 'plan_id', 'status', 'tosca_template'],
            registry=self.registry
        )
        
        # Agent coordination metrics
        self.agent_health = Gauge(
            'agent_health_status',
            'Health status of individual agents',
            ['agent_name', 'agent_type'],
            registry=self.registry
        )
        
        # Network topology metrics from NS3
        self.network_topology_status = Gauge(
            'network_topology_node_status',
            'Status of nodes in network topology',
            ['node_id', 'node_type', 'layer', 'simulation_step'],
            registry=self.registry
        )
    
    def update_agent_metrics(self, agent_name: str, metrics_data: Dict[str, Any]):
        """Update metrics from individual agents"""
        self._agent_data[agent_name] = {
            'data': metrics_data,
            'timestamp': time.time()
        }
        
        if agent_name == 'monitor_agent':
            self._update_monitor_metrics(metrics_data)
        elif agent_name == 'calculation_agent':
            self._update_calculation_metrics(metrics_data)
        elif agent_name == 'healing_agent':
            self._update_healing_metrics(metrics_data)
        elif agent_name == 'orchestrator_agent':
            self._update_orchestrator_metrics(metrics_data)
    
    def _update_monitor_metrics(self, data):
        """Update metrics from monitor agent"""
        if 'shap_scores' in data:
            for node_id, features in data['shap_scores'].items():
                for feature_name, score in features.items():
                    self.shap_anomaly_score.labels(
                        node_id=node_id,
                        feature_name=feature_name,
                        agent_source='monitor_agent'
                    ).set(score)
    
    def _update_calculation_metrics(self, data):
        """Update metrics from calculation agent"""
        if 'lstm_predictions' in data:
            for prediction in data['lstm_predictions']:
                self.lstm_prediction.labels(
                    node_id=prediction['node_id'],
                    metric_type=prediction['metric_type'],
                    prediction_horizon=prediction.get('horizon', '1h')
                ).set(prediction['predicted_value'])
                
                if 'actual_value' in prediction:
                    self.lstm_actual.labels(
                        node_id=prediction['node_id'],
                        metric_type=prediction['metric_type']
                    ).set(prediction['actual_value'])
    
    def _update_healing_metrics(self, data):
        """Update metrics from healing agent"""
        if 'fault_classifications' in data:
            for classification in data['fault_classifications']:
                self.fault_classification.labels(
                    node_id=classification['node_id'],
                    fault_type=classification['fault_type'],
                    classifier_model=classification.get('model', 'default')
                ).set(classification['confidence'])
    
    def _update_orchestrator_metrics(self, data):
        """Update metrics from orchestrator agent with TOSCA integration"""
        if 'healing_plans' in data:
            for plan in data['healing_plans']:
                self.healing_plan_status.labels(
                    anomaly_id=plan['anomaly_id'],
                    plan_id=plan['plan_id'],
                    status=plan['status'],
                    tosca_template=plan.get('tosca_template', 'unknown')
                ).set(self._status_to_numeric(plan['status']))
    
    def _status_to_numeric(self, status: str) -> int:
        """Convert status strings to numeric values for Grafana"""
        status_map = {
            'pending': 0,
            'approved': 1,
            'executing': 2,
            'completed': 3,
            'failed': -1,
            'rejected': -2
        }
        return status_map.get(status.lower(), 0)

# Global metrics instance
metrics_collector = HealingAgentMetrics()