from flask import Flask, render_template, request, jsonify, Response
from prometheus_client import generate_latest
from prometheus_metrics import metrics_collector
import json
import asyncio
import threading
import sys
import os

# Import your agents
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'agents'))
from main_orchestrator import MainOrchestrator

app = Flask(__name__)

class FlaskAgentInterface:
    def __init__(self):
        self.main_orchestrator = None
        self.setup_orchestrator()
    
    def setup_orchestrator(self):
        """Initialize the main orchestrator in a separate thread"""
        def run_orchestrator():
            try:
                self.main_orchestrator = MainOrchestrator()
                asyncio.run(self.main_orchestrator.start())
            except Exception as e:
                app.logger.error(f"Error starting orchestrator: {e}")
        
        orchestrator_thread = threading.Thread(target=run_orchestrator, daemon=True)
        orchestrator_thread.start()

# Initialize interface
agent_interface = FlaskAgentInterface()

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/network-topology')
def network_topology():
    return render_template('network_topology.html')

@app.route('/approval-interface')
def approval_interface():
    return render_template('approval_interface.html')

@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint for Grafana Node Exporter dashboard"""
    return Response(
        generate_latest(metrics_collector.registry), 
        mimetype='text/plain'
    )

@app.route('/api/agent-status')
def get_agent_status():
    """Get status of all 4 agents"""
    if agent_interface.main_orchestrator:
        return jsonify({
            'monitor_agent': 'active',
            'calculation_agent': 'active', 
            'healing_agent': 'active',
            'orchestrator_agent': 'active',
            'main_orchestrator': 'active'
        })
    return jsonify({'error': 'Orchestrator not initialized'}), 500

@app.route('/api/tosca-templates')
def get_tosca_templates():
    """Get available TOSCA templates from orchestrator"""
    try:
        # This would interface with your orchestrator agent
        templates = [
            {
                'name': 'network_healing_template.tosca',
                'version': '1.0',
                'description': 'Standard network healing topology'
            },
            {
                'name': 'emergency_routing_template.tosca', 
                'version': '1.1',
                'description': 'Emergency traffic rerouting'
            }
        ]
        return jsonify(templates)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/healing-plans', methods=['POST'])
def approve_healing_plan():
    """Network operations approval for TOSCA-based healing plans"""
    try:
        data = request.json
        plan_id = data.get('plan_id')
        decision = data.get('decision')  # approve, reject, modify
        tosca_template = data.get('tosca_template')
        
        # Interface with your orchestrator agent
        result = {
            'status': 'success',
            'plan_id': plan_id,
            'decision': decision,
            'tosca_template': tosca_template,
            'timestamp': time.time()
        }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)