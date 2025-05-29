# orchestration_agent.py
import asyncio
import logging
import json
import subprocess
import os
import tempfile
import yaml
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from a2a_protocol_client import A2AProtocolClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrchestrationAgent:
    """Orchestration Agent - Execute recovery using xOpera/TOSCA"""
    
    def __init__(self, config_file: str = "orchestration_config.json"):
        self.config = self.load_configuration(config_file)
        
        # Initialize A2A communication
        self.a2a_client = A2AProtocolClient(self.config.get('a2a', {}))
        
        # xOpera configuration
        self.xopera_path = self.config.get('xopera_path', 'opera')
        self.tosca_templates_dir = self.config.get('tosca_templates_dir', './tosca_templates')
        self.workspace_dir = self.config.get('workspace_dir', './xopera_workspace')
        
        # Recovery state
        self.active_recoveries = {}
        self.is_running = False
        
        logger.info("Orchestration Agent initialized")

    def load_configuration(self, config_file: str) -> Dict[str, Any]:
        """Load configuration"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return self.get_default_config()

    def get_default_config(self) -> Dict[str, Any]:
        """Default configuration"""
        return {
            "a2a": {
                "agent_id": "orchestration_agent_001",
                "communication_port": 9005,
                "target_agents": ["monitor_agent", "healing_agent"]
            },
            "xopera_path": "opera",
            "tosca_templates_dir": "./tosca_templates",
            "workspace_dir": "./xopera_workspace"
        }

    async def start_orchestration(self):
        """Start orchestration agent"""
        logger.info("Starting Orchestration Agent...")
        self.is_running = True
        
        try:
            # Start A2A communication
            await self.a2a_client.start_communication()
            
            # Register message handlers
            self.a2a_client.register_message_handler('healing_plan', self.handle_healing_plan)
            self.a2a_client.register_message_handler('recovery_request', self.handle_recovery_request)
            
            # Setup xOpera environment
            await self.setup_xopera_environment()
            
            # Start listening for healing plans
            await self.orchestration_loop()
            
        except Exception as e:
            logger.error(f"Error starting orchestration agent: {e}")
            raise

    async def setup_xopera_environment(self):
        """Setup xOpera environment and TOSCA templates"""
        # Create workspace directory
        os.makedirs(self.workspace_dir, exist_ok=True)
        os.makedirs(self.tosca_templates_dir, exist_ok=True)
        
        # Create basic TOSCA templates for common recovery scenarios
        await self.create_tosca_templates()
        
        logger.info("xOpera environment setup complete")

    async def create_tosca_templates(self):
        """Create TOSCA templates for recovery scenarios"""
        
        # Template for fiber cut recovery
        fiber_cut_template = {
            'tosca_definitions_version': 'tosca_simple_yaml_1_3',
            'description': 'Fiber cut recovery template',
            'node_types': {
                'rural.nodes.NetworkNode': {
                    'derived_from': 'tosca.nodes.Root',
                    'properties': {
                        'node_id': {'type': 'string'},
                        'backup_routes': {'type': 'list'}
                    },
                    'interfaces': {
                        'Standard': {
                            'configure': 'scripts/activate_backup_route.sh',
                            'start': 'scripts/verify_connectivity.sh'
                        }
                    }
                }
            },
            'topology_template': {
                'node_templates': {
                    'failed_node': {
                        'type': 'rural.nodes.NetworkNode',
                        'properties': {
                            'node_id': {'get_input': 'target_node_id'},
                            'backup_routes': {'get_input': 'backup_routes'}
                        }
                    }
                },
                'inputs': {
                    'target_node_id': {'type': 'string'},
                    'backup_routes': {'type': 'list'}
                }
            }
        }
        
        # Save fiber cut template
        fiber_cut_path = os.path.join(self.tosca_templates_dir, 'fiber_cut_recovery.yaml')
        with open(fiber_cut_path, 'w') as f:
            yaml.dump(fiber_cut_template, f, default_flow_style=False)
        
        # Template for power fluctuation recovery
        power_recovery_template = {
            'tosca_definitions_version': 'tosca_simple_yaml_1_3',
            'description': 'Power fluctuation recovery template',
            'node_types': {
                'rural.nodes.PowerNode': {
                    'derived_from': 'tosca.nodes.Root',
                    'properties': {
                        'node_id': {'type': 'string'},
                        'power_mode': {'type': 'string'}
                    },
                    'interfaces': {
                        'Standard': {
                            'configure': 'scripts/activate_backup_power.sh',
                            'start': 'scripts/optimize_power_usage.sh'
                        }
                    }
                }
            },
            'topology_template': {
                'node_templates': {
                    'power_node': {
                        'type': 'rural.nodes.PowerNode',
                        'properties': {
                            'node_id': {'get_input': 'target_node_id'},
                            'power_mode': {'get_input': 'recovery_mode'}
                        }
                    }
                },
                'inputs': {
                    'target_node_id': {'type': 'string'},
                    'recovery_mode': {'type': 'string'}
                }
            }
        }
        
        # Save power recovery template
        power_recovery_path = os.path.join(self.tosca_templates_dir, 'power_recovery.yaml')
        with open(power_recovery_path, 'w') as f:
            yaml.dump(power_recovery_template, f, default_flow_style=False)
        
        # Create recovery scripts
        await self.create_recovery_scripts()
        
        logger.info("TOSCA templates created successfully")

    async def create_recovery_scripts(self):
        """Create recovery scripts for TOSCA templates"""
        scripts_dir = os.path.join(self.tosca_templates_dir, 'scripts')
        os.makedirs(scripts_dir, exist_ok=True)
        
        # Backup route activation script
        backup_route_script = """#!/bin/bash
# Activate backup route for fiber cut recovery
NODE_ID="$1"
BACKUP_ROUTES="$2"

echo "Activating backup routes for node $NODE_ID"
echo "Backup routes: $BACKUP_ROUTES"

# In real implementation, this would configure network routing
# For demo purposes, we simulate the recovery
sleep 2
echo "Backup routes activated successfully"
exit 0
"""
        
        with open(os.path.join(scripts_dir, 'activate_backup_route.sh'), 'w') as f:
            f.write(backup_route_script)
        
        # Connectivity verification script
        connectivity_script = """#!/bin/bash
# Verify connectivity after recovery
NODE_ID="$1"

echo "Verifying connectivity for node $NODE_ID"
# Simulate connectivity check
sleep 1
echo "Connectivity verified successfully"
exit 0
"""
        
        with open(os.path.join(scripts_dir, 'verify_connectivity.sh'), 'w') as f:
            f.write(connectivity_script)
        
        # Backup power activation script
        backup_power_script = """#!/bin/bash
# Activate backup power for power fluctuation recovery
NODE_ID="$1"
POWER_MODE="$2"

echo "Activating backup power for node $NODE_ID"
echo "Power mode: $POWER_MODE"

# Simulate power recovery
sleep 2
echo "Backup power activated successfully"
exit 0
"""
        
        with open(os.path.join(scripts_dir, 'activate_backup_power.sh'), 'w') as f:
            f.write(backup_power_script)
        
        # Power optimization script
        power_optimize_script = """#!/bin/bash
# Optimize power usage
NODE_ID="$1"

echo "Optimizing power usage for node $NODE_ID"
# Simulate power optimization
sleep 1
echo "Power usage optimized successfully"
exit 0
"""
        
        with open(os.path.join(scripts_dir, 'optimize_power_usage.sh'), 'w') as f:
            f.write(power_optimize_script)
        
        # Make scripts executable
        for script in ['activate_backup_route.sh', 'verify_connectivity.sh', 
                      'activate_backup_power.sh', 'optimize_power_usage.sh']:
            os.chmod(os.path.join(scripts_dir, script), 0o755)

    async def orchestration_loop(self):
        """Main orchestration loop"""
        while self.is_running:
            try:
                # Check for new healing plans from A2A
                response = await self.a2a_client.check_for_response()
                
                if response and response.get('type') == 'healing_plan':
                    await self.execute_healing_plan(response)
                
                # Check status of active recoveries
                await self.monitor_active_recoveries()
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in orchestration loop: {e}")
                await asyncio.sleep(5)

    async def handle_healing_plan(self, message: Dict[str, Any]):
        """Handle healing plan from healing agent"""
        healing_plan = message.get('data', {})
        logger.info(f"Received healing plan: {healing_plan.get('plan_id')}")
        
        await self.execute_healing_plan(healing_plan)

    async def handle_recovery_request(self, message: Dict[str, Any]):
        """Handle direct recovery request"""
        request = message.get('data', {})
        logger.info(f"Received recovery request: {request.get('request_id')}")
        
        await self.execute_recovery_request(request)

    async def execute_healing_plan(self, healing_plan: Dict[str, Any]):
        """Execute healing plan using xOpera/TOSCA"""
        plan_id = healing_plan.get('plan_id', f'plan_{int(time.time())}')
        target_nodes = healing_plan.get('target_nodes', [])
        recovery_actions = healing_plan.get('recovery_actions', [])
        
        logger.info(f"Executing healing plan {plan_id} for nodes: {target_nodes}")
        
        try:
            for action in recovery_actions:
                await self.execute_recovery_action(plan_id, action)
            
            # Mark recovery as successful
            await self.report_recovery_status(plan_id, 'SUCCESS', target_nodes)
            
        except Exception as e:
            logger.error(f"Failed to execute healing plan {plan_id}: {e}")
            await self.report_recovery_status(plan_id, 'FAILED', target_nodes, str(e))

    async def execute_recovery_action(self, plan_id: str, action: Dict[str, Any]):
        """Execute individual recovery action using xOpera"""
        action_type = action.get('type')
        node_id = action.get('node_id')
        parameters = action.get('parameters', {})
        
        logger.info(f"Executing recovery action: {action_type} on node {node_id}")
        
        # Select appropriate TOSCA template
        template_file = self.select_tosca_template(action_type)
        
        if not template_file:
            raise ValueError(f"No TOSCA template found for action type: {action_type}")
        
        # Create inputs file for xOpera
        inputs_file = await self.create_xopera_inputs(node_id, parameters)
        
        # Execute with xOpera
        await self.run_xopera_deployment(plan_id, template_file, inputs_file)

    def select_tosca_template(self, action_type: str) -> Optional[str]:
        """Select appropriate TOSCA template based on action type"""
        template_map = {
            'fiber_cut_recovery': 'fiber_cut_recovery.yaml',
            'backup_route_activation': 'fiber_cut_recovery.yaml',
            'power_recovery': 'power_recovery.yaml',
            'power_fluctuation_recovery': 'power_recovery.yaml'
        }
        
        template_name = template_map.get(action_type)
        if template_name:
            return os.path.join(self.tosca_templates_dir, template_name)
        
        return None

    async def create_xopera_inputs(self, node_id: str, parameters: Dict[str, Any]) -> str:
        """Create inputs file for xOpera deployment"""
        inputs = {
            'target_node_id': node_id,
            **parameters
        }
        
        # Create temporary inputs file
        inputs_file = os.path.join(self.workspace_dir, f'inputs_{node_id}_{int(time.time())}.yaml')
        
        with open(inputs_file, 'w') as f:
            yaml.dump(inputs, f, default_flow_style=False)
        
        return inputs_file

    async def run_xopera_deployment(self, plan_id: str, template_file: str, inputs_file: str):
        """Run xOpera deployment"""
        # Create deployment workspace
        deployment_dir = os.path.join(self.workspace_dir, f'deployment_{plan_id}')
        os.makedirs(deployment_dir, exist_ok=True)
        
        # xOpera commands
        init_cmd = [self.xopera_path, 'init', '-t', template_file, '-i', inputs_file]
        deploy_cmd = [self.xopera_path, 'deploy']
        
        try:
            # Initialize deployment
            logger.info(f"Initializing xOpera deployment: {' '.join(init_cmd)}")
            result = subprocess.run(init_cmd, cwd=deployment_dir, 
                                  capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                raise RuntimeError(f"xOpera init failed: {result.stderr}")
            
            # Execute deployment
            logger.info(f"Executing xOpera deployment: {' '.join(deploy_cmd)}")
            result = subprocess.run(deploy_cmd, cwd=deployment_dir, 
                                  capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                raise RuntimeError(f"xOpera deployment failed: {result.stderr}")
            
            logger.info(f"xOpera deployment completed successfully for plan {plan_id}")
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("xOpera deployment timed out")
        except Exception as e:
            raise RuntimeError(f"xOpera deployment error: {e}")

    async def monitor_active_recoveries(self):
        """Monitor status of active recoveries"""