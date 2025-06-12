import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'  # Hide GPU from TensorFlow
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'   # Reduce TensorFlow logging

import asyncio
import logging
import json
import time
import yaml
import zmq
import zmq.asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# Import your existing orchestration agent base class
try:
    from orchestration_agent import OrchestrationAgent
except ImportError:
    # Fallback base class if original doesn't exist
    class OrchestrationAgent:
        def __init__(self, *args, **kwargs):
            self.context = zmq.asyncio.Context()
            self.is_running = False
            pass

logger = logging.getLogger(__name__)

@dataclass
class ToscaTemplate:
    """TOSCA template structure"""
    template_id: str
    node_id: str
    template_name: str
    tosca_version: str
    description: str
    node_templates: Dict[str, Any]
    topology_template: Dict[str, Any]
    generated_timestamp: str
    file_path: str

@dataclass
class NS3IntegrationPlan:
    """NS3 integration plan structure"""
    plan_id: str
    healing_plan_id: str
    node_id: str
    simulation_config: Dict[str, Any]
    network_topology_changes: List[Dict[str, Any]]
    routing_updates: List[Dict[str, Any]]
    configuration_changes: List[Dict[str, Any]]
    simulation_parameters: Dict[str, Any]
    validation_criteria: Dict[str, Any]
    generated_timestamp: str
    file_path: str

@dataclass
class OrchestrationMetrics:
    """Orchestration performance metrics"""
    healing_plans_received: int = 0
    tosca_templates_generated: int = 0
    ns3_plans_exported: int = 0
    orchestration_executions: int = 0
    successful_deployments: int = 0
    failed_operations: int = 0
    avg_processing_time: float = 0.0

class EnhancedOrchestrationAgent(OrchestrationAgent):
    """Enhanced Orchestration Agent with TOSCA generation and NS3 integration"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 🔗 Communication Setup
        self.context = zmq.asyncio.Context()
        self.healing_subscriber = None    # Receive healing plans from Healing Agent
        self.status_publisher = None      # Send status updates
        
        # 📁 Directory Structure
        self.tosca_templates_dir = Path("tosca_templates")
        self.ns3_integration_dir = Path("ns3_integration")
        self.healing_plans_for_ns3_dir = Path("healing_plans_for_ns3")
        self.orchestration_reports_dir = Path("orchestration_reports")
        self.deployment_configs_dir = Path("deployment_configs")
        
        # Create directories
        for directory in [self.tosca_templates_dir, self.ns3_integration_dir, 
                         self.healing_plans_for_ns3_dir, self.orchestration_reports_dir,
                         self.deployment_configs_dir]:
            directory.mkdir(exist_ok=True)
        
        # 📊 Metrics and Tracking
        self.metrics = OrchestrationMetrics()
        self.active_orchestrations = {}
        self.processing_queue = asyncio.Queue()
        self.processing_times = []
        
        # 🎯 Nokia Rural Network Templates
        self.network_templates = self.initialize_network_templates()
        
        # 🔧 NS3 Configuration
        self.ns3_config = self.initialize_ns3_configuration()
        
        logger.info("✅ Enhanced Orchestration Agent initialized")
        logger.info(f"📁 TOSCA Templates: {self.tosca_templates_dir}")
        logger.info(f"📁 NS3 Integration: {self.ns3_integration_dir}")
        logger.info(f"📁 Healing Plans for NS3: {self.healing_plans_for_ns3_dir}")

    def initialize_network_templates(self) -> Dict[str, Any]:
        """Initialize Nokia rural network TOSCA templates"""
        return {
            'base_template': {
                'tosca_definitions_version': 'tosca_simple_yaml_1_3',
                'description': 'Nokia Rural Network Self-Healing Infrastructure',
                'metadata': {
                    'template_name': 'nokia-rural-network-healing',
                    'template_author': 'Nokia-AI-System',
                    'template_version': '2.1.0'
                },
                'imports': [
                    'tosca-normative-types:1.0',
                    'nokia-rural-network-types:2.1'
                ]
            },
            'node_type_mappings': {
                'CORE': {
                    'tosca_type': 'nokia.nodes.CoreNetworkFunction',
                    'capabilities': ['high_throughput', 'load_balancing', 'failover'],
                    'requirements': ['backup_connectivity', 'power_redundancy']
                },
                'DIST': {
                    'tosca_type': 'nokia.nodes.DistributionNode',
                    'capabilities': ['power_management', 'signal_boost', 'backup_routing'],
                    'requirements': ['stable_power', 'backup_links']
                },
                'ACC': {
                    'tosca_type': 'nokia.nodes.AccessNode',
                    'capabilities': ['resource_scaling', 'load_shedding', 'service_migration'],
                    'requirements': ['compute_resources', 'storage_capacity']
                }
            },
            'healing_action_mappings': {
                'traffic_rerouting': {
                    'tosca_policy': 'nokia.policies.TrafficRerouting',
                    'implementation': 'nokia.implementations.RoutingManager'
                },
                'power_optimization': {
                    'tosca_policy': 'nokia.policies.PowerManagement',
                    'implementation': 'nokia.implementations.PowerController'
                },
                'resource_reallocation': {
                    'tosca_policy': 'nokia.policies.ResourceManagement',
                    'implementation': 'nokia.implementations.ResourceOrchestrator'
                },
                'load_balancing': {
                    'tosca_policy': 'nokia.policies.LoadBalancing',
                    'implementation': 'nokia.implementations.LoadBalancer'
                },
                'emergency_restart': {
                    'tosca_policy': 'nokia.policies.ServiceRestart',
                    'implementation': 'nokia.implementations.ServiceManager'
                }
            }
        }

    def initialize_ns3_configuration(self) -> Dict[str, Any]:
        """Initialize NS3 simulation configuration"""
        return {
            'simulation_defaults': {
                'simulation_time': 300.0,  # 5 minutes
                'animation_enabled': True,
                'pcap_enabled': True,
                'tracing_enabled': True,
                'mobility_model': 'ns3::ConstantPositionMobilityModel',
                'propagation_model': 'ns3::FriisPropagationLossModel',
                'error_model': 'ns3::YansErrorRateModel'
            },
            'network_topology': {
                'rural_network_size': '5x5km',
                'node_density': 'sparse',
                'connectivity_pattern': 'mesh_with_backbone',
                'power_model': 'battery_with_solar'
            },
            'healing_validation': {
                'metrics_collection_interval': 1.0,
                'convergence_timeout': 60.0,
                'success_criteria': {
                    'throughput_recovery_threshold': 0.8,
                    'latency_improvement_threshold': 0.5,
                    'packet_loss_reduction_threshold': 0.3
                }
            }
        }

    async def initialize_communication(self):
        """Initialize ZeroMQ communication channels"""
        try:
            # 👂 Healing Plans Subscriber - Receive from Healing Agent
            self.healing_subscriber = self.context.socket(zmq.SUB)
            self.healing_subscriber.connect("tcp://127.0.0.1:5558")
            self.healing_subscriber.setsockopt_string(zmq.SUBSCRIBE, "")
            
            # 📤 Status Publisher - Send status updates
            self.status_publisher = self.context.socket(zmq.PUB)
            self.status_publisher.bind("tcp://127.0.0.1:5559")
            
            logger.info("✅ Enhanced Orchestration Agent communication initialized")
            logger.info("👂 Healing Plans Subscriber: Port 5558 (from Healing Agent)")
            logger.info("📤 Status Publisher: Port 5559 (status updates)")
            
            # Give time for socket binding
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"❌ Communication initialization failed: {e}")
            raise

    async def start_with_ns3_integration(self):
        """Start Enhanced Orchestration Agent with NS3 integration"""
        logger.info("🚀 Starting Enhanced Orchestration Agent...")
        
        # Initialize communication
        await self.initialize_communication()
        
        # Start processing tasks
        self.is_running = True
        
        # Create background tasks
        tasks = [
            asyncio.create_task(self.listen_for_healing_plans()),
            asyncio.create_task(self.process_orchestration_queue()),
            asyncio.create_task(self.monitor_orchestration_performance()),
            asyncio.create_task(self.generate_periodic_reports()),
            asyncio.create_task(self.cleanup_old_files())
        ]
        
        logger.info("✅ Enhanced Orchestration Agent started successfully")
        logger.info("👂 Listening for healing plans...")
        logger.info("🎯 TOSCA template generation ready...")
        logger.info("📊 NS3 integration ready...")
        
        try:
            # Wait for all tasks
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("🛑 Shutdown requested")
        finally:
            await self.cleanup()

    async def listen_for_healing_plans(self):
        """Listen for healing plans from Healing Agent"""
        logger.info("👂 Starting healing plans listener...")
        
        while self.is_running:
            try:
                # Non-blocking receive with timeout
                message = await asyncio.wait_for(
                    self.healing_subscriber.recv_json(),
                    timeout=1.0
                )
                
                if message.get('message_type') == 'healing_plan':
                    await self.handle_incoming_healing_plan(message)
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"❌ Error receiving healing plan: {e}")
                self.metrics.failed_operations += 1
                await asyncio.sleep(1)

    async def handle_incoming_healing_plan(self, plan_message: Dict[str, Any]):
        """Handle incoming healing plan with validation and queuing"""
        try:
            healing_plan_data = plan_message.get('healing_plan_data', {})
            
            if not healing_plan_data:
                logger.error("❌ Invalid healing plan received")
                return
            
            plan_id = healing_plan_data.get('plan_id', 'unknown')
            node_id = healing_plan_data.get('node_id', 'unknown')
            severity = healing_plan_data.get('severity', 'unknown')
            
            logger.info(f"🎯 Healing plan received: {plan_id}")
            logger.info(f"📍 Node: {node_id} | Severity: {severity}")
            logger.info(f"🔧 Actions: {len(healing_plan_data.get('healing_actions', []))}")
            
            self.metrics.healing_plans_received += 1
            
            # Add to processing queue
            await self.processing_queue.put(healing_plan_data)
            
        except Exception as e:
            logger.error(f"❌ Error handling healing plan: {e}")
            self.metrics.failed_operations += 1

    async def process_orchestration_queue(self):
        """Process orchestration requests from the queue"""
        logger.info("🔄 Starting orchestration queue processor...")
        
        while self.is_running:
            try:
                # Get healing plan from queue (with timeout)
                healing_plan_data = await asyncio.wait_for(
                    self.processing_queue.get(),
                    timeout=5.0
                )
                
                # Process the orchestration request
                start_time = time.time()
                await self.execute_comprehensive_orchestration(healing_plan_data)
                processing_time = time.time() - start_time
                
                # Track performance
                self.processing_times.append(processing_time)
                self.metrics.orchestration_executions += 1
                
                # Update average processing time
                self.metrics.avg_processing_time = sum(self.processing_times) / len(self.processing_times)
                
                logger.info(f"✅ Orchestration completed in {processing_time:.2f}s")
                
                # Mark task as done
                self.processing_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"❌ Error processing orchestration queue: {e}")
                self.metrics.failed_operations += 1

    async def execute_comprehensive_orchestration(self, healing_plan_data: Dict[str, Any]):
        """Execute comprehensive orchestration with TOSCA and NS3 integration"""
        try:
            plan_id = healing_plan_data.get('plan_id', 'unknown')
            node_id = healing_plan_data.get('node_id', 'unknown')
            
            logger.info(f"🎯 Executing comprehensive orchestration: {plan_id}")
            
            # 1. Generate TOSCA Template
            tosca_template = await self.generate_enhanced_tosca_template(healing_plan_data)
            
            # 2. Generate NS3 Integration Plan
            ns3_plan = await self.generate_ns3_integration_plan(healing_plan_data)
            
            # 3. Create Deployment Configuration
            deployment_config = await self.create_deployment_configuration(healing_plan_data, tosca_template)
            
            # 4. Execute Orchestration (if auto-execute enabled)
            execution_result = None
            if not healing_plan_data.get('requires_approval', False):
                execution_result = await self.execute_orchestration_deployment(
                    tosca_template, deployment_config
                )
            
            # 5. Send Status Updates
            await self.send_orchestration_status_update(
                plan_id, tosca_template, ns3_plan, execution_result
            )
            
            # 6. Generate Comprehensive Report
            await self.generate_orchestration_report(
                healing_plan_data, tosca_template, ns3_plan, execution_result
            )
            
            logger.info(f"✅ Comprehensive orchestration completed: {plan_id}")
            
        except Exception as e:
            logger.error(f"❌ Comprehensive orchestration failed: {e}")
            self.metrics.failed_operations += 1

    async def generate_enhanced_tosca_template(self, healing_plan_data: Dict[str, Any]) -> ToscaTemplate:
        """Generate enhanced TOSCA template from healing plan"""
        try:
            plan_id = healing_plan_data.get('plan_id', 'unknown')
            node_id = healing_plan_data.get('node_id', 'unknown')
            healing_actions = healing_plan_data.get('healing_actions', [])
            
            logger.info(f"📋 Generating TOSCA template for {plan_id}...")
            
            # Get node type for template selection
            node_type = self.determine_node_type(node_id)
            node_template_config = self.network_templates['node_type_mappings'].get(node_type, {})
            
            # Build TOSCA template structure
            tosca_template_data = {
                **self.network_templates['base_template'],
                'metadata': {
                    **self.network_templates['base_template']['metadata'],
                    'healing_plan_id': plan_id,
                    'target_node_id': node_id,
                    'node_type': node_type,
                    'generated_timestamp': datetime.now().isoformat()
                },
                'topology_template': {
                    'description': f'Self-healing orchestration for {node_id}',
                    'node_templates': self.build_node_templates(node_id, node_type, healing_actions),
                    'policies': self.build_healing_policies(healing_actions),
                    'workflows': self.build_healing_workflows(healing_actions)
                }
            }
            
            # Generate unique template filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            template_filename = f"healing_tosca_{node_id}_{timestamp}.yaml"
            template_path = self.tosca_templates_dir / template_filename
            
            # Save TOSCA template to file
            with open(template_path, 'w') as f:
                yaml.dump(tosca_template_data, f, default_flow_style=False, indent=2)
            
            # Create ToscaTemplate object
            tosca_template = ToscaTemplate(
                template_id=f"TOSCA_{plan_id}_{int(time.time())}",
                node_id=node_id,
                template_name=template_filename,
                tosca_version=tosca_template_data['tosca_definitions_version'],
                description=tosca_template_data['topology_template']['description'],
                node_templates=tosca_template_data['topology_template']['node_templates'],
                topology_template=tosca_template_data['topology_template'],
                generated_timestamp=datetime.now().isoformat(),
                file_path=str(template_path)
            )
            
            self.metrics.tosca_templates_generated += 1
            logger.info(f"✅ TOSCA template generated: {template_path}")
            
            return tosca_template
            
        except Exception as e:
            logger.error(f"❌ Error generating TOSCA template: {e}")
            raise

    def determine_node_type(self, node_id: str) -> str:
        """Determine node type from node ID"""
        try:
            node_num = int(node_id.split('_')[1])
            if node_num in [0, 1]:
                return "CORE"
            elif node_num in [5, 7]:
                return "DIST"
            elif node_num in [20, 25]:
                return "ACC"
            else:
                return "GENERIC"
        except:
            return "GENERIC"

    def build_node_templates(self, node_id: str, node_type: str, healing_actions: List[Dict]) -> Dict[str, Any]:
        """Build TOSCA node templates"""
        node_config = self.network_templates['node_type_mappings'].get(node_type, {})
        
        node_templates = {
            f"{node_id.replace('_', '-')}-healing": {
                'type': node_config.get('tosca_type', 'nokia.nodes.GenericNode'),
                'properties': {
                    'node_id': node_id,
                    'node_type': node_type,
                    'healing_enabled': True,
                    'monitoring_interval': 10,
                    'health_check_timeout': 30
                },
                'capabilities': {
                    cap: {'enabled': True} for cap in node_config.get('capabilities', [])
                },
                'requirements': [
                    {'dependency': f"{node_id.replace('_', '-')}-monitor"}
                ],
                'interfaces': {
                    'Nokia.Healing': {
                        'operations': {
                            action['action_type']: {
                                'implementation': self.network_templates['healing_action_mappings']
                                .get(action['action_type'], {})
                                .get('implementation', 'nokia.implementations.GenericAction'),
                                'inputs': action.get('parameters', {})
                            }
                            for action in healing_actions
                        }
                    }
                }
            },
            f"{node_id.replace('_', '-')}-monitor": {
                'type': 'nokia.nodes.MonitoringService',
                'properties': {
                    'target_node': node_id,
                    'metrics_collection': True,
                    'alerting_enabled': True,
                    'retention_period': '7d'
                }
            }
        }
        
        return node_templates

    def build_healing_policies(self, healing_actions: List[Dict]) -> List[Dict[str, Any]]:
        """Build TOSCA healing policies"""
        policies = []
        
        for i, action in enumerate(healing_actions):
            action_type = action.get('action_type', 'generic_action')
            policy_config = self.network_templates['healing_action_mappings'].get(action_type, {})
            
            policy = {
                f"healing-policy-{i+1}": {
                    'type': policy_config.get('tosca_policy', 'nokia.policies.GenericHealing'),
                    'description': action.get('description', 'Healing action policy'),
                    'properties': {
                        'priority': action.get('priority', 3),
                        'estimated_duration': action.get('estimated_duration', 60),
                        'success_probability': action.get('success_probability', 0.8),
                        'rollback_enabled': True,
                        'approval_required': action.get('priority', 3) <= 1
                    },
                    'targets': [action.get('target_node', 'all_nodes')]
                }
            }
            policies.append(policy)
        
        return policies

    def build_healing_workflows(self, healing_actions: List[Dict]) -> Dict[str, Any]:
        """Build TOSCA healing workflows"""
        workflow_steps = []
        
        for i, action in enumerate(healing_actions):
            step = {
                f"step_{i+1}_{action.get('action_type', 'action')}": {
                    'target': f"healing-policy-{i+1}",
                    'activities': [
                        {
                            'set_state': 'executing'
                        },
                        {
                            'call_operation': {
                                'operation': f"Nokia.Healing.{action.get('action_type', 'generic_action')}",
                                'inputs': action.get('parameters', {})
                            }
                        },
                        {
                            'set_state': 'completed'
                        }
                    ],
                    'on_success': f"step_{i+2}" if i < len(healing_actions) - 1 else 'workflow_complete',
                    'on_failure': 'rollback_workflow'
                }
            }
            workflow_steps.append(step)
        
        workflows = {
            'healing_workflow': {
                'description': 'Automated healing workflow execution',
                'steps': {step_name: step_config for step_dict in workflow_steps for step_name, step_config in step_dict.items()},
                'inputs': {
                    'healing_plan_id': {
                        'type': 'string',
                        'description': 'ID of the healing plan being executed'
                    }
                },
                'outputs': {
                    'execution_status': {
                        'type': 'string',
                        'description': 'Overall execution status'
                    },
                    'execution_report': {
                        'type': 'string',
                        'description': 'Detailed execution report'
                    }
                }
            }
        }
        
        return workflows

    async def generate_ns3_integration_plan(self, healing_plan_data: Dict[str, Any]) -> NS3IntegrationPlan:
        """Generate NS3-compatible integration plan"""
        try:
            plan_id = healing_plan_data.get('plan_id', 'unknown')
            node_id = healing_plan_data.get('node_id', 'unknown')
            healing_actions = healing_plan_data.get('healing_actions', [])
            
            logger.info(f"📊 Generating NS3 integration plan for {plan_id}...")
            
            # Build NS3 simulation configuration
            simulation_config = {
                **self.ns3_config['simulation_defaults'],
                'healing_scenario': {
                    'target_node': node_id,
                    'fault_injection_time': 60.0,
                    'healing_start_time': 120.0,
                    'validation_duration': 180.0
                }
            }
            
            # Generate network topology changes
            topology_changes = self.generate_ns3_topology_changes(node_id, healing_actions)
            
            # Generate routing updates
            routing_updates = self.generate_ns3_routing_updates(node_id, healing_actions)
            
            # Generate configuration changes
            config_changes = self.generate_ns3_config_changes(node_id, healing_actions)
            
            # Generate simulation parameters
            sim_parameters = self.generate_ns3_simulation_parameters(healing_plan_data)
            
            # Generate validation criteria
            validation_criteria = self.generate_ns3_validation_criteria(healing_actions)
            
            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            ns3_filename = f"ns3_healing_plan_{node_id}_{timestamp}.json"
            ns3_path = self.healing_plans_for_ns3_dir / ns3_filename
            
            # Create NS3IntegrationPlan object
            ns3_plan = NS3IntegrationPlan(
                plan_id=f"NS3_{plan_id}_{int(time.time())}",
                healing_plan_id=plan_id,
                node_id=node_id,
                simulation_config=simulation_config,
                network_topology_changes=topology_changes,
                routing_updates=routing_updates,
                configuration_changes=config_changes,
                simulation_parameters=sim_parameters,
                validation_criteria=validation_criteria,
                generated_timestamp=datetime.now().isoformat(),
                file_path=str(ns3_path)
            )
            
            # Build complete NS3 integration JSON
            ns3_integration_data = {
                'ns3_integration_metadata': {
                    'plan_id': ns3_plan.plan_id,
                    'healing_plan_id': plan_id,
                    'target_node': node_id,
                    'generated_timestamp': ns3_plan.generated_timestamp,
                    'orchestrator_version': 'Nokia-Rural-Network-v2.1.0',
                    'ns3_compatibility_version': '3.35+',
                    'export_format': 'healing_commands_json'
                },
                'simulation_configuration': simulation_config,
                'network_topology_changes': topology_changes,
                'routing_updates': routing_updates,
                'configuration_changes': config_changes,
                'simulation_parameters': sim_parameters,
                'validation_criteria': validation_criteria,
                'original_healing_plan': healing_plan_data,
                'ns3_execution_commands': self.generate_ns3_execution_commands(ns3_filename)
            }
            
            # Save NS3 integration plan to file
            with open(ns3_path, 'w') as f:
                json.dump(ns3_integration_data, f, indent=2, default=str)
            
            self.metrics.ns3_plans_exported += 1
            logger.info(f"✅ NS3 integration plan generated: {ns3_path}")
            
            return ns3_plan
            
        except Exception as e:
            logger.error(f"❌ Error generating NS3 integration plan: {e}")
            raise

    def generate_ns3_topology_changes(self, node_id: str, healing_actions: List[Dict]) -> List[Dict[str, Any]]:
        """Generate NS3 topology modification commands"""
        topology_changes = []
        
        for action in healing_actions:
            action_type = action.get('action_type', '')
            
            if action_type == 'traffic_rerouting':
                topology_changes.append({
                    'command': 'modify_routing_table',
                    'target_node': node_id,
                    'action': 'activate_backup_path',
                    'parameters': {
                        'backup_path_priority': 1,
                        'reroute_percentage': action.get('parameters', {}).get('reroute_percentage', 50),
                        'convergence_time': 30.0
                    },
                    'validation': {
                        'expected_throughput_recovery': 0.8,
                        'max_convergence_time': 60.0
                    }
                })
                
            elif action_type == 'load_balancing':
                topology_changes.append({
                    'command': 'enable_load_balancing',
                    'target_node': node_id,
                    'action': 'distribute_traffic',
                    'parameters': {
                        'balancing_algorithm': action.get('parameters', {}).get('balancing_algorithm', 'round_robin'),
                        'load_threshold': action.get('parameters', {}).get('load_threshold', 0.8),
                        'rebalancing_interval': 10.0
                    },
                    'validation': {
                        'load_distribution_variance': 0.2,
                        'throughput_improvement': 0.3
                    }
                })
        
        return topology_changes

    def generate_ns3_routing_updates(self, node_id: str, healing_actions: List[Dict]) -> List[Dict[str, Any]]:
        """Generate NS3 routing protocol updates"""
        routing_updates = []
        
        node_type = self.determine_node_type(node_id)
        
        for action in healing_actions:
            if action.get('action_type') in ['traffic_rerouting', 'load_balancing']:
                
                # Dynamic routing protocol updates
                routing_updates.append({
                    'protocol': 'OLSR',  # OLSR for rural mesh networks
                    'target_node': node_id,
                    'update_type': 'emergency_reroute',
                    'parameters': {
                        'hello_interval': 0.5,  # Faster neighbor detection
                        'tc_interval': 1.0,     # Faster topology updates
                        'neighbor_hold_time': 10.0,
                        'mpr_coverage': 2,      # Redundant multipoint relays
                        'link_quality_threshold': 0.3
                    },
                    'affected_neighbors': self.get_node_neighbors(node_id),
                    'convergence_timeout': 30.0
                })
                
                # Static route backup injection
                routing_updates.append({
                    'protocol': 'STATIC',
                    'target_node': node_id,
                    'update_type': 'backup_route_injection',
                    'parameters': {
                        'backup_routes': self.generate_backup_routes(node_id, node_type),
                        'route_priority': 10,   # Lower priority than dynamic routes
                        'metric_adjustment': 100
                    }
                })
        
        return routing_updates

    def generate_ns3_config_changes(self, node_id: str, healing_actions: List[Dict]) -> List[Dict[str, Any]]:
        """Generate NS3 configuration changes"""
        config_changes = []
        
        for action in healing_actions:
            action_type = action.get('action_type', '')
            
            if action_type == 'power_optimization':
                config_changes.append({
                    'config_type': 'energy_model',
                    'target_node': node_id,
                    'parameters': {
                        'tx_power_dbm': 25,  # Increase transmission power
                        'energy_source': 'backup_battery',
                        'power_management_mode': 'emergency',
                        'sleep_mode_disabled': True,
                        'energy_harvesting': 'solar_boost'
                    },
                    'validation': {
                        'signal_strength_improvement': 3.0,  # dB
                        'coverage_area_expansion': 1.2
                    }
                })
                
            elif action_type == 'resource_reallocation':
                config_changes.append({
                    'config_type': 'resource_allocation',
                    'target_node': node_id,
                    'parameters': {
                        'cpu_allocation_increase': action.get('parameters', {}).get('cpu_limit_increase', 20),
                        'memory_pool_expansion': True,
                        'buffer_size_multiplier': 1.5,
                        'queue_management': 'priority_based',
                        'congestion_control': 'enhanced'
                    },
                    'validation': {
                        'processing_capacity_improvement': 0.25,
                        'queue_length_reduction': 0.4
                    }
                })
                
            elif action_type == 'emergency_restart':
                config_changes.append({
                    'config_type': 'service_management',
                    'target_node': node_id,
                    'parameters': {
                        'restart_sequence': 'graceful_with_state_preservation',
                        'service_migration_enabled': True,
                        'connection_preservation': True,
                        'restart_timeout': 60.0,
                        'health_check_frequency': 5.0
                    },
                    'validation': {
                        'service_downtime': 'max_30_seconds',
                        'connection_recovery_rate': 0.95
                    }
                })
        
        return config_changes

    def generate_ns3_simulation_parameters(self, healing_plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate NS3 simulation parameters"""
        severity = healing_plan_data.get('severity', 'medium')
        
        # Adjust simulation parameters based on severity
        simulation_time = 600.0 if severity == 'critical' else 300.0
        
        return {
            'simulation_time': simulation_time,
            'healing_validation_interval': 10.0,
            'fault_injection': {
                'enabled': True,
                'fault_type': 'progressive_degradation',
                'severity_level': severity,
                'injection_time': 60.0,
                'duration': 120.0
            },
            'metrics_collection': {
                'throughput': {'enabled': True, 'interval': 1.0},
                'latency': {'enabled': True, 'interval': 1.0},
                'packet_loss': {'enabled': True, 'interval': 1.0},
                'energy_consumption': {'enabled': True, 'interval': 5.0},
                'routing_convergence': {'enabled': True, 'interval': 1.0},
                'link_quality': {'enabled': True, 'interval': 2.0}
            },
            'output_configuration': {
                'animation_file': f"healing_animation_{healing_plan_data.get('node_id', 'unknown')}.xml",
                'pcap_enabled': True,
                'ascii_trace_enabled': True,
                'flow_monitor_enabled': True,
                'results_directory': f"results/healing_{healing_plan_data.get('plan_id', 'unknown')}"
            }
        }

    def generate_ns3_validation_criteria(self, healing_actions: List[Dict]) -> Dict[str, Any]:
        """Generate NS3 validation criteria"""
        return {
            'healing_success_criteria': {
                'throughput_recovery_threshold': 0.8,
                'latency_improvement_threshold': 0.5,
                'packet_loss_reduction_threshold': 0.7,
                'energy_efficiency_maintenance': 0.9,
                'convergence_time_limit': 60.0
            },
            'performance_benchmarks': {
                'baseline_throughput': 'measured_before_fault',
                'acceptable_latency_increase': 0.2,
                'maximum_packet_loss': 0.05,
                'energy_consumption_limit': 1.1  # 10% increase allowed
            },
            'validation_timeline': {
                'immediate_response': '0-30s',
                'short_term_recovery': '30s-2min',
                'long_term_stability': '2min-5min',
                'performance_verification': '5min-10min'
            },
            'failure_conditions': {
                'healing_timeout': 300.0,
                'consecutive_failures': 3,
                'performance_degradation_threshold': 0.5,
                'network_partition_detection': True
            }
        }

    def get_node_neighbors(self, node_id: str) -> List[str]:
        """Get neighboring nodes for routing updates"""
        # This would typically query the actual network topology
        # For now, provide realistic neighbor sets based on node type
        node_num = int(node_id.split('_')[1])
        
        if node_num in [0, 1]:  # CORE nodes
            return [f"node_{i:02d}" for i in [2, 3, 4, 5, 6, 7]]
        elif node_num in [5, 7]:  # DIST nodes  
            return [f"node_{i:02d}" for i in [0, 1, 8, 9, 10, 20, 21, 22]]
        elif node_num in [20, 25]:  # ACC nodes
            return [f"node_{i:02d}" for i in [5, 7, 18, 19, 23, 24, 26, 27]]
        else:
            return []

    def generate_backup_routes(self, node_id: str, node_type: str) -> List[Dict[str, Any]]:
        """Generate backup routes for the node"""
        backup_routes = []
        
        if node_type == 'CORE':
            backup_routes = [
                {
                    'destination': '0.0.0.0/0',  # Default route
                    'next_hop': 'backup_core_node',
                    'metric': 150,
                    'interface': 'backup_interface'
                }
            ]
        elif node_type == 'DIST':
            backup_routes = [
                {
                    'destination': 'core_network/16',
                    'next_hop': 'alternate_dist_node',
                    'metric': 120,
                    'interface': 'wireless_backup'
                }
            ]
        elif node_type == 'ACC':
            backup_routes = [
                {
                    'destination': 'distribution_network/24',
                    'next_hop': 'neighbor_acc_node',
                    'metric': 100,
                    'interface': 'mesh_backup'
                }
            ]
        
        return backup_routes

    def generate_ns3_execution_commands(self, ns3_filename: str) -> List[str]:
        """Generate NS3 execution commands"""
        return [
            f"# Load healing plan in NS3 simulation:",
            f"# 1. Copy {ns3_filename} to ns3/src/rural-network/examples/",
            f"# 2. Run: ./waf --run 'rural-network-healing --healing-plan={ns3_filename}'",
            f"# 3. Monitor results in ns3/results/healing_validation/",
            f"# 4. Generate reports: python3 scripts/analyze_healing_results.py",
            f"# 5. Visualization: python3 scripts/visualize_healing_performance.py"
        ]

    async def create_deployment_configuration(self, healing_plan_data: Dict[str, Any], tosca_template: ToscaTemplate) -> Dict[str, Any]:
        """Create deployment configuration"""
        try:
            deployment_config = {
                'deployment_metadata': {
                    'deployment_id': f"DEPLOY_{healing_plan_data.get('plan_id', 'unknown')}_{int(time.time())}",
                    'tosca_template_path': tosca_template.file_path,
                    'target_environment': 'nokia_rural_network',
                    'deployment_type': 'healing_orchestration',
                    'created_timestamp': datetime.now().isoformat()
                },
                'orchestrator_config': {
                    'orchestrator_type': 'nokia_orchestrator',
                    'api_endpoint': 'https://orchestrator.nokia.rural/api/v2',
                    'authentication': {
                        'type': 'service_account',
                        'credentials_path': 'config/orchestrator_credentials.json'
                    },
                    'timeout_settings': {
                        'deployment_timeout': 600,
                        'health_check_timeout': 120,
                        'rollback_timeout': 300
                    }
                },
                'deployment_parameters': {
                    'auto_approve': not healing_plan_data.get('requires_approval', False),
                    'rollback_on_failure': True,
                    'dry_run': False,
                    'validate_before_deploy': True,
                    'notification_endpoints': [
                        'healing-agent@nokia.rural',
                        'orchestration-alerts@nokia.rural'
                    ]
                },
                'resource_requirements': {
                    'compute_resources': self.calculate_compute_requirements(healing_plan_data),
                    'network_resources': self.calculate_network_requirements(healing_plan_data),
                    'storage_resources': self.calculate_storage_requirements(healing_plan_data)
                }
            }
            
            # Save deployment configuration
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            config_filename = f"deployment_config_{healing_plan_data.get('node_id', 'unknown')}_{timestamp}.json"
            config_path = self.deployment_configs_dir / config_filename
            
            with open(config_path, 'w') as f:
                json.dump(deployment_config, f, indent=2, default=str)
            
            logger.info(f"✅ Deployment configuration created: {config_path}")
            
            return deployment_config
            
        except Exception as e:
            logger.error(f"❌ Error creating deployment configuration: {e}")
            raise

    def calculate_compute_requirements(self, healing_plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate compute resource requirements"""
        healing_actions = healing_plan_data.get('healing_actions', [])
        severity = healing_plan_data.get('severity', 'medium')
        
        base_cpu = 0.5  # Base CPU cores
        base_memory = 1024  # Base memory in MB
        
        # Adjust based on number of healing actions
        cpu_per_action = 0.2
        memory_per_action = 256
        
        # Severity multiplier
        severity_multiplier = {'low': 1.0, 'medium': 1.2, 'high': 1.5, 'critical': 2.0}.get(severity, 1.0)
        
        return {
            'cpu_cores': (base_cpu + len(healing_actions) * cpu_per_action) * severity_multiplier,
            'memory_mb': int((base_memory + len(healing_actions) * memory_per_action) * severity_multiplier),
            'disk_space_mb': 100,  # Log storage
            'network_bandwidth_mbps': 10 * severity_multiplier
        }

    def calculate_network_requirements(self, healing_plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate network resource requirements"""
        return {
            'bandwidth_requirements': {
                'control_plane': '1Mbps',
                'data_plane': '10Mbps',
                'monitoring': '0.5Mbps'
            },
            'connectivity_requirements': [
                'management_network_access',
                'node_control_interface',
                'monitoring_system_connection'
            ],
            'security_requirements': [
                'encrypted_communication',
                'certificate_based_auth',
                'firewall_rules_update'
            ]
        }

    def calculate_storage_requirements(self, healing_plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate storage resource requirements"""
        return {
            'configuration_storage': '50MB',
            'log_storage': '200MB',
            'backup_storage': '100MB',
            'temporary_storage': '50MB',
            'retention_policy': '7_days'
        }

    async def execute_orchestration_deployment(self, tosca_template: ToscaTemplate, deployment_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute orchestration deployment (simulation)"""
        try:
            logger.info(f"🚀 Executing orchestration deployment: {tosca_template.template_id}")
            
            # Simulate deployment execution
            execution_start = time.time()
            
            # Phase 1: Validation
            await asyncio.sleep(2)  # Simulate validation time
            logger.info("✅ Phase 1: Template validation completed")
            
            # Phase 2: Resource preparation
            await asyncio.sleep(3)  # Simulate resource preparation
            logger.info("✅ Phase 2: Resource preparation completed")
            
            # Phase 3: Deployment execution
            await asyncio.sleep(5)  # Simulate deployment execution
            logger.info("✅ Phase 3: Deployment execution completed")
            
            # Phase 4: Health checks
            await asyncio.sleep(2)  # Simulate health checks
            logger.info("✅ Phase 4: Health checks completed")
            
            execution_duration = time.time() - execution_start
            
            execution_result = {
                'execution_id': f"EXEC_{int(time.time())}",
                'status': 'success',
                'execution_duration': execution_duration,
                'phases_completed': ['validation', 'resource_preparation', 'deployment', 'health_checks'],
                'deployed_components': list(tosca_template.node_templates.keys()),
                'deployment_summary': {
                    'total_nodes_affected': 1,
                    'total_services_deployed': len(tosca_template.node_templates),
                    'successful_deployments': len(tosca_template.node_templates),
                    'failed_deployments': 0
                },
                'resource_usage': {
                    'cpu_utilization': '45%',
                    'memory_utilization': '60%',
                    'network_utilization': '25%'
                },
                'completion_timestamp': datetime.now().isoformat()
            }
            
            self.metrics.successful_deployments += 1
            logger.info(f"✅ Orchestration deployment completed in {execution_duration:.2f}s")
            
            return execution_result
            
        except Exception as e:
            logger.error(f"❌ Orchestration deployment failed: {e}")
            self.metrics.failed_operations += 1
            
            return {
                'execution_id': f"EXEC_FAILED_{int(time.time())}",
                'status': 'failed',
                'error': str(e),
                'failure_timestamp': datetime.now().isoformat()
            }

    async def send_orchestration_status_update(self, plan_id: str, tosca_template: ToscaTemplate, 
                                             ns3_plan: NS3IntegrationPlan, execution_result: Optional[Dict[str, Any]]):
        """Send orchestration status update"""
        try:
            status_update = {
                'message_type': 'orchestration_status',
                'timestamp': datetime.now().isoformat(),
                'source_agent': 'orchestration_agent',
                'plan_id': plan_id,
                'orchestration_summary': {
                    'tosca_template_generated': True,
                    'tosca_template_path': tosca_template.file_path,
                    'ns3_plan_generated': True,
                    'ns3_plan_path': ns3_plan.file_path,
                    'deployment_executed': execution_result is not None,
                    'deployment_status': execution_result.get('status', 'not_executed') if execution_result else 'not_executed'
                },
                'performance_metrics': {
                    'total_processing_time': self.metrics.avg_processing_time,
                    'tosca_templates_generated': self.metrics.tosca_templates_generated,
                    'ns3_plans_exported': self.metrics.ns3_plans_exported,
                    'successful_deployments': self.metrics.successful_deployments
                }
            }
            
            await self.status_publisher.send_json(status_update)
            logger.info(f"📤 Orchestration status update sent for {plan_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to send orchestration status update: {e}")

    async def generate_orchestration_report(self, healing_plan_data: Dict[str, Any], tosca_template: ToscaTemplate,
                                          ns3_plan: NS3IntegrationPlan, execution_result: Optional[Dict[str, Any]]):
        """Generate comprehensive orchestration report"""
        try:
            report = {
                'report_metadata': {
                    'report_id': f"ORCH_REPORT_{int(time.time())}",
                    'generated_timestamp': datetime.now().isoformat(),
                    'healing_plan_id': healing_plan_data.get('plan_id', 'unknown'),
                    'node_id': healing_plan_data.get('node_id', 'unknown')
                },
                'healing_plan_summary': {
                    'node_id': healing_plan_data.get('node_id', 'unknown'),
                    'severity': healing_plan_data.get('severity', 'unknown'),
                    'total_healing_actions': len(healing_plan_data.get('healing_actions', [])),
                    'estimated_duration': healing_plan_data.get('total_estimated_duration', 0),
                    'confidence': healing_plan_data.get('confidence', 0.0)
                },
                'tosca_template_details': {
                    'template_id': tosca_template.template_id,
                    'template_path': tosca_template.file_path,
                    'node_templates_count': len(tosca_template.node_templates),
                    'generated_timestamp': tosca_template.generated_timestamp
                },
                'ns3_integration_details': {
                    'plan_id': ns3_plan.plan_id,
                    'integration_path': ns3_plan.file_path,
                    'topology_changes': len(ns3_plan.network_topology_changes),
                    'routing_updates': len(ns3_plan.routing_updates),
                    'config_changes': len(ns3_plan.configuration_changes),
                    'generated_timestamp': ns3_plan.generated_timestamp
                },
                'deployment_details': execution_result if execution_result else {'status': 'not_executed'},
                'orchestration_metrics': asdict(self.metrics),
                'files_generated': {
                    'tosca_template': tosca_template.file_path,
                    'ns3_integration_plan': ns3_plan.file_path,
                    'deployment_config': f"deployment_configs/deployment_config_{healing_plan_data.get('node_id', 'unknown')}_*.json"
                },
                'next_steps': [
                    f"Execute NS3 simulation using: {ns3_plan.file_path}",
                    f"Deploy TOSCA template using: {tosca_template.file_path}",
                    "Monitor healing effectiveness through NS3 simulation results",
                    "Validate healing success criteria",
                    "Generate post-healing performance report"
                ]
            }
            
            # Save report
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_filename = f"orchestration_report_{healing_plan_data.get('node_id', 'unknown')}_{timestamp}.json"
            report_path = self.orchestration_reports_dir / report_filename
            
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"📋 Orchestration report generated: {report_path}")
            
        except Exception as e:
            logger.error(f"❌ Error generating orchestration report: {e}")

    async def monitor_orchestration_performance(self):
        """Monitor orchestration performance metrics"""
        logger.info("📊 Starting orchestration performance monitoring...")
        
        while self.is_running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Log performance summary
                logger.info(f"📊 Orchestration Performance Summary:")
                logger.info(f"   • Healing Plans Received: {self.metrics.healing_plans_received}")
                logger.info(f"   • TOSCA Templates Generated: {self.metrics.tosca_templates_generated}")
                logger.info(f"   • NS3 Plans Exported: {self.metrics.ns3_plans_exported}")
                logger.info(f"   • Orchestration Executions: {self.metrics.orchestration_executions}")
                logger.info(f"   • Successful Deployments: {self.metrics.successful_deployments}")
                logger.info(f"   • Failed Operations: {self.metrics.failed_operations}")
                logger.info(f"   • Avg Processing Time: {self.metrics.avg_processing_time:.2f}s")
                logger.info(f"   • Active Orchestrations: {len(self.active_orchestrations)}")
                
                # Clean up old processing times (keep last 100)
                if len(self.processing_times) > 100:
                    self.processing_times = self.processing_times[-100:]
                
            except Exception as e:
                logger.error(f"❌ Error in orchestration performance monitoring: {e}")

    async def generate_periodic_reports(self):
        """Generate periodic orchestration reports"""
        logger.info("📋 Starting periodic orchestration report generation...")
        
        while self.is_running:
            try:
                await asyncio.sleep(3600)  # Generate report every hour
                
                periodic_report = {
                    'report_timestamp': datetime.now().isoformat(),
                    'reporting_period': '1 hour',
                    'orchestration_metrics': asdict(self.metrics),
                    'performance_summary': {
                        'avg_processing_time': self.metrics.avg_processing_time,
                        'success_rate': (
                            (self.metrics.successful_deployments / 
                             max(self.metrics.orchestration_executions, 1)) * 100
                        ),
                        'throughput_per_hour': self.metrics.orchestration_executions,
                        'error_rate': (
                            (self.metrics.failed_operations / 
                             max(self.metrics.orchestration_executions, 1)) * 100
                        )
                    },
                    'file_generation_summary': {
                        'tosca_templates_generated': self.metrics.tosca_templates_generated,
                        'ns3_plans_exported': self.metrics.ns3_plans_exported,
                        'total_files_created': (
                            self.metrics.tosca_templates_generated + 
                            self.metrics.ns3_plans_exported
                        )
                    }
                }
                
                # Save periodic report
                report_file = self.orchestration_reports_dir / f"periodic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(report_file, 'w') as f:
                    json.dump(periodic_report, f, indent=2, default=str)
                
                logger.info(f"📋 Periodic orchestration report generated: {report_file}")
                
            except Exception as e:
                logger.error(f"❌ Error generating periodic orchestration report: {e}")

    async def cleanup_old_files(self):
        """Cleanup old files periodically"""
        logger.info("🧹 Starting periodic file cleanup...")
        
        while self.is_running:
            try:
                await asyncio.sleep(86400)  # Cleanup daily
                
                # Cleanup files older than 7 days
                cutoff_time = time.time() - (7 * 24 * 3600)  # 7 days ago
                
                directories_to_clean = [
                    self.tosca_templates_dir,
                    self.healing_plans_for_ns3_dir,
                    self.orchestration_reports_dir,
                    self.deployment_configs_dir
                ]
                
                files_cleaned = 0
                for directory in directories_to_clean:
                    for file_path in directory.glob('*'):
                        if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                            file_path.unlink()
                            files_cleaned += 1
                
                logger.info(f"🧹 Cleaned up {files_cleaned} old files")
                
            except Exception as e:
                logger.error(f"❌ Error in file cleanup: {e}")

    async def cleanup(self):
        """Cleanup resources and connections"""
        try:
            self.is_running = False
            
            # Close ZeroMQ sockets
            if self.healing_subscriber:
                self.healing_subscriber.close()
            if self.status_publisher:
                self.status_publisher.close()
            if self.context:
                self.context.term()
            
            # Generate final orchestration report
            final_report = {
                'shutdown_timestamp': datetime.now().isoformat(),
                'final_metrics': asdict(self.metrics),
                'total_active_orchestrations': len(self.active_orchestrations),
                'avg_processing_time': self.metrics.avg_processing_time,
                'total_files_generated': (
                    self.metrics.tosca_templates_generated + 
                    self.metrics.ns3_plans_exported
                )
            }
            
            final_report_file = self.orchestration_reports_dir / f"final_orchestration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(final_report_file, 'w') as f:
                json.dump(final_report, f, indent=2, default=str)
            
            logger.info("✅ Enhanced Orchestration Agent cleanup completed")
            logger.info(f"📋 Final report saved: {final_report_file}")
            
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")

# Main execution function
async def main():
    """Main execution function for Enhanced Orchestration Agent"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize agent
    agent = EnhancedOrchestrationAgent()
    
    try:
        print('🎯 Enhanced Orchestration Agent starting...')
        print('👂 Listening for healing plans from Healing Agent')
        print('📋 Ready to generate TOSCA templates')
        print('📊 Ready to export NS3 integration plans')
        print('🚀 Ready to execute orchestration deployments')
        print(f'📁 TOSCA Templates: {agent.tosca_templates_dir}')
        print(f'📁 NS3 Integration: {agent.healing_plans_for_ns3_dir}')
        print(f'📊 Reports: {agent.orchestration_reports_dir}')
        
        await agent.start_with_ns3_integration()
        
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown requested")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
    finally:
        await agent.cleanup()

if __name__ == '__main__':
    asyncio.run(main())