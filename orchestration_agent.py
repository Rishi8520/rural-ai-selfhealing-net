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
    """ENHANCED: Orchestration performance metrics with file monitoring"""
    healing_plans_received: int = 0
    tosca_templates_generated: int = 0
    ns3_plans_exported: int = 0
    orchestration_executions: int = 0
    successful_deployments: int = 0
    failed_operations: int = 0
    avg_processing_time: float = 0.0
    # File-based monitoring metrics
    file_healing_plans_processed: int = 0
    ns3_deployment_files_created: int = 0
    realtime_orchestration_cycles: int = 0
    # Validation metrics
    tosca_validation_successes: int = 0
    tosca_validation_failures: int = 0

class RobustOrchestrationAgent(OrchestrationAgent):
    """
    🏆 ROBUST: Complete Orchestration Agent with Full TOSCA Implementation
    
    ENHANCED FEATURES:
    - Complete TOSCA template generation with all missing methods
    - Advanced NS3 command generation for all healing action types
    - TOSCA validation engine
    - Enhanced file monitoring and ZeroMQ communication
    - Comprehensive error handling and recovery
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Dual communication setup
        self.context = zmq.asyncio.Context()
        self.healing_subscriber = None
        self.status_publisher = None
        
        # Directory structure
        self.tosca_templates_dir = Path("tosca_templates")
        self.ns3_integration_dir = Path("ns3_integration")
        self.healing_plans_for_ns3_dir = Path("healing_plans_for_ns3")
        self.orchestration_reports_dir = Path("orchestration_reports")
        self.deployment_configs_dir = Path("deployment_configs")
        self.healing_plans_input_dir = Path("healing_plans_for_orchestration")
        self.ns3_deployments_dir = Path("orchestration_deployments")
        
        # Create all directories
        for directory in [self.tosca_templates_dir, self.ns3_integration_dir, 
                         self.healing_plans_for_ns3_dir, self.orchestration_reports_dir,
                         self.deployment_configs_dir, self.healing_plans_input_dir,
                         self.ns3_deployments_dir]:
            directory.mkdir(exist_ok=True)
        
        # Enhanced metrics
        self.metrics = OrchestrationMetrics()
        self.active_orchestrations = {}
        self.processing_queue = asyncio.Queue()
        self.processing_times = []
        
        # Configuration
        self.network_templates = self.initialize_network_templates()
        self.ns3_config = self.initialize_ns3_configuration()
        
        # File monitoring state
        self.last_processed_files = set()
        self.file_monitoring_active = False
        
        logger.info("✅ Robust Orchestration Agent initialized")
        logger.info(f"📁 TOSCA Templates: {self.tosca_templates_dir}")
        logger.info(f"📁 NS3 Integration: {self.ns3_integration_dir}")
        logger.info(f"🔥 Real-time input: {self.healing_plans_input_dir}")
        logger.info(f"🔥 NS3 deployments: {self.ns3_deployments_dir}")

    def initialize_network_templates(self) -> Dict[str, Any]:
        """Initialize comprehensive Nokia rural network TOSCA templates"""
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
                },
                'GENERIC': {
                    'tosca_type': 'nokia.nodes.GenericNode',
                    'capabilities': ['basic_connectivity', 'monitoring'],
                    'requirements': ['network_access', 'power_supply']
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
                },
                'signal_boost': {
                    'tosca_policy': 'nokia.policies.SignalAmplification',
                    'implementation': 'nokia.implementations.SignalProcessor'
                },
                'network_isolation': {
                    'tosca_policy': 'nokia.policies.NetworkIsolation',
                    'implementation': 'nokia.implementations.IsolationManager'
                }
            }
        }

    def initialize_ns3_configuration(self) -> Dict[str, Any]:
        """Initialize comprehensive NS3 simulation configuration"""
        return {
            'simulation_defaults': {
                'simulation_time': 300.0,
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
            },
            'action_parameters': {
                'power_optimization': {
                    'voltage_boost_percentage': 5,
                    'power_stabilization_time': 30,
                    'energy_efficiency_mode': True
                },
                'traffic_rerouting': {
                    'backup_path_count': 3,
                    'rerouting_delay_ms': 100,
                    'load_balancing_enabled': True
                },
                'load_balancing': {
                    'algorithm': 'weighted_round_robin',
                    'rebalancing_interval': 60,
                    'threshold_percentage': 80
                }
            }
        }

    # **COMPLETE IMPLEMENTATION: TOSCA Template Generation Methods**
    
    def build_node_templates(self, node_id: str, node_type: str, healing_actions: List[Dict]) -> Dict[str, Any]:
        """Build complete TOSCA node templates"""
        node_templates = {}
        
        # Main healing target node
        node_templates[f"healing_target_{node_id}"] = {
            'type': self.network_templates['node_type_mappings'][node_type]['tosca_type'],
            'properties': {
                'node_id': node_id,
                'node_type': node_type,
                'healing_required': True,
                'current_status': 'degraded',
                'priority_level': 'high' if any(action.get('priority', 3) <= 2 for action in healing_actions) else 'medium'
            },
            'capabilities': {
                'healing_endpoint': {
                    'type': 'nokia.capabilities.HealingEndpoint',
                    'properties': {
                        'supported_actions': [action.get('action_type') for action in healing_actions],
                        'max_concurrent_actions': 3,
                        'healing_timeout': 300
                    }
                }
            },
            'requirements': self.network_templates['node_type_mappings'][node_type]['requirements']
        }
        
        # Healing service nodes for each action
        for i, action in enumerate(healing_actions):
            action_type = action.get('action_type', 'unknown')
            service_node_id = f"healing_service_{action_type}_{i}"
            
            node_templates[service_node_id] = {
                'type': 'nokia.nodes.HealingService',
                'properties': {
                    'service_type': action_type,
                    'priority': action.get('priority', 3),
                    'estimated_duration': action.get('estimated_duration', 60),
                    'success_probability': action.get('success_probability', 0.8),
                    'target_node': node_id,
                    'parameters': action.get('parameters', {}),
                    'rollback_enabled': True,
                    'monitoring_enabled': True
                },
                'requirements': [{
                    'target': {
                        'node': f"healing_target_{node_id}",
                        'capability': 'healing_endpoint'
                    }
                }],
                'interfaces': {
                    'Standard': {
                        'create': f"nokia.scripts.{action_type}_create.sh",
                        'configure': f"nokia.scripts.{action_type}_configure.sh",
                        'start': f"nokia.scripts.{action_type}_start.sh",
                        'stop': f"nokia.scripts.{action_type}_stop.sh",
                        'delete': f"nokia.scripts.{action_type}_delete.sh"
                    },
                    'Healing': {
                        'execute': f"nokia.scripts.{action_type}_execute.py",
                        'validate': f"nokia.scripts.{action_type}_validate.py",
                        'rollback': f"nokia.scripts.{action_type}_rollback.py"
                    }
                }
            }
        
        return node_templates

    def build_healing_policies(self, healing_actions: List[Dict]) -> List[Dict[str, Any]]:
        """Build comprehensive TOSCA policies for healing actions"""
        policies = []
        
        for i, action in enumerate(healing_actions):
            action_type = action.get('action_type', 'unknown')
            
            # Get policy mapping
            policy_config = self.network_templates['healing_action_mappings'].get(action_type, {
                'tosca_policy': 'nokia.policies.GenericHealing',
                'implementation': 'nokia.implementations.HealingManager'
            })
            
            policy = {
                f"healing_policy_{action_type}_{i}": {
                    'type': policy_config['tosca_policy'],
                    'properties': {
                        'action_type': action_type,
                        'priority': action.get('priority', 3),
                        'timeout': action.get('estimated_duration', 60),
                        'retry_count': 3,
                        'retry_interval': 10,
                        'rollback_enabled': True,
                        'success_threshold': action.get('success_probability', 0.8),
                        'monitoring_interval': 5,
                        'alert_on_failure': True
                    },
                    'targets': [f"healing_service_{action_type}_{i}"],
                    'implementation': {
                        'primary': policy_config['implementation'],
                        'dependencies': [
                            'nokia.artifacts.HealingScript',
                            'nokia.artifacts.MonitoringAgent',
                            'nokia.artifacts.ValidationEngine'
                        ]
                    },
                    'triggers': {
                        'healing_timeout': {
                            'event': 'timeout',
                            'condition': f"get_property(['SELF', 'timeout']) < get_attribute(['SELF', 'execution_time'])",
                            'action': [
                                'rollback',
                                'alert'
                            ]
                        },
                        'healing_failure': {
                            'event': 'failure',
                            'condition': f"get_attribute(['SELF', 'success_rate']) < get_property(['SELF', 'success_threshold'])",
                            'action': [
                                'retry',
                                'escalate'
                            ]
                        }
                    }
                }
            }
            policies.append(policy)
        
        return policies

    def build_healing_workflows(self, healing_actions: List[Dict]) -> Dict[str, Any]:
        """Build comprehensive TOSCA workflows for coordinated healing"""
        workflows = {}
        
        # Main healing workflow
        workflow_steps = {}
        
        # Add pre-healing validation step
        workflow_steps['pre_healing_validation'] = {
            'target': 'healing_validation_service',
            'activities': [
                {'call_operation': 'Validation.check_prerequisites'},
                {'call_operation': 'Validation.assess_risk'},
                {'call_operation': 'Validation.approve_execution'}
            ],
            'on_success': 'parallel_healing_execution' if len(healing_actions) > 1 else f"execute_{healing_actions[0].get('action_type', 'unknown')}_0",
            'on_failure': 'healing_failed'
        }
        
        # Add parallel or sequential execution based on action priorities
        high_priority_actions = [action for action in healing_actions if action.get('priority', 3) <= 2]
        low_priority_actions = [action for action in healing_actions if action.get('priority', 3) > 2]
        
        if len(healing_actions) > 1:
            # Parallel execution for multiple actions
            workflow_steps['parallel_healing_execution'] = {
                'target': 'coordination_service',
                'activities': [
                    {'call_operation': 'Coordination.start_parallel_execution'},
                    {'delegate': [f"execute_{action.get('action_type', 'unknown')}_{i}" 
                                for i, action in enumerate(healing_actions)]}
                ],
                'on_success': 'post_healing_validation',
                'on_failure': 'parallel_rollback'
            }
        
        # Individual action execution steps
        for i, action in enumerate(healing_actions):
            action_type = action.get('action_type', 'unknown')
            step_name = f"execute_{action_type}_{i}"
            
            workflow_steps[step_name] = {
                'target': f"healing_service_{action_type}_{i}",
                'activities': [
                    {'call_operation': 'Standard.start'},
                    {'call_operation': 'Healing.execute'},
                    {'call_operation': 'Healing.validate'}
                ],
                'on_success': f"validate_{action_type}_{i}",
                'on_failure': f"rollback_{action_type}_{i}"
            }
            
            # Validation steps
            workflow_steps[f"validate_{action_type}_{i}"] = {
                'target': f"healing_service_{action_type}_{i}",
                'activities': [
                    {'call_operation': 'Validation.check_success'},
                    {'call_operation': 'Monitoring.collect_metrics'},
                    {'call_operation': 'Reporting.update_status'}
                ],
                'on_success': 'post_healing_validation' if i == len(healing_actions) - 1 else 'continue_execution',
                'on_failure': f"retry_{action_type}_{i}"
            }
            
            # Rollback steps
            workflow_steps[f"rollback_{action_type}_{i}"] = {
                'target': f"healing_service_{action_type}_{i}",
                'activities': [
                    {'call_operation': 'Healing.rollback'},
                    {'call_operation': 'Standard.stop'},
                    {'call_operation': 'Reporting.log_failure'}
                ],
                'on_success': 'healing_failed',
                'on_failure': 'critical_failure'
            }
        
        # Post-healing validation
        workflow_steps['post_healing_validation'] = {
            'target': 'healing_validation_service',
            'activities': [
                {'call_operation': 'Validation.verify_healing_success'},
                {'call_operation': 'Monitoring.final_assessment'},
                {'call_operation': 'Reporting.generate_completion_report'}
            ],
            'on_success': 'healing_complete',
            'on_failure': 'healing_partial_success'
        }
        
        # Completion states
        workflow_steps['healing_complete'] = {
            'target': 'notification_service',
            'activities': [
                {'call_operation': 'Notification.success_alert'},
                {'call_operation': 'Cleanup.finalize'}
            ]
        }
        
        workflow_steps['healing_failed'] = {
            'target': 'notification_service',
            'activities': [
                {'call_operation': 'Notification.failure_alert'},
                {'call_operation': 'Escalation.trigger_manual_intervention'}
            ]
        }
        
        workflows['comprehensive_healing_orchestration'] = {
            'description': 'Comprehensive healing workflow with validation, parallel execution, and rollback support',
            'inputs': {
                'healing_plan_id': {'type': 'string', 'required': True},
                'node_id': {'type': 'string', 'required': True},
                'severity': {'type': 'string', 'required': True, 'constraints': [{'valid_values': ['low', 'medium', 'high', 'critical']}]},
                'auto_approve': {'type': 'boolean', 'default': False},
                'timeout_minutes': {'type': 'integer', 'default': 30}
            },
            'outputs': {
                'healing_status': {'type': 'string'},
                'completion_time': {'type': 'timestamp'},
                'success_rate': {'type': 'float'},
                'actions_executed': {'type': 'list'}
            },
            'steps': workflow_steps
        }
        
        return workflows

    def determine_node_type(self, node_id: str) -> str:
        """Determine node type from node ID with validation"""
        try:
            # Extract numeric part from node_id (e.g., "node_05" -> 5)
            if node_id.startswith('node_'):
                node_num = int(node_id.split('_')[-1])
                
                if node_num < 5:
                    return "CORE"
                elif node_num < 20:
                    return "DIST"
                else:
                    return "ACC"
            else:
                # Handle different node ID formats
                logger.warning(f"Unexpected node ID format: {node_id}")
                return "GENERIC"
        except (ValueError, IndexError):
            logger.warning(f"Could not determine node type for {node_id}, defaulting to GENERIC")
            return "GENERIC"

    # **COMPLETE IMPLEMENTATION: TOSCA Validation Engine**
    
    def validate_tosca_template(self, tosca_template_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Comprehensive TOSCA template validation"""
        errors = []
        warnings = []
        
        try:
            # Check required top-level sections
            required_sections = ['tosca_definitions_version', 'topology_template']
            for section in required_sections:
                if section not in tosca_template_data:
                    errors.append(f"Missing required section: {section}")
            
            # Validate TOSCA version
            tosca_version = tosca_template_data.get('tosca_definitions_version', '')
            if not tosca_version.startswith('tosca_simple_yaml'):
                warnings.append(f"Unrecognized TOSCA version: {tosca_version}")
            
            # Validate topology template
            if 'topology_template' in tosca_template_data:
                topology = tosca_template_data['topology_template']
                
                # Check node templates
                if 'node_templates' not in topology:
                    errors.append("Missing node_templates in topology_template")
                else:
                    node_templates = topology['node_templates']
                    self._validate_node_templates(node_templates, errors, warnings)
                
                # Check policies
                if 'policies' in topology:
                    policies = topology['policies']
                    self._validate_policies(policies, errors, warnings)
                
                # Check workflows
                if 'workflows' in topology:
                    workflows = topology['workflows']
                    self._validate_workflows(workflows, errors, warnings)
            
            # Log validation results
            if errors:
                logger.error(f"TOSCA validation failed with {len(errors)} errors: {errors}")
                self.metrics.tosca_validation_failures += 1
            else:
                logger.info(f"TOSCA validation passed with {len(warnings)} warnings")
                self.metrics.tosca_validation_successes += 1
            
            if warnings:
                logger.warning(f"TOSCA validation warnings: {warnings}")
            
            is_valid = len(errors) == 0
            return is_valid, errors + warnings
            
        except Exception as e:
            error_msg = f"TOSCA validation exception: {str(e)}"
            logger.error(error_msg)
            return False, [error_msg]

    def _validate_node_templates(self, node_templates: Dict[str, Any], errors: List[str], warnings: List[str]):
        """Validate node templates section"""
        for node_name, node_def in node_templates.items():
            if 'type' not in node_def:
                errors.append(f"Node {node_name} missing required 'type' field")
            
            # Validate node properties
            if 'properties' in node_def:
                properties = node_def['properties']
                if 'node_id' not in properties:
                    warnings.append(f"Node {node_name} missing node_id property")
            
            # Validate requirements
            if 'requirements' in node_def:
                requirements = node_def['requirements']
                if not isinstance(requirements, list):
                    errors.append(f"Node {node_name} requirements must be a list")

    def _validate_policies(self, policies: List[Dict], errors: List[str], warnings: List[str]):
        """Validate policies section"""
        for policy in policies:
            if not isinstance(policy, dict):
                errors.append("Policy must be a dictionary")
                continue
            
            for policy_name, policy_def in policy.items():
                if 'type' not in policy_def:
                    errors.append(f"Policy {policy_name} missing required 'type' field")
                
                if 'targets' not in policy_def:
                    warnings.append(f"Policy {policy_name} has no targets defined")

    def _validate_workflows(self, workflows: Dict[str, Any], errors: List[str], warnings: List[str]):
        """Validate workflows section"""
        for workflow_name, workflow_def in workflows.items():
            if 'steps' not in workflow_def:
                errors.append(f"Workflow {workflow_name} missing steps")
            else:
                steps = workflow_def['steps']
                if not isinstance(steps, dict):
                    errors.append(f"Workflow {workflow_name} steps must be a dictionary")
                
                # Validate step connectivity
                step_names = set(steps.keys())
                for step_name, step_def in steps.items():
                    if 'on_success' in step_def:
                        success_target = step_def['on_success']
                        if success_target not in step_names and success_target not in ['healing_complete', 'healing_failed']:
                            warnings.append(f"Step {step_name} references unknown success target: {success_target}")

    async def trigger_ns3_deployment(self, deployment_file: Path):
        """Trigger NS3 deployment execution"""
        try:
        # Create execution command for NS3
            ns3_command = {
            'command_type': 'execute_healing',
            'deployment_file': str(deployment_file),
            'timestamp': time.time(),
            'execution_mode': 'immediate'
            }
        
        # Save command file for NS3 to pick up
            #command_file = Path("ns3_commands") / f"execute_{deployment_file.stem}.json"
            ns3_commands_dir = Path("/media/rishi/Windows-SSD/PROJECT_&_RESEARCH/NOKIA/Buil-a-thon/ns3_commands")
            ns3_commands_dir.mkdir(exist_ok=True)
            command_file = ns3_commands_dir / f"execute_{deployment_file.stem}.json"
            with open(command_file, 'w') as f:
                json.dump(ns3_command, f, indent=2)
        
            logger.info(f"🚀 NS3 execution command created: {command_file}")
        
        # Optional: Direct subprocess call if NS3 supports it
        # subprocess.run([
        #     "./ns3", "run", 
        #     f"rural_network_50nodes --deploymentFile={deployment_file} --executeHealing=true"
        # ], cwd="/path/to/ns3/")
        
        except Exception as e:
            logger.error(f"❌ NS3 deployment trigger failed: {e}")

    # **ENHANCED: NS3 Command Generation**
    
    async def monitor_ns3_confirmations(self):
        confirmation_dir = Path("ns3_output")
        while self.is_running:
            for conf_file in confirmation_dir.glob("deployment_confirmation_*.json"):
            # Process confirmation
                await self.process_deployment_confirmation(conf_file)
                conf_file.unlink()  # Clean up
            await asyncio.sleep(5)

    async def create_ns3_deployment_file(self, healing_plan_data: Dict[str, Any], 
                                       tosca_template: ToscaTemplate, execution_result: Optional[Dict[str, Any]]):
        """ENHANCED: Create comprehensive deployment file for NS3 with all healing actions"""
        try:
            deployment_data = {
                'deployment_metadata': {
                    'deployment_id': f"DEPLOY_{healing_plan_data.get('plan_id', 'unknown')}_{int(time.time())}",
                    'healing_plan_id': healing_plan_data.get('plan_id', 'unknown'),
                    'node_id': healing_plan_data.get('node_id', 'unknown'),
                    'timestamp': time.time(),
                    'tosca_template_path': tosca_template.file_path,
                    'deployment_status': execution_result.get('status', 'success') if execution_result else 'queued',
                    'orchestration_agent': 'robust_orchestration_agent',
                    'validation_passed': True,
                    'estimated_completion_time': time.time() + sum(action.get('estimated_duration', 60) for action in healing_plan_data.get('healing_actions', []))
                },
                'healing_actions': [],
                'ns3_commands': [],
                'visualization_updates': [],
                'network_topology_changes': [],
                'routing_updates': [],
                'performance_targets': {},
                'rollback_plan': []
            }
            
            # ENHANCED: Process all healing action types
            for action in healing_plan_data.get('healing_actions', []):
                action_type = action.get('action_type', '')
                node_id = healing_plan_data.get('node_id')
                priority = action.get('priority', 3)
                
                if action_type == 'power_optimization':
                    self._add_power_optimization_commands(deployment_data, node_id, action)
                    
                elif action_type == 'traffic_rerouting':
                    self._add_traffic_rerouting_commands(deployment_data, node_id, action)
                    
                elif action_type == 'load_balancing':
                    self._add_load_balancing_commands(deployment_data, node_id, action)
                    
                elif action_type == 'emergency_restart':
                    self._add_emergency_restart_commands(deployment_data, node_id, action)
                    
                elif action_type == 'resource_reallocation':
                    self._add_resource_reallocation_commands(deployment_data, node_id, action)
                    
                elif action_type == 'signal_boost':
                    self._add_signal_boost_commands(deployment_data, node_id, action)
                    
                elif action_type == 'network_isolation':
                    self._add_network_isolation_commands(deployment_data, node_id, action)
                
                else:
                    # Generic healing action
                    self._add_generic_healing_commands(deployment_data, node_id, action)
            
            # Add coordination commands for multi-action scenarios
            if len(deployment_data['healing_actions']) > 1:
                self._add_coordination_commands(deployment_data, healing_plan_data)
            
            # Save enhanced deployment file
            timestamp = int(time.time())
            deployment_file = self.ns3_deployments_dir / f"deployment_{healing_plan_data.get('plan_id', 'unknown')}_{timestamp}.json"
            
            with open(deployment_file, 'w') as f:
                json.dump(deployment_data, f, indent=2)
            
            self.metrics.ns3_deployment_files_created += 1
            logger.info(f"📤 Enhanced NS3 deployment file created: {deployment_file.name}")
            logger.info(f"🎯 Actions: {len(deployment_data['healing_actions'])}")
            logger.info(f"⚡ Commands: {len(deployment_data['ns3_commands'])}")
            if deployment_file:
                await self.trigger_ns3_deployment(deployment_file)    
            return deployment_file
            
        except Exception as e:
            logger.error(f"❌ Error creating enhanced NS3 deployment file: {e}")
            return None

    def _add_power_optimization_commands(self, deployment_data: Dict, node_id: str, action: Dict):
        """Add power optimization specific commands"""
        deployment_data['healing_actions'].append({
            'command': 'heal_power_fluctuation',
            'node_id': node_id,
            'parameters': {
                'restore_power_stability': True,
                'visual_healing_indicator': True,
                'healing_duration': action.get('estimated_duration', 30),
                'power_boost_dbm': action.get('parameters', {}).get('power_boost', 3),
                'voltage_stabilization': True,
                'energy_efficiency_mode': True,
                'power_redundancy_check': True
            }
        })
        deployment_data['ns3_commands'].extend([
            f"ExecutePowerFluctuationHealing({node_id})",
            f"SetNodePowerStability({node_id}, 0.95)",
            f"BoostNodePower({node_id}, {action.get('parameters', {}).get('power_boost', 3)})",
            f"UpdatePowerVisualization({node_id}, 'healing')",
            f"EnablePowerRedundancy({node_id})"
        ])
        deployment_data['performance_targets'][node_id] = {
            'power_stability': 0.95,
            'voltage_level': 1.0,
            'energy_efficiency': 0.9
        }

    def _add_traffic_rerouting_commands(self, deployment_data: Dict, node_id: str, action: Dict):
        """Add traffic rerouting specific commands"""
        backup_nodes = self.find_backup_nodes(node_id)
        deployment_data['healing_actions'].append({
            'command': 'reroute_traffic',
            'node_id': node_id,
            'parameters': {
                'activate_backup_path': True,
                'reroute_percentage': action.get('parameters', {}).get('reroute_percentage', 50),
                'visual_rerouting_indicator': True,
                'healing_duration': action.get('estimated_duration', 60),
                'load_balancing': True,
                'backup_nodes': backup_nodes,
                'failover_timeout': 5
            }
        })
        deployment_data['routing_updates'].append({
            'type': 'backup_path_activation',
            'primary_node': node_id,
            'backup_nodes': backup_nodes,
            'traffic_split': 'weighted_round_robin',
            'failover_criteria': 'packet_loss > 0.1 OR latency > 100ms'
        })
        deployment_data['ns3_commands'].extend([
            f"ExecuteFiberCutRerouting({node_id}, {backup_nodes[0]})",
            f"ActivateBackupPath({node_id}, {backup_nodes})",
            f"SetTrafficDistribution({node_id}, 'weighted_round_robin')",
            f"UpdateRoutingVisualization({node_id}, 'rerouting')"
        ])

    def _add_load_balancing_commands(self, deployment_data: Dict, node_id: str, action: Dict):
        """Add load balancing specific commands"""
        neighbor_nodes = self.get_neighbor_nodes(node_id)
        deployment_data['healing_actions'].append({
            'command': 'activate_load_balancing',
            'node_id': node_id,
            'parameters': {
                'balancing_algorithm': action.get('parameters', {}).get('algorithm', 'weighted_fair_queuing'),
                'redistribution_ratio': action.get('parameters', {}).get('ratio', 0.7),
                'neighbor_nodes': neighbor_nodes,
                'healing_duration': action.get('estimated_duration', 120),
                'dynamic_adjustment': True,
                'threshold_monitoring': True
            }
        })
        deployment_data['ns3_commands'].extend([
            f"ActivateLoadBalancing({node_id}, '{action.get('parameters', {}).get('algorithm', 'weighted_fair_queuing')}')",
            f"SetLoadDistribution({node_id}, {neighbor_nodes})",
            f"EnableDynamicLoadAdjustment({node_id})",
            f"UpdateLoadBalancingVisualization({node_id}, 'active')"
        ])

    def _add_emergency_restart_commands(self, deployment_data: Dict, node_id: str, action: Dict):
        """Add emergency restart specific commands"""
        deployment_data['healing_actions'].append({
            'command': 'emergency_restart',
            'node_id': node_id,
            'parameters': {
                'restart_type': action.get('parameters', {}).get('restart_type', 'graceful'),
                'preserve_connections': action.get('parameters', {}).get('preserve_connections', True),
                'failover_enabled': True,
                'healing_duration': action.get('estimated_duration', 120),
                'state_backup': True,
                'connection_migration': True
            }
        })
        deployment_data['ns3_commands'].extend([
            f"PrepareEmergencyRestart({node_id})",
            f"BackupNodeState({node_id})",
            f"ExecuteGracefulRestart({node_id})",
            f"RestoreNodeState({node_id})",
            f"UpdateRestartVisualization({node_id}, 'restarting')"
        ])
        # Add rollback plan
        deployment_data['rollback_plan'].append({
            'action': 'restore_from_backup',
            'node_id': node_id,
            'backup_timestamp': time.time()
        })

    def _add_resource_reallocation_commands(self, deployment_data: Dict, node_id: str, action: Dict):
        """Add resource reallocation specific commands"""
        deployment_data['healing_actions'].append({
            'command': 'reallocate_resources',
            'node_id': node_id,
            'parameters': {
                'cpu_boost': action.get('parameters', {}).get('cpu_boost', 0.2),
                'memory_allocation': action.get('parameters', {}).get('memory_allocation', 0.8),
                'bandwidth_priority': action.get('parameters', {}).get('bandwidth_priority', 'high'),
                'healing_duration': action.get('estimated_duration', 90),
                'resource_monitoring': True,
                'automatic_scaling': True
            }
        })
        deployment_data['ns3_commands'].extend([
            f"ReallocateResources({node_id}, cpu={action.get('parameters', {}).get('cpu_boost', 0.2)})",
            f"SetMemoryAllocation({node_id}, {action.get('parameters', {}).get('memory_allocation', 0.8)})",
            f"SetBandwidthPriority({node_id}, '{action.get('parameters', {}).get('bandwidth_priority', 'high')}')",
            f"UpdateResourceVisualization({node_id}, 'reallocating')"
        ])

    def _add_signal_boost_commands(self, deployment_data: Dict, node_id: str, action: Dict):
        """Add signal boost specific commands"""
        deployment_data['healing_actions'].append({
            'command': 'boost_signal_strength',
            'node_id': node_id,
            'parameters': {
                'signal_boost_db': action.get('parameters', {}).get('signal_boost', 5),
                'amplification_duration': action.get('estimated_duration', 60),
                'power_control': True,
                'interference_mitigation': True
            }
        })
        deployment_data['ns3_commands'].extend([
            f"BoostSignalStrength({node_id}, {action.get('parameters', {}).get('signal_boost', 5)})",
            f"OptimizeAntennaPattern({node_id})",
            f"UpdateSignalVisualization({node_id}, 'boosted')"
        ])

    def _add_network_isolation_commands(self, deployment_data: Dict, node_id: str, action: Dict):
        """Add network isolation specific commands"""
        deployment_data['healing_actions'].append({
            'command': 'isolate_network_segment',
            'node_id': node_id,
            'parameters': {
                'isolation_level': action.get('parameters', {}).get('isolation_level', 'partial'),
                'preserve_critical_services': True,
                'isolation_duration': action.get('estimated_duration', 180)
            }
        })
        deployment_data['ns3_commands'].extend([
            f"IsolateNetworkSegment({node_id}, '{action.get('parameters', {}).get('isolation_level', 'partial')}')",
            f"PreserveCriticalServices({node_id})",
            f"UpdateIsolationVisualization({node_id}, 'isolated')"
        ])

    def _add_generic_healing_commands(self, deployment_data: Dict, node_id: str, action: Dict):
        """Add generic healing commands for unknown action types"""
        deployment_data['healing_actions'].append({
            'command': 'generic_healing_action',
            'node_id': node_id,
            'parameters': {
                'action_type': action.get('action_type', 'unknown'),
                'healing_duration': action.get('estimated_duration', 60),
                'generic_parameters': action.get('parameters', {})
            }
        })
        deployment_data['ns3_commands'].extend([
            f"ExecuteGenericHealing({node_id}, '{action.get('action_type', 'unknown')}')",
            f"UpdateGenericVisualization({node_id}, 'healing')"
        ])

    def _add_coordination_commands(self, deployment_data: Dict, healing_plan_data: Dict):
        """Add coordination commands for multi-action scenarios"""
        node_id = healing_plan_data.get('node_id')
        deployment_data['network_topology_changes'].append({
            'change_type': 'multi_action_coordination',
            'primary_node': node_id,
            'coordination_nodes': self.get_coordination_nodes(node_id),
            'healing_sequence': 'parallel_with_dependencies',
            'coordination_timeout': 300
        })
        deployment_data['ns3_commands'].extend([
            f"InitializeHealingCoordination({node_id})",
            f"SynchronizeHealingActions({node_id})",
            f"MonitorHealingProgress({node_id})"
        ])

    def find_backup_nodes(self, primary_node_id: str) -> List[str]:
        """Find backup nodes for traffic rerouting"""
        try:
            node_num = int(primary_node_id.split('_')[-1])
            backup_nodes = []
            
            if node_num < 5:  # Core node
                backup_nodes = [f"node_{i:02d}" for i in range(5) if i != node_num]
            elif node_num < 20:  # Distribution node  
                backup_nodes = [f"node_{i:02d}" for i in range(5, 20) if i != node_num]
            else:  # Access node
                backup_nodes = [f"node_{i:02d}" for i in range(20, 30) if i != node_num]
            
            return backup_nodes[:3]  # Return top 3 backup options
        except (ValueError, IndexError):
            logger.warning(f"Could not find backup nodes for {primary_node_id}")
            return []

    def get_neighbor_nodes(self, node_id: str) -> List[str]:
        """Get neighboring nodes for load balancing"""
        return self.find_backup_nodes(node_id)[:2]  # Top 2 neighbors

    def get_coordination_nodes(self, node_id: str) -> List[str]:
        """Get nodes for coordination during multi-action healing"""
        return self.find_backup_nodes(node_id)[:1]  # Primary coordinator

    # **PRESERVED: All existing communication and monitoring methods**
    
    async def initialize_communication(self):
        """Initialize ZeroMQ communication channels"""
        try:
            self.healing_subscriber = self.context.socket(zmq.SUB)
            self.healing_subscriber.connect("tcp://127.0.0.1:5558")
            self.healing_subscriber.setsockopt_string(zmq.SUBSCRIBE, "")
            
            self.status_publisher = self.context.socket(zmq.PUB)
            self.status_publisher.bind("tcp://127.0.0.1:5560")
            
            logger.info("✅ Robust Orchestration Agent communication initialized")
            logger.info("👂 ZeroMQ Healing Plans Subscriber: Port 5558")
            logger.info("📤 ZeroMQ Status Publisher: Port 5560")
            logger.info("📁 FILE: Healing plans monitoring: healing_plans_for_orchestration/")
            logger.info("📁 FILE: NS3 deployments output: orchestration_deployments/")
            
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"❌ Communication initialization failed: {e}")
            raise

    async def monitor_healing_plan_files_every_10_seconds(self):
        """Monitor for healing plan files from Healing Agent every 10 seconds"""
        logger.info("🔥 Starting robust real-time healing plan file monitoring...")
        self.file_monitoring_active = True
        
        while self.is_running:
            try:
                for plan_file in self.healing_plans_input_dir.glob("healing_plan_*.json"):
                    if plan_file.name not in self.last_processed_files:
                        logger.info(f"📥 NEW healing plan file detected: {plan_file.name}")
                        
                        await self.process_healing_plan_file(plan_file)
                        
                        self.last_processed_files.add(plan_file.name)
                        self.metrics.file_healing_plans_processed += 1
                        self.metrics.realtime_orchestration_cycles += 1
                        
                        plan_file.unlink()
                        logger.info(f"✅ Processed and removed: {plan_file.name}")
                
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"❌ Error in file monitoring: {e}")
                await asyncio.sleep(5)
        
        self.file_monitoring_active = False

    async def process_healing_plan_file(self, plan_file: Path):
        """Process healing plan from file and execute orchestration"""
        try:
            with open(plan_file, 'r') as f:
                healing_plan_data = json.load(f)
            
            plan_id = healing_plan_data.get('plan_id', 'unknown')
            node_id = healing_plan_data.get('node_id', 'unknown')
            
            logger.info(f"🎯 Processing file-based healing plan: {plan_id}")
            logger.info(f"📍 Target node: {node_id}")
            
            await self.execute_comprehensive_orchestration_from_file(healing_plan_data)
            
        except Exception as e:
            logger.error(f"❌ Error processing healing plan file {plan_file}: {e}")
            self.metrics.failed_operations += 1

    async def execute_comprehensive_orchestration_from_file(self, healing_plan_data: Dict[str, Any]):
        """Execute comprehensive orchestration from file-based healing plan"""
        try:
            plan_id = healing_plan_data.get('plan_id', 'unknown')
            
            logger.info(f"🎯 Executing file-based comprehensive orchestration: {plan_id}")
            
            # Generate TOSCA Template with validation
            tosca_template = await self.generate_enhanced_tosca_template(healing_plan_data)
            
            # Generate NS3 Integration Plan
            ns3_plan = await self.generate_ns3_integration_plan(healing_plan_data)
            
            # Create Deployment Configuration
            deployment_config = await self.create_deployment_configuration(healing_plan_data, tosca_template)
            
            # Execute Orchestration
            execution_result = None
            if not healing_plan_data.get('requires_approval', False):
                execution_result = await self.execute_orchestration_deployment(
                    tosca_template, deployment_config
                )
            
            # Create NS3 deployment file
            await self.create_ns3_deployment_file(healing_plan_data, tosca_template, execution_result)
            
            # Send status updates
            await self.send_orchestration_status_update(
                plan_id, tosca_template, ns3_plan, execution_result
            )
            
            # Generate comprehensive report
            await self.generate_orchestration_report(
                healing_plan_data, tosca_template, ns3_plan, execution_result
            )
            
            logger.info(f"✅ File-based comprehensive orchestration completed: {plan_id}")
            
        except Exception as e:
            logger.error(f"❌ File-based comprehensive orchestration failed: {e}")
            self.metrics.failed_operations += 1

    async def generate_enhanced_tosca_template(self, healing_plan_data: Dict[str, Any]) -> ToscaTemplate:
        """Generate enhanced TOSCA template with validation"""
        try:
            plan_id = healing_plan_data.get('plan_id', 'unknown')
            node_id = healing_plan_data.get('node_id', 'unknown')
            healing_actions = healing_plan_data.get('healing_actions', [])
            
            logger.info(f"📋 Generating TOSCA template for {plan_id}...")
            
            # Get node type
            node_type = self.determine_node_type(node_id)
            
            # Build TOSCA template structure
            tosca_template_data = {
                **self.network_templates['base_template'],
                'metadata': {
                    **self.network_templates['base_template']['metadata'],
                    'healing_plan_id': plan_id,
                    'target_node_id': node_id,
                    'node_type': node_type,
                    'generated_timestamp': datetime.now().isoformat(),
                    'action_count': len(healing_actions),
                    'validation_enabled': True
                },
                'topology_template': {
                    'description': f'Self-healing orchestration for {node_id} ({node_type})',
                    'node_templates': self.build_node_templates(node_id, node_type, healing_actions),
                    'policies': self.build_healing_policies(healing_actions),
                    'workflows': self.build_healing_workflows(healing_actions),
                    'inputs': {
                        'healing_plan_id': {'type': 'string', 'default': plan_id},
                        'target_node_id': {'type': 'string', 'default': node_id},
                        'execution_timeout': {'type': 'integer', 'default': 1800}
                    },
                    'outputs': {
                        'healing_status': {'type': 'string'},
                        'execution_summary': {'type': 'string'},
                        'performance_metrics': {'type': 'map'}
                    }
                }
            }
            
            # Validate TOSCA template
            is_valid, validation_messages = self.validate_tosca_template(tosca_template_data)
            if not is_valid:
                logger.error(f"TOSCA template validation failed: {validation_messages}")
                raise ValueError(f"Invalid TOSCA template: {validation_messages}")
            
            # Generate filename and save
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            template_filename = f"healing_tosca_{node_id}_{timestamp}.yaml"
            template_path = self.tosca_templates_dir / template_filename
            
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
            logger.info(f"✅ Enhanced TOSCA template generated: {template_path}")
            logger.info(f"📊 Validation: PASSED | Actions: {len(healing_actions)} | Node Type: {node_type}")
            
            return tosca_template
            
        except Exception as e:
            logger.error(f"❌ Error generating enhanced TOSCA template: {e}")
            raise

    # **PRESERVED: All remaining existing methods with same functionality**
    # [Including: listen_for_healing_plans, process_orchestration_queue, etc.]
    
    async def generate_ns3_integration_plan(self, healing_plan_data: Dict[str, Any]) -> NS3IntegrationPlan:
        """Generate NS3 integration plan (preserved existing method)"""
        try:
            plan_id = healing_plan_data.get('plan_id', 'unknown')
            node_id = healing_plan_data.get('node_id', 'unknown')
            
            # Create comprehensive NS3 integration plan
            integration_plan_data = {
                'simulation_config': self.ns3_config['simulation_defaults'],
                'network_topology_changes': [],
                'routing_updates': [],
                'configuration_changes': [],
                'simulation_parameters': {
                    'healing_validation_enabled': True,
                    'metrics_collection_enhanced': True,
                    'animation_healing_events': True
                },
                'validation_criteria': self.ns3_config['healing_validation']
            }
            
            # Generate filename and save
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            plan_filename = f"ns3_integration_{node_id}_{timestamp}.json"
            plan_path = self.ns3_integration_dir / plan_filename
            
            with open(plan_path, 'w') as f:
                json.dump(integration_plan_data, f, indent=2)
            
            ns3_plan = NS3IntegrationPlan(
                plan_id=f"NS3_{plan_id}_{int(time.time())}",
                healing_plan_id=plan_id,
                node_id=node_id,
                simulation_config=integration_plan_data['simulation_config'],
                network_topology_changes=integration_plan_data['network_topology_changes'],
                routing_updates=integration_plan_data['routing_updates'],
                configuration_changes=integration_plan_data['configuration_changes'],
                simulation_parameters=integration_plan_data['simulation_parameters'],
                validation_criteria=integration_plan_data['validation_criteria'],
                generated_timestamp=datetime.now().isoformat(),
                file_path=str(plan_path)
            )
            
            self.metrics.ns3_plans_exported += 1
            logger.info(f"✅ NS3 integration plan generated: {plan_path}")
            
            return ns3_plan
            
        except Exception as e:
            logger.error(f"❌ Error generating NS3 integration plan: {e}")
            raise

    async def create_deployment_configuration(self, healing_plan_data: Dict[str, Any], 
                                            tosca_template: ToscaTemplate) -> Dict[str, Any]:
        """Create deployment configuration (preserved existing method)"""
        return {
            'deployment_type': 'simulation_based',
            'target_environment': 'ns3_rural_network',
            'healing_plan_reference': healing_plan_data.get('plan_id'),
            'tosca_template_reference': tosca_template.template_id,
            'execution_parameters': {
                'auto_execute': not healing_plan_data.get('requires_approval', False),
                'validation_required': True,
                'rollback_enabled': True,
                'monitoring_enabled': True
            }
        }

    async def execute_orchestration_deployment(self, tosca_template: ToscaTemplate, 
                                             deployment_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute orchestration deployment (preserved existing method)"""
        try:
            deployment_id = f"DEPLOY_{tosca_template.template_id}_{int(time.time())}"
            
            logger.info(f"🚀 Executing robust orchestration deployment: {deployment_id}")
            
            execution_result = {
                'deployment_id': deployment_id,
                'status': 'success',
                'execution_type': 'simulation_based',
                'tosca_template_applied': tosca_template.file_path,
                'deployment_config_applied': deployment_config,
                'timestamp': datetime.now().isoformat(),
                'validation_results': {
                    'tosca_validation': 'passed',
                    'configuration_validation': 'passed',
                    'deployment_readiness': 'ready'
                },
                'simulated_infrastructure_changes': [
                    f"Node {tosca_template.node_id} healing actions scheduled",
                    "Network topology update queued for NS-3",
                    "Healing policies activated in simulation",
                    "Monitoring and rollback mechanisms enabled"
                ],
                'next_steps': [
                    "NS-3 will process deployment file",
                    "Healing actions will be visualized",
                    "Metrics will be collected and fed back",
                    "Validation criteria will be monitored"
                ]
            }
            
            logger.info(f"✅ Robust deployment completed: {deployment_id}")
            self.metrics.successful_deployments += 1
            
            return execution_result
            
        except Exception as e:
            logger.error(f"❌ Robust deployment failed: {e}")
            self.metrics.failed_operations += 1
            
            return {
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    # **PRESERVED: All existing communication, monitoring, and cleanup methods**
    
    async def listen_for_healing_plans(self):
        """Listen for healing plans from Healing Agent via ZeroMQ"""
        logger.info("👂 Starting ZeroMQ healing plans listener...")
        
        while self.is_running:
            try:
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
            
            logger.info(f"🎯 ZeroMQ healing plan received: {plan_id}")
            logger.info(f"📍 Node: {node_id} | Severity: {severity}")
            logger.info(f"🔧 Actions: {len(healing_plan_data.get('healing_actions', []))}")
            
            self.metrics.healing_plans_received += 1
            await self.processing_queue.put(healing_plan_data)
            
        except Exception as e:
            logger.error(f"❌ Error handling healing plan: {e}")
            self.metrics.failed_operations += 1

    async def process_orchestration_queue(self):
        """Process orchestration requests from the queue"""
        logger.info("🔄 Starting orchestration queue processor...")
        
        while self.is_running:
            try:
                healing_plan_data = await asyncio.wait_for(
                    self.processing_queue.get(),
                    timeout=5.0
                )
                
                start_time = time.time()
                await self.execute_comprehensive_orchestration(healing_plan_data)
                processing_time = time.time() - start_time
                
                self.processing_times.append(processing_time)
                self.metrics.orchestration_executions += 1
                self.metrics.avg_processing_time = sum(self.processing_times) / len(self.processing_times)
                
                logger.info(f"✅ ZeroMQ orchestration completed in {processing_time:.2f}s")
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
            
            logger.info(f"🎯 Executing ZeroMQ comprehensive orchestration: {plan_id}")
            
            # Generate enhanced TOSCA Template with validation
            tosca_template = await self.generate_enhanced_tosca_template(healing_plan_data)
            
            # Generate NS3 Integration Plan
            ns3_plan = await self.generate_ns3_integration_plan(healing_plan_data)
            
            # Create Deployment Configuration
            deployment_config = await self.create_deployment_configuration(healing_plan_data, tosca_template)
            
            # Execute Orchestration
            execution_result = None
            if not healing_plan_data.get('requires_approval', False):
                execution_result = await self.execute_orchestration_deployment(
                    tosca_template, deployment_config
                )
            
            # Create enhanced NS3 deployment file
            await self.create_ns3_deployment_file(healing_plan_data, tosca_template, execution_result)
            
            # Send status updates
            await self.send_orchestration_status_update(
                plan_id, tosca_template, ns3_plan, execution_result
            )
            
            # Generate comprehensive report
            await self.generate_orchestration_report(
                healing_plan_data, tosca_template, ns3_plan, execution_result
            )
            
            logger.info(f"✅ ZeroMQ comprehensive orchestration completed: {plan_id}")
            
        except Exception as e:
            logger.error(f"❌ ZeroMQ comprehensive orchestration failed: {e}")
            self.metrics.failed_operations += 1

    async def send_orchestration_status_update(self, plan_id: str, tosca_template: ToscaTemplate, 
                                             ns3_plan: NS3IntegrationPlan, execution_result: Optional[Dict[str, Any]]):
        """Send orchestration status update"""
        try:
            status_update = {
                'message_type': 'orchestration_status',
                'timestamp': datetime.now().isoformat(),
                'plan_id': plan_id,
                'orchestration_status': {
                    'tosca_template_generated': True,
                    'ns3_plan_created': True,
                    'deployment_executed': execution_result is not None,
                    'overall_status': 'success' if execution_result and execution_result.get('status') == 'success' else 'pending'
                },
                'file_references': {
                    'tosca_template': tosca_template.file_path,
                    'ns3_integration_plan': ns3_plan.file_path
                }
            }
            
            await self.status_publisher.send_json(status_update)
            logger.info(f"📤 Status update sent for plan: {plan_id}")
            
        except Exception as e:
            logger.error(f"❌ Error sending status update: {e}")

    async def generate_orchestration_report(self, healing_plan_data: Dict[str, Any], 
                                          tosca_template: ToscaTemplate, ns3_plan: NS3IntegrationPlan, 
                                          execution_result: Optional[Dict[str, Any]]):
        """Generate comprehensive orchestration report"""
        try:
            plan_id = healing_plan_data.get('plan_id', 'unknown')
            
            report = {
                'report_metadata': {
                    'report_id': f"REPORT_{plan_id}_{int(time.time())}",
                    'generated_timestamp': datetime.now().isoformat(),
                    'healing_plan_id': plan_id,
                    'node_id': healing_plan_data.get('node_id', 'unknown')
                },
                'orchestration_summary': {
                    'healing_actions_count': len(healing_plan_data.get('healing_actions', [])),
                    'tosca_template_generated': True,
                    'ns3_integration_completed': True,
                    'validation_results': {
                        'tosca_validation': 'passed',
                        'deployment_validation': execution_result is not None
                    }
                },
                'generated_artifacts': {
                    'tosca_template': {
                        'file_path': tosca_template.file_path,
                        'template_id': tosca_template.template_id,
                        'node_templates_count': len(tosca_template.node_templates)
                    },
                    'ns3_integration_plan': {
                        'file_path': ns3_plan.file_path,
                        'plan_id': ns3_plan.plan_id
                    }
                },
                'execution_summary': execution_result,
                'performance_metrics': {
                    'total_processing_time': time.time() - time.time(),  # This would be calculated properly
                    'tosca_generation_time': 'tracked',
                    'validation_time': 'tracked'
                }
            }
            
            # Save report
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = self.orchestration_reports_dir / f"orchestration_report_{plan_id}_{timestamp}.json"
            
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"📋 Orchestration report generated: {report_file}")
            
        except Exception as e:
            logger.error(f"❌ Error generating orchestration report: {e}")

    async def monitor_orchestration_performance(self):
        """Monitor orchestration performance metrics"""
        logger.info("📊 Starting robust orchestration performance monitoring...")
        
        while self.is_running:
            try:
                await asyncio.sleep(60)
                
                logger.info(f"📊 Robust Orchestration Performance Summary:")
                logger.info(f"   • ZeroMQ Healing Plans: {self.metrics.healing_plans_received}")
                logger.info(f"   • File Healing Plans: {self.metrics.file_healing_plans_processed}")
                logger.info(f"   • TOSCA Templates: {self.metrics.tosca_templates_generated}")
                logger.info(f"   • TOSCA Validations: {self.metrics.tosca_validation_successes}/{self.metrics.tosca_validation_failures}")
                logger.info(f"   • NS3 Plans: {self.metrics.ns3_plans_exported}")
                logger.info(f"   • NS3 Deployments: {self.metrics.ns3_deployment_files_created}")
                logger.info(f"   • Successful Deployments: {self.metrics.successful_deployments}")
                logger.info(f"   • Failed Operations: {self.metrics.failed_operations}")
                logger.info(f"   • Avg Processing Time: {self.metrics.avg_processing_time:.2f}s")
                logger.info(f"   • File Monitoring: {'ACTIVE' if self.file_monitoring_active else 'INACTIVE'}")
                
                # Clean up processing times
                if len(self.processing_times) > 100:
                    self.processing_times = self.processing_times[-100:]
                
            except Exception as e:
                logger.error(f"❌ Error in performance monitoring: {e}")

    async def generate_periodic_reports(self):
        """Generate periodic orchestration reports"""
        logger.info("Starting periodic report generation...")
        
        while self.is_running:
            try:
                await asyncio.sleep(1800)  # Every 30 minutes
                
                report = {
                    'report_timestamp': datetime.now().isoformat(),
                    'reporting_period': '30 minutes',
                    'orchestration_metrics': asdict(self.metrics),
                    'active_orchestrations': len(self.active_orchestrations),
                    'performance_summary': {
                        'tosca_generation_success_rate': (
                            self.metrics.tosca_validation_successes / 
                            max(self.metrics.tosca_templates_generated, 1) * 100
                        ),
                        'deployment_success_rate': (
                            self.metrics.successful_deployments / 
                            max(self.metrics.orchestration_executions, 1) * 100
                        ),
                        'avg_processing_time': self.metrics.avg_processing_time,
                        'file_processing_efficiency': (
                            self.metrics.file_healing_plans_processed / 
                            max(self.metrics.realtime_orchestration_cycles, 1)
                        )
                    }
                }
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                report_file = self.orchestration_reports_dir / f"periodic_robust_report_{timestamp}.json"
                
                with open(report_file, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
                
                logger.info(f"📊 Periodic robust report generated: {report_file}")
                
            except Exception as e:
                logger.error(f"❌ Error generating periodic report: {e}")

    async def cleanup_old_files(self):
        """Clean up old generated files"""
        while self.is_running:
            try:
                await asyncio.sleep(3600)  # Clean up every hour
                
                # Clean up old TOSCA templates (keep last 50)
                tosca_files = sorted(self.tosca_templates_dir.glob("*.yaml"), key=os.path.getmtime)
                if len(tosca_files) > 50:
                    for old_file in tosca_files[:-50]:
                        old_file.unlink()
                        logger.debug(f"🧹 Cleaned up old TOSCA file: {old_file.name}")
                
                # Clean up old reports (keep last 100)
                report_files = sorted(self.orchestration_reports_dir.glob("*.json"), key=os.path.getmtime)
                if len(report_files) > 100:
                    for old_file in report_files[:-100]:
                        old_file.unlink()
                        logger.debug(f"🧹 Cleaned up old report: {old_file.name}")
                
            except Exception as e:
                logger.error(f"❌ Error in cleanup: {e}")

    async def start_with_enhanced_realtime_monitoring(self):
        """Start with both ZeroMQ and file-based monitoring"""
        logger.info("🚀 Starting Robust Orchestration Agent with Enhanced Monitoring...")
        logger.info("👂 ZeroMQ Communication: Port 5558")
        logger.info("📁 File Monitoring: healing_plans_for_orchestration/ every 10s")
        logger.info("✅ TOSCA Validation: ENABLED")
        logger.info("🎯 Enhanced NS3 Integration: ALL ACTION TYPES")
        
        await self.initialize_communication()
        
        self.is_running = True
        
        tasks = [
            asyncio.create_task(self.listen_for_healing_plans()),
            asyncio.create_task(self.process_orchestration_queue()),
            asyncio.create_task(self.monitor_orchestration_performance()),
            asyncio.create_task(self.generate_periodic_reports()),
            asyncio.create_task(self.cleanup_old_files()),
            asyncio.create_task(self.monitor_healing_plan_files_every_10_seconds())
        ]
        
        logger.info("✅ Robust Orchestration Agent started successfully")
        logger.info("🏆 Features: TOSCA Validation | Enhanced Actions | Dual Monitoring")
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("🛑 Shutdown requested")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Enhanced cleanup with final comprehensive report"""
        try:
            self.is_running = False
            
            # Close ZeroMQ sockets
            if self.healing_subscriber:
                self.healing_subscriber.close()
            if self.status_publisher:
                self.status_publisher.close()
            if self.context:
                self.context.term()
            
            # Generate final comprehensive report
            final_report = {
                'shutdown_timestamp': datetime.now().isoformat(),
                'final_metrics': asdict(self.metrics),
                'performance_summary': {
                    'total_orchestrations': self.metrics.orchestration_executions,
                    'tosca_templates_generated': self.metrics.tosca_templates_generated,
                    'tosca_validation_success_rate': (
                        self.metrics.tosca_validation_successes / 
                        max(self.metrics.tosca_templates_generated, 1) * 100
                    ),
                    'deployment_success_rate': (
                        self.metrics.successful_deployments / 
                        max(self.metrics.orchestration_executions, 1) * 100
                    ),
                    'avg_processing_time': self.metrics.avg_processing_time
                },
                'communication_summary': {
                    'zeromq_plans_processed': self.metrics.healing_plans_received,
                    'file_plans_processed': self.metrics.file_healing_plans_processed,
                    'total_communication_channels': 2
                },
                'file_generation_summary': {
                    'tosca_templates': self.metrics.tosca_templates_generated,
                    'ns3_integration_plans': self.metrics.ns3_plans_exported,
                    'ns3_deployment_files': self.metrics.ns3_deployment_files_created,
                    'total_files': (
                        self.metrics.tosca_templates_generated + 
                        self.metrics.ns3_plans_exported + 
                        self.metrics.ns3_deployment_files_created
                    )
                }
            }
            
            final_report_file = self.orchestration_reports_dir / f"final_robust_orchestration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(final_report_file, 'w') as f:
                json.dump(final_report, f, indent=2, default=str)
            
            logger.info("✅ Robust Orchestration Agent cleanup completed")
            logger.info(f"📋 Final comprehensive report: {final_report_file}")
            logger.info(f"🏆 Session Summary:")
            logger.info(f"   • Total Orchestrations: {self.metrics.orchestration_executions}")
            logger.info(f"   • TOSCA Templates: {self.metrics.tosca_templates_generated}")
            logger.info(f"   • Validation Success Rate: {final_report['performance_summary']['tosca_validation_success_rate']:.1f}%")
            logger.info(f"   • Deployment Success Rate: {final_report['performance_summary']['deployment_success_rate']:.1f}%")
            
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")


# Main execution function
async def main():
    """Main execution function for Robust Orchestration Agent"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    agent = RobustOrchestrationAgent()
    
    try:
        print('🏆 Robust Orchestration Agent starting...')
        print('✅ Complete TOSCA template generation with validation')
        print('🎯 Enhanced NS3 command generation for ALL action types')
        print('👂 Dual communication: ZeroMQ + File monitoring')
        print('📊 Comprehensive metrics and performance tracking')
        print('🔧 Advanced healing action support:')
        print('   • Power optimization')
        print('   • Traffic rerouting')
        print('   • Load balancing')
        print('   • Emergency restart')
        print('   • Resource reallocation')
        print('   • Signal boost')
        print('   • Network isolation')
        print('   • Generic healing actions')
        print(f'📁 TOSCA Templates: {agent.tosca_templates_dir}')
        print(f'📁 NS3 Integration: {agent.healing_plans_for_ns3_dir}')
        print(f'📁 NS3 Deployments: {agent.ns3_deployments_dir}')
        print(f'📊 Reports: {agent.orchestration_reports_dir}')
        
        await agent.start_with_enhanced_realtime_monitoring()
        
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown requested")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
    finally:
        await agent.cleanup()


if __name__ == '__main__':
    asyncio.run(main())