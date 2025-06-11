import requests
import json
import os

class NodeExporterDashboardEnhancer:
    def __init__(self, grafana_url="http://localhost:3000", api_key=None):
        self.grafana_url = grafana_url
        self.api_key = api_key or os.getenv('GRAFANA_API_KEY')
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def enhance_node_exporter_dashboard(self):
        """Download Node Exporter Full (ID: 1860) and enhance with healing agent metrics"""
        try:
            # Download original dashboard
            dashboard_url = "https://grafana.com/api/dashboards/1860/revisions/latest/download"
            response = requests.get(dashboard_url)
            original_dashboard = response.json()
            
            # Enhance with your custom panels
            enhanced_dashboard = self._add_healing_agent_panels(original_dashboard)
            
            # Import to Grafana
            import_payload = {
                "dashboard": enhanced_dashboard,
                "overwrite": True,
                "inputs": [{
                    "name": "DS_PROMETHEUS",
                    "type": "datasource", 
                    "pluginId": "prometheus",
                    "value": "Prometheus"
                }]
            }
            
            response = requests.post(
                f"{self.grafana_url}/api/dashboards/import",
                headers=self.headers,
                json=import_payload
            )
            
            return response.json()
            
        except Exception as e:
            print(f"Error enhancing dashboard: {e}")
            return None
    
    def _add_healing_agent_panels(self, dashboard):
        """Add your specific panels to Node Exporter dashboard"""
        
        # Shift existing panels down
        for panel in dashboard['panels']:
            panel['gridPos']['y'] += 16  # Make room for 4 rows of new panels
        
        # Add your custom panels at the top
        healing_panels = [
            # SHAP Anomaly Score Timeline
            {
                "id": 20001,
                "title": "🎯 SHAP Anomaly Score Timeline (Multi-Agent)",
                "type": "timeseries",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                "targets": [{
                    "expr": "shap_anomaly_score",
                    "legendFormat": "{{node_id}} - {{feature_name}} ({{agent_source}})",
                    "refId": "A"
                }],
                "fieldConfig": {
                    "defaults": {
                        "thresholds": {
                            "steps": [
                                {"color": "green", "value": None},
                                {"color": "yellow", "value": 0.3},
                                {"color": "red", "value": 0.7}
                            ]
                        }
                    }
                }
            },
            
            # LSTM Prediction vs Actual
            {
                "id": 20002,
                "title": "🤖 LSTM Prediction vs Actual (Calculation Agent)",
                "type": "timeseries",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                "targets": [
                    {
                        "expr": "lstm_prediction_value",
                        "legendFormat": "{{node_id}} - Predicted ({{metric_type}})",
                        "refId": "A"
                    },
                    {
                        "expr": "lstm_actual_value", 
                        "legendFormat": "{{node_id}} - Actual ({{metric_type}})",
                        "refId": "B"
                    }
                ]
            },
            
            # Fault Classification
            {
                "id": 20003,
                "title": "⚠️ Fault Classification (Healing Agent)",
                "type": "stat",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                "targets": [{
                    "expr": "fault_classification_confidence",
                    "legendFormat": "{{fault_type}} - {{node_id}}",
                    "refId": "A"
                }],
                "options": {
                    "colorMode": "background",
                    "graphMode": "area"
                }
            },
            
            # Healing Plan Application Status with TOSCA
            {
                "id": 20004,
                "title": "🔧 Healing Plan Status (TOSCA Orchestrator)",
                "type": "stat",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                "targets": [{
                    "expr": "healing_plan_application_status",
                    "legendFormat": "{{tosca_template}} - {{status}}",
                    "refId": "A"
                }],
                "fieldConfig": {
                    "defaults": {
                        "mappings": [
                            {"options": {"0": {"text": "⏳ Pending"}}, "type": "value"},
                            {"options": {"1": {"text": "✅ Approved"}}, "type": "value"},
                            {"options": {"2": {"text": "🔄 Executing"}}, "type": "value"},
                            {"options": {"3": {"text": "✅ Completed"}}, "type": "value"},
                            {"options": {"-1": {"text": "❌ Failed"}}, "type": "value"},
                            {"options": {"-2": {"text": "🚫 Rejected"}}, "type": "value"}
                        ]
                    }
                }
            }
        ]
        
        # Add panels to dashboard
        dashboard['panels'] = healing_panels + dashboard['panels']
        
        # Update metadata
        dashboard['title'] = "Node Exporter Full - Enhanced with Rural AI Self-Healing Network"
        dashboard['tags'].extend(["rural-ai", "self-healing", "multi-agent", "tosca"])
        
        return dashboard

if __name__ == "__main__":
    enhancer = NodeExporterDashboardEnhancer()
    result = enhancer.enhance_node_exporter_dashboard()
    print("Dashboard enhancement result:", result)