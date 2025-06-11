import requests
import json
import time

class NokiaGrafanaSetup:
    def __init__(self):
        self.grafana_url = "http://localhost:3000"
        self.username = "admin"
        self.password = "admin" 
        self.auth = (self.username, self.password)
        
    def setup_prometheus_datasource(self):
        """Add Prometheus data source"""
        datasource_config = {
            "name": "Nokia-Prometheus",
            "type": "prometheus",
            "url": "http://localhost:9090",
            "access": "proxy",
            "isDefault": True
        }
        
        response = requests.post(
            f"{self.grafana_url}/api/datasources",
            auth=self.auth,
            headers={"Content-Type": "application/json"},
            json=datasource_config
        )
        
        if response.status_code in [200, 409]:
            print("✅ Prometheus datasource configured")
            return True
        else:
            print(f"❌ Failed to setup datasource: {response.text}")
            return False
    
    def create_nokia_dashboard(self):
        """Create Nokia Build-a-thon dashboard"""
        dashboard = {
            "dashboard": {
                "id": None,
                "title": "Nokia Build-a-thon: AI Self-Healing Network with TOSCA",
                "tags": ["nokia", "build-a-thon", "ai", "tosca", "healing"],
                "timezone": "browser",
                "panels": [
                    # System Status Overview
                    {
                        "id": 1,
                        "title": "🏆 Nokia Build-a-thon System Status",
                        "type": "stat",
                        "gridPos": {"h": 4, "w": 24, "x": 0, "y": 0},
                        "targets": [{
                            "expr": "nokia_builathon_system_status",
                            "legendFormat": "{{component}}"
                        }],
                        "options": {
                            "colorMode": "background",
                            "graphMode": "area"
                        }
                    },
                    
                    # Agent Status
                    {
                        "id": 2,
                        "title": "🤖 Multi-Agent System Status",
                        "type": "stat", 
                        "gridPos": {"h": 6, "w": 8, "x": 0, "y": 4},
                        "targets": [{
                            "expr": "nokia_agent_status",
                            "legendFormat": "{{agent_name}}"
                        }]
                    },
                    
                    # Network Health
                    {
                        "id": 3,
                        "title": "🌐 Network Health",
                        "type": "gauge",
                        "gridPos": {"h": 6, "w": 8, "x": 8, "y": 4},
                        "targets": [{
                            "expr": "nokia_network_health_percentage",
                            "legendFormat": "Health %"
                        }],
                        "fieldConfig": {
                            "defaults": {
                                "min": 0,
                                "max": 100,
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": 0},
                                        {"color": "yellow", "value": 70},
                                        {"color": "green", "value": 90}
                                    ]
                                }
                            }
                        }
                    },
                    
                    # GPU Status
                    {
                        "id": 4,
                        "title": "🚀 GPU Acceleration",
                        "type": "stat",
                        "gridPos": {"h": 6, "w": 8, "x": 16, "y": 4},
                        "targets": [{
                            "expr": "nokia_gpu_acceleration_active",
                            "legendFormat": "RTX 3050 Active"
                        }]
                    },
                    
                    # TOSCA Workflows
                    {
                        "id": 5,
                        "title": "🎭 TOSCA Workflow Success Rate",
                        "type": "timeseries",
                        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 10},
                        "targets": [
                            {
                                "expr": "rate(nokia_tosca_workflows_successful_total[5m])",
                                "legendFormat": "Successful Workflows"
                            },
                            {
                                "expr": "rate(nokia_tosca_workflows_failed_total[5m])",
                                "legendFormat": "Failed Workflows"
                            }
                        ]
                    },
                    
                    # Node Status Grid
                    {
                        "id": 6,
                        "title": "📊 Node Status Grid",
                        "type": "timeseries",
                        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 10},
                        "targets": [{
                            "expr": "nokia_node_status",
                            "legendFormat": "{{node_id}} ({{node_type}})"
                        }]
                    }
                ],
                "time": {"from": "now-1h", "to": "now"},
                "refresh": "10s"
            },
            "overwrite": True
        }
        
        response = requests.post(
            f"{self.grafana_url}/api/dashboards/db",
            auth=self.auth,
            headers={"Content-Type": "application/json"},
            json=dashboard
        )
        
        if response.status_code == 200:
            result = response.json()
            dashboard_url = f"{self.grafana_url}/d/{result.get('uid', '')}"
            print(f"✅ Nokia dashboard created: {dashboard_url}")
            return dashboard_url
        else:
            print(f"❌ Failed to create dashboard: {response.text}")
            return None

def main():
    print("🔧 Setting up Grafana for Nokia Build-a-thon...")
    setup = NokiaGrafanaSetup()
    
    # Wait for Grafana to be ready
    print("🕐 Waiting for Grafana to start...")
    time.sleep(10)
    
    if setup.setup_prometheus_datasource():
        dashboard_url = setup.create_nokia_dashboard()
        if dashboard_url:
            print(f"\n🎉 Setup complete!")
            print(f"📊 Grafana Dashboard: http://localhost:3000")
            print(f"🔍 Prometheus: http://localhost:9090") 
            print(f"🚀 Your Nokia Dashboard: {dashboard_url}")

if __name__ == "__main__":
    main()