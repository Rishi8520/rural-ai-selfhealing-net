import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any

class FallbackKnowledgeBase:
    def __init__(self):
        self.static_knowledge = self._load_static_knowledge()
        self.fallback_db_path = 'fallback_knowledge.db'
        self._create_fallback_db()
    
    def _load_static_knowledge(self) -> Dict[str, Any]:
        """Load static knowledge for fallback scenarios"""
        return {
            'node_types': [
                {
                    'name': 'Core_Router',
                    'description': 'High-performance core network router',
                    'critical_metrics': ['throughput', 'packet_loss', 'cpu_usage', 'memory_usage'],
                    'common_faults': ['power_failure', 'fiber_cut', 'equipment_overload', 'software_bug'],
                    'healing_strategies': ['emergency_reroute', 'backup_power', 'load_balancing', 'redundant_path']
                },
                {
                    'name': 'Distribution_Switch',
                    'description': 'Regional distribution switch',
                    'critical_metrics': ['bandwidth_utilization', 'latency', 'buffer_occupancy', 'link_status'],
                    'common_faults': ['link_failure', 'congestion', 'power_instability', 'configuration_error'],
                    'healing_strategies': ['traffic_rerouting', 'qos_adjustment', 'power_switching', 'config_rollback']
                },
                {
                    'name': 'Access_Point',
                    'description': 'End-user access point',
                    'critical_metrics': ['signal_strength', 'user_count', 'data_rate', 'error_rate'],
                    'common_faults': ['interference', 'weather_impact', 'equipment_aging', 'user_overload'],
                    'healing_strategies': ['power_adjustment', 'channel_switching', 'load_shedding', 'antenna_optimization']
                }
            ],
            'fault_patterns': [
                {
                    'name': 'Cascading_Failure',
                    'symptoms': ['multiple_node_failures', 'traffic_blackhole', 'widespread_outage'],
                    'causes': ['fiber_cut', 'power_grid_failure', 'software_bug'],
                    'healing_actions': ['emergency_isolation', 'traffic_rerouting', 'backup_activation']
                },
                {
                    'name': 'Performance_Degradation',
                    'symptoms': ['high_latency', 'packet_loss', 'slow_response'],
                    'causes': ['network_congestion', 'equipment_aging', 'misconfiguration'],
                    'healing_actions': ['load_balancing', 'qos_optimization', 'equipment_restart']
                }
            ],
            'healing_templates': [
                {
                    'name': 'Emergency_Isolation',
                    'action_type': 'isolation',
                    'description': 'Isolate failing component to prevent cascade',
                    'duration': 60,
                    'success_rate': 0.9,
                    'prerequisites': ['backup_path_available']
                },
                {
                    'name': 'Gradual_Recovery',
                    'action_type': 'recovery',
                    'description': 'Gradually restore service with monitoring',
                    'duration': 300,
                    'success_rate': 0.8,
                    'prerequisites': ['root_cause_identified']
                }
            ],
            'recovery_tactics': [
                {
                    'id': 'FALLBACK_001',
                    'name': 'Emergency_Shutdown',
                    'description': 'Emergency shutdown to prevent damage',
                    'estimated_time': 30,
                    'priority': 'critical',
                    'applicable_node_types': ['Core_Router', 'Distribution_Switch', 'Access_Point']
                },
                {
                    'id': 'FALLBACK_002', 
                    'name': 'Safe_Mode_Activation',
                    'description': 'Activate safe mode with minimal functionality',
                    'estimated_time': 120,
                    'priority': 'high',
                    'applicable_node_types': ['Distribution_Switch', 'Access_Point']
                }
            ]
        }
    
    def _create_fallback_db(self):
        """Create fallback SQLite database"""
        try:
            conn = sqlite3.connect(self.fallback_db_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS fallback_node_types (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    knowledge_json TEXT
                );
                
                CREATE TABLE IF NOT EXISTS fallback_patterns (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    knowledge_json TEXT
                );
                
                CREATE TABLE IF NOT EXISTS fallback_templates (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    action_type TEXT,
                    knowledge_json TEXT
                );
                
                CREATE TABLE IF NOT EXISTS fallback_tactics (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    knowledge_json TEXT
                );
            """)
            
            # Insert fallback data
            for i, node_type in enumerate(self.static_knowledge['node_types']):
                cursor.execute(
                    "INSERT OR REPLACE INTO fallback_node_types (id, name, description, knowledge_json) VALUES (?, ?, ?, ?)",
                    (i+1, node_type['name'], node_type['description'], json.dumps(node_type))
                )
            
            for i, pattern in enumerate(self.static_knowledge['fault_patterns']):
                cursor.execute(
                    "INSERT OR REPLACE INTO fallback_patterns (id, name, knowledge_json) VALUES (?, ?, ?)",
                    (i+1, pattern['name'], json.dumps(pattern))
                )
            
            for i, template in enumerate(self.static_knowledge['healing_templates']):
                cursor.execute(
                    "INSERT OR REPLACE INTO fallback_templates (id, name, action_type, knowledge_json) VALUES (?, ?, ?, ?)",
                    (i+1, template['name'], template['action_type'], json.dumps(template))
                )
            
            for tactic in self.static_knowledge['recovery_tactics']:
                cursor.execute(
                    "INSERT OR REPLACE INTO fallback_tactics (id, name, knowledge_json) VALUES (?, ?, ?)",
                    (tactic['id'], tactic['name'], json.dumps(tactic))
                )
            
            conn.commit()
            conn.close()
            print(f"✅ Fallback knowledge base created: {self.fallback_db_path}")
            
        except Exception as e:
            print(f"❌ Error creating fallback knowledge base: {e}")
    
    def get_fallback_knowledge(self, knowledge_type: str) -> List[Dict[str, Any]]:
        """Get fallback knowledge when API is unavailable"""
        return self.static_knowledge.get(knowledge_type, [])
    
    def save_successful_api_response(self, endpoint: str, data: Any):
        """Cache successful API responses for future fallback"""
        try:
            cache_file = Path(f"api_cache_{endpoint.replace('/', '_')}.json")
            with open(cache_file, 'w') as f:
                json.dump({
                    'timestamp': str(datetime.now()),
                    'data': data
                }, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not cache API response: {e}")

# Create fallback knowledge base
if __name__ == "__main__":
    fallback_kb = FallbackKnowledgeBase()
    print("✅ Fallback knowledge base initialized")
