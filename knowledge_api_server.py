from flask import Flask, jsonify, request
import sqlite3
import json
import os
from datetime import datetime
from contextlib import closing

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

class KnowledgeAPI:
    def __init__(self, db_path='network_knowledge.db'):
        self.db_path = db_path
        
    def get_db_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_node_types(self):
        """Get all node types with their knowledge"""
        with closing(self.get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT nt.*, 
                       GROUP_CONCAT(DISTINCT rt.tactic_name) as healing_strategies
                FROM NodeTypes nt
                LEFT JOIN RecoveryTactics rt ON rt.policy_id IN (1,2,3,4)
                GROUP BY nt.node_type_id
            """)
            
            results = cursor.fetchall()
            node_types = []
            
            for row in results:
                node_types.append({
                    'id': row['node_type_id'],
                    'name': row['type_name'],
                    'description': row['description'],
                    'typical_role': row['typical_role'],
                    'critical_metrics': ['cpu_load', 'memory_usage', 'bandwidth_util', 'latency'],
                    'common_faults': ['power_failure', 'link_failure', 'congestion', 'equipment_failure'],
                    'healing_strategies': row['healing_strategies'].split(',') if row['healing_strategies'] else []
                })
                
            return node_types
    
    def get_fault_patterns(self):
        """Get all fault patterns"""
        with closing(self.get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM FaultPatterns")
            
            results = cursor.fetchall()
            patterns = []
            
            for row in results:
                patterns.append({
                    'id': row['pattern_id'],
                    'name': row['pattern_name'],
                    'symptoms': row['symptoms'].split(',') if row['symptoms'] else [],
                    'causes': row['causes'].split(',') if row['causes'] else [],
                    'healing_actions': row['healing_actions'].split(',') if row['healing_actions'] else []
                })
                
            return patterns
    
    def get_healing_templates(self):
        """Get all healing templates"""
        with closing(self.get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM HealingTemplates")
            
            results = cursor.fetchall()
            templates = []
            
            for row in results:
                templates.append({
                    'id': row['template_id'],
                    'name': row['template_name'],
                    'action_type': row['action_type'],
                    'description': row['description'],
                    'duration': row['duration'],
                    'success_rate': row['success_rate'],
                    'prerequisites': row['prerequisites'].split(',') if row['prerequisites'] else []
                })
                
            return templates
    
    def get_recovery_tactics(self):
        """Get all recovery tactics"""
        with closing(self.get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT rt.*, p.policy_name, p.policy_category
                FROM RecoveryTactics rt
                LEFT JOIN Policies p ON rt.policy_id = p.policy_id
            """)
            
            results = cursor.fetchall()
            tactics = []
            
            for row in results:
                tactics.append({
                    'id': row['tactic_id'],
                    'name': row['tactic_name'],
                    'description': row['description'],
                    'estimated_time': row['estimated_downtime_seconds'],
                    'risk_level': row['risk_level'],
                    'is_automated': row['is_automated_capable'],
                    'priority': 'high' if row['estimated_downtime_seconds'] < 60 else 'medium' if row['estimated_downtime_seconds'] < 300 else 'low',
                    'policy': row['policy_name'] if row['policy_name'] else 'General',
                    'applicable_node_types': ['Core_Router', 'Distribution_Switch', 'Access_Point']
                })
                
            return tactics

# Initialize API
knowledge_api = KnowledgeAPI()

# API Endpoints
@app.route('/api/node-types', methods=['GET'])
def api_node_types():
    """Node types endpoint"""
    try:
        data = knowledge_api.get_node_types()
        return jsonify({
            'status': 'success',
            'count': len(data),
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/fault-patterns', methods=['GET'])
def api_fault_patterns():
    """Fault patterns endpoint"""
    try:
        data = knowledge_api.get_fault_patterns()
        return jsonify({
            'status': 'success',
            'count': len(data),
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/healing-templates', methods=['GET'])
def api_healing_templates():
    """Healing templates endpoint"""
    try:
        data = knowledge_api.get_healing_templates()
        return jsonify({
            'status': 'success',
            'count': len(data),
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/recovery-tactics', methods=['GET'])
def api_recovery_tactics():
    """Recovery tactics endpoint"""
    try:
        data = knowledge_api.get_recovery_tactics()
        return jsonify({
            'status': 'success',
            'count': len(data),
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/health', methods=['GET'])
def api_health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Nokia Rural Network Knowledge API',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/status', methods=['GET'])
def api_status():
    """Status endpoint with database statistics"""
    try:
        with closing(knowledge_api.get_db_connection()) as conn:
            cursor = conn.cursor()
            
            # Get record counts
            stats = {}
            tables = ['Nodes', 'Links', 'RecoveryTactics', 'FaultPatterns', 'HealingTemplates', 'Policies']
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table.lower()] = cursor.fetchone()[0]
        
        return jsonify({
            'status': 'operational',
            'database_stats': stats,
            'endpoints': [
                '/api/node-types',
                '/api/fault-patterns', 
                '/api/healing-templates',
                '/api/recovery-tactics'
            ],
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    print("🚀 Starting Nokia Rural Network Knowledge API Server...")
    print("📊 Available endpoints:")
    print("   - GET /api/node-types")
    print("   - GET /api/fault-patterns") 
    print("   - GET /api/healing-templates")
    print("   - GET /api/recovery-tactics")
    print("   - GET /api/health")
    print("   - GET /api/status")
    print("🔗 Server running on http://localhost:8080")
    
    app.run(host='0.0.0.0', port=8080, debug=True)
