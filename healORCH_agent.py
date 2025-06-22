import os
# **CPU-ONLY CONFIGURATION - Optimized for 24GB RAM**
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'   # Keep for cleaner output

import asyncio
import logging
import json
import time
import yaml
import zmq
import zmq.asyncio
import google.generativeai as genai
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# **CPU-OPTIMIZED TENSORFLOW CONFIGURATION**
import tensorflow as tf
# Explicitly configure for CPU optimization with 24GB RAM
tf.config.set_visible_devices([], 'GPU')  # Disable GPU completely
tf.config.threading.set_inter_op_parallelism_threads(0)  # Use all CPU cores
tf.config.threading.set_intra_op_parallelism_threads(0)  # Use all CPU cores
tf.config.run_functions_eagerly(True)

# Configure memory growth for large RAM (24GB)
cpus = tf.config.list_physical_devices('CPU')
if cpus:
    try:
        # Enable memory growth to prevent TensorFlow from allocating all RAM at once
        for cpu in cpus:
            tf.config.experimental.set_memory_growth(cpu, True)
    except RuntimeError as e:
        print(f"Memory growth setting: {e}")

logger = logging.getLogger(__name__)

# **PRESERVED: All original data structures from both agents**
@dataclass
class AnomalyAlert:
    """Structured anomaly alert data from Healing Agent"""
    message_id: str
    node_id: str
    anomaly_id: str
    anomaly_score: float
    severity: str
    detection_timestamp: str
    network_context: Dict[str, Any]
    confidence: float = 0.95

@dataclass
class HealingAction:
    """Individual healing action from Healing Agent"""
    action_id: str
    action_type: str
    priority: int
    description: str
    parameters: Dict[str, Any]
    estimated_duration: int
    success_probability: float

@dataclass
class HealingPlan:
    """Complete healing plan from Healing Agent"""
    plan_id: str
    anomaly_id: str
    node_id: str
    severity: str
    healing_actions: List[HealingAction]
    total_estimated_duration: int
    confidence: float
    requires_approval: bool
    generated_timestamp: str

@dataclass
class ToscaTemplate:
    """TOSCA template structure from Orchestration Agent"""
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
    """NS3 integration plan structure from Orchestration Agent"""
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
class CombinedMetrics:
    """Combined metrics for unified agent"""
    # Healing metrics
    alerts_received: int = 0
    healing_plans_generated: int = 0
    healing_responses_sent: int = 0
    
    # Orchestration metrics
    tosca_templates_generated: int = 0
    ns3_plans_exported: int = 0
    orchestration_executions: int = 0
    successful_deployments: int = 0
    
    # Combined metrics
    end_to_end_completions: int = 0
    failed_operations: int = 0
    avg_processing_time: float = 0.0

class CombinedHealingOrchestrationAgent:
    """
    🏆 ITU Competition Ready: Combined Healing & Orchestration Agent
    💻 CPU-Optimized for 24GB RAM
    
    Integrates ALL functionalities from both agents:
    - Gemini AI-powered healing plan generation
    - TOSCA template orchestration
    - NS3 integration planning  
    - Complete closed-loop healing workflow
    """

    def __init__(self, *args, **kwargs):
        # 🤖 PRESERVED: Gemini AI Configuration from Healing Agent
        self.gemini_api_key = os.getenv('GEMINI_API_KEY', 'YOUR_GEMINI_API_KEY_HERE')
        self.gemini_model = None
        self.initialize_gemini()
        
        # 🔗 ENHANCED: Unified Communication Setup
        self.context = zmq.asyncio.Context()
        self.a2a_subscriber = None      # Receive from Calculation Agent (port 5555)
        self.mcp_publisher = None       # Send to Calculation Agent (port 5556)
        self.status_publisher = None    # Send status updates (port 5559)
        
        # 📁 COMBINED: All directories from both agents
        self.healing_plans_dir = Path("healing_plans")
        self.healing_reports_dir = Path("healing_reports")
        self.tosca_templates_dir = Path("tosca_templates")
        self.ns3_integration_dir = Path("ns3_integration")
        self.healing_plans_for_ns3_dir = Path("healing_plans_for_ns3")
        self.orchestration_reports_dir = Path("orchestration_reports")
        self.deployment_configs_dir = Path("deployment_configs")
        
        # Create all directories
        for directory in [self.healing_plans_dir, self.healing_reports_dir, 
                         self.tosca_templates_dir, self.ns3_integration_dir,
                         self.healing_plans_for_ns3_dir, self.orchestration_reports_dir,
                         self.deployment_configs_dir]:
            directory.mkdir(exist_ok=True)
        
        # 📊 COMBINED: Unified metrics and tracking
        self.metrics = CombinedMetrics()
        self.processing_queue = asyncio.Queue()
        self.active_healing_plans = {}
        self.active_orchestrations = {}
        self.processing_times = []
        
        # 🎯 PRESERVED: Nokia Rural Network Knowledge Base from Healing Agent
        self.network_knowledge = self.initialize_network_knowledge()
        
        # 🎯 PRESERVED: Network Templates from Orchestration Agent  
        self.network_templates = self.initialize_network_templates()
        
        # 🔧 PRESERVED: NS3 Configuration from Orchestration Agent
        self.ns3_config = self.initialize_ns3_configuration()
        
        logger.info("✅ Combined Healing & Orchestration Agent initialized (CPU-OPTIMIZED)")
        logger.info(f"🏥 Healing functionality: Gemini AI + Knowledge Base")
        logger.info(f"🎯 Orchestration functionality: TOSCA + NS3 Integration")
        logger.info(f"💻 CPU Configuration: 24GB RAM optimized")
        logger.info(f"📁 All directories created and ready")

    # **PRESERVED: All Healing Agent initialization methods**
    def initialize_gemini(self):
        """Initialize Gemini AI for healing plan generation"""
        try:
            if self.gemini_api_key and self.gemini_api_key != 'YOUR_GEMINI_API_KEY_HERE':
                genai.configure(api_key=self.gemini_api_key)
                self.gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
                logger.info("✅ Gemini AI initialized successfully")
            else:
                logger.warning("⚠️ Gemini API key not provided, using fallback healing generation")
                self.gemini_model = None
        except Exception as e:
            logger.error(f"❌ Gemini AI initialization failed: {e}")
            self.gemini_model = None

    def initialize_network_knowledge(self) -> Dict[str, Any]:
        """PRESERVED: Nokia Rural Network knowledge base from Healing Agent"""
        return {
            'node_types': {
                'CORE': {
                    'description': 'Core network nodes handling main traffic',
                    'critical_metrics': ['throughput', 'latency', 'packet_loss'],
                    'common_faults': ['hardware_failure', 'overload', 'routing_issues'],
                    'healing_strategies': ['load_balancing', 'failover', 'traffic_rerouting']
                },
                'DIST': {
                    'description': 'Distribution nodes connecting core to access',
                    'critical_metrics': ['power_stability', 'link_utilization', 'signal_strength'],
                    'common_faults': ['power_issues', 'link_degradation', 'interference'],
                    'healing_strategies': ['power_optimization', 'backup_path_activation', 'signal_boost']
                },
                'ACC': {
                    'description': 'Access nodes serving end users',
                    'critical_metrics': ['cpu_usage', 'memory_usage', 'buffer_occupancy'],
                    'common_faults': ['resource_exhaustion', 'congestion', 'equipment_failure'],
                    'healing_strategies': ['resource_reallocation', 'load_shedding', 'service_migration']
                }
            },
            'fault_patterns': {
                'throughput_loss': {
                    'symptoms': ['low_throughput', 'high_latency', 'packet_loss'],
                    'causes': ['congestion', 'hardware_failure', 'routing_loops'],
                    'healing_actions': ['traffic_rerouting', 'load_balancing', 'hardware_replacement']
                },
                'power_instability': {
                    'symptoms': ['voltage_fluctuation', 'power_drops', 'equipment_restarts'],
                    'causes': ['power_grid_issues', 'battery_degradation', 'power_management_failure'],
                    'healing_actions': ['backup_power_activation', 'power_optimization', 'equipment_restart']
                },
                'equipment_overload': {
                    'symptoms': ['high_cpu', 'high_memory', 'buffer_overflow'],
                    'causes': ['traffic_spike', 'resource_leak', 'inadequate_capacity'],
                    'healing_actions': ['load_shedding', 'resource_reallocation', 'service_migration']
                }
            },
            'healing_templates': {
                'emergency_rerouting': {
                    'duration': 30,
                    'success_rate': 0.9,
                    'prerequisites': ['backup_path_available', 'routing_table_access']
                },
                'power_management': {
                    'duration': 60,
                    'success_rate': 0.85,
                    'prerequisites': ['backup_power_available', 'power_control_access']
                },
                'resource_optimization': {
                    'duration': 120,
                    'success_rate': 0.8,
                    'prerequisites': ['resource_monitoring', 'configuration_access']
                }
            }
        }

    def initialize_network_templates(self) -> Dict[str, Any]:
        """PRESERVED: Nokia rural network TOSCA templates from Orchestration Agent"""
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
        """PRESERVED: NS3 simulation configuration from Orchestration Agent"""
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
        """ENHANCED: Unified communication setup"""
        try:
            # 👂 A2A Subscriber - Receive anomaly alerts from Calculation Agent
            self.a2a_subscriber = self.context.socket(zmq.SUB)
            self.a2a_subscriber.connect("tcp://127.0.0.1:5555")
            self.a2a_subscriber.setsockopt_string(zmq.SUBSCRIBE, "")

            # 📤 MCP Publisher - Send healing responses back to Calculation Agent
            self.mcp_publisher = self.context.socket(zmq.PUB)
            self.mcp_publisher.bind("tcp://127.0.0.1:5556")

            # 📡 Status Publisher - Send orchestration status updates
            self.status_publisher = self.context.socket(zmq.PUB)
            self.status_publisher.bind("tcp://127.0.0.1:5559")

            logger.info("✅ Combined Agent communication initialized")
            logger.info("👂 A2A Subscriber: Port 5555 (from Calculation Agent)")
            logger.info("📤 MCP Publisher: Port 5556 (to Calculation Agent)")
            logger.info("📡 Status Publisher: Port 5559 (status updates)")
            logger.info("🔄 Internal orchestration: Direct method calls (no ZeroMQ)")

            # Give time for socket binding
            await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"❌ Communication initialization failed: {e}")
            raise

    async def start_combined_agent(self):
        """🚀 MAIN: Start the combined healing and orchestration agent"""
        logger.info("🚀 Starting Combined Healing & Orchestration Agent...")

        # Initialize communication
        await self.initialize_communication()

        # Start processing tasks
        self.is_running = True

        # Create background tasks
        tasks = [
            asyncio.create_task(self.listen_for_anomaly_alerts()),
            asyncio.create_task(self.process_combined_workflow_queue()),
            asyncio.create_task(self.monitor_combined_performance()),
            asyncio.create_task(self.generate_combined_reports()),
            asyncio.create_task(self.cleanup_old_files())
        ]

        logger.info("✅ Combined Agent started successfully")
        logger.info("👂 Listening for anomaly alerts...")
        logger.info("🔄 Processing unified healing→orchestration workflow...")
        logger.info("📊 Performance monitoring active...")

        try:
            # Wait for all tasks
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("🛑 Shutdown requested")
        finally:
            await self.cleanup()

    async def listen_for_anomaly_alerts(self):
        """PRESERVED: Enhanced anomaly alert listener from Healing Agent"""
        logger.info("👂 Starting anomaly alert listener...")
        while self.is_running:
            try:
                # Non-blocking receive with timeout
                message = await asyncio.wait_for(
                    self.a2a_subscriber.recv_json(),
                    timeout=1.0
                )

                if message.get('message_type') == 'anomaly_alert':
                    await self.handle_incoming_anomaly_alert(message)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"❌ Error receiving anomaly alert: {e}")
                self.metrics.failed_operations += 1
                await asyncio.sleep(1)

    async def handle_incoming_anomaly_alert(self, alert_message: Dict[str, Any]):
        """PRESERVED: Handle incoming anomaly alert from Healing Agent"""
        try:
            # Parse and validate alert
            anomaly_alert = self.parse_anomaly_alert(alert_message)
            if anomaly_alert is None:
                logger.error("❌ Invalid anomaly alert received")
                return

            logger.info(f"🚨 Anomaly alert received: {anomaly_alert.anomaly_id}")
            logger.info(f"📍 Node: {anomaly_alert.node_id} | Severity: {anomaly_alert.severity}")
            logger.info(f"📊 Score: {anomaly_alert.anomaly_score:.3f}")

            self.metrics.alerts_received += 1

            # Add to unified processing queue
            await self.processing_queue.put(anomaly_alert)

        except Exception as e:
            logger.error(f"❌ Error handling anomaly alert: {e}")
            self.metrics.failed_operations += 1

    def parse_anomaly_alert(self, alert_message: Dict[str, Any]) -> Optional[AnomalyAlert]:
        """PRESERVED: Parse and validate incoming anomaly alert from Healing Agent"""
        try:
            anomaly_details = alert_message.get('anomaly_details', {})
            network_context = alert_message.get('network_context', {})

            return AnomalyAlert(
                message_id=alert_message.get('message_id', ''),
                node_id=anomaly_details.get('node_id', ''),
                anomaly_id=anomaly_details.get('anomaly_id', ''),
                anomaly_score=anomaly_details.get('anomaly_score', 0.0),
                severity=anomaly_details.get('severity', 'unknown'),
                detection_timestamp=anomaly_details.get('detection_timestamp', ''),
                network_context=network_context,
                confidence=anomaly_details.get('confidence', 0.95)
            )

        except Exception as e:
            logger.error(f"❌ Error parsing anomaly alert: {e}")
            return None

    async def process_combined_workflow_queue(self):
        """🏆 NEW: Unified processing queue - Healing → Orchestration → Deployment"""
        logger.info("🔄 Starting combined workflow processor...")
        while self.is_running:
            try:
                # Get anomaly alert from queue (with timeout)
                anomaly_alert = await asyncio.wait_for(
                    self.processing_queue.get(),
                    timeout=5.0
                )

                # **COMPLETE WORKFLOW: Healing → Orchestration → Deployment**
                start_time = time.time()
                success = await self.execute_complete_healing_orchestration_workflow(anomaly_alert)
                processing_time = time.time() - start_time

                if success:
                    # Track performance
                    self.processing_times.append(processing_time)
                    self.metrics.end_to_end_completions += 1
                    logger.info(f"✅ Complete workflow executed in {processing_time:.2f}s")
                else:
                    logger.error(f"❌ Complete workflow failed for {anomaly_alert.anomaly_id}")
                    self.metrics.failed_operations += 1

                # Mark task as done
                self.processing_queue.task_done()

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"❌ Error processing combined workflow: {e}")
                self.metrics.failed_operations += 1

    async def execute_complete_healing_orchestration_workflow(self, anomaly_alert: AnomalyAlert) -> bool:
        """
        🎯 MAIN WORKFLOW: Complete end-to-end healing and orchestration
        
        Flow: Anomaly Alert → Healing Plan → TOSCA Template → NS3 Integration → Deployment
        """
        try:
            logger.info(f"🔄 Starting complete workflow for {anomaly_alert.anomaly_id}")

            # **STEP 1: Generate Healing Plan (from Healing Agent)**
            healing_plan = await self.generate_comprehensive_healing_plan(anomaly_alert)
            if not healing_plan:
                logger.error(f"❌ Step 1 failed: No healing plan generated")
                return False

            # **STEP 2: Generate TOSCA Template (from Orchestration Agent)**
            tosca_template = await self.generate_enhanced_tosca_template_from_healing_plan(healing_plan)
            if not tosca_template:
                logger.error(f"❌ Step 2 failed: TOSCA template generation failed")
                return False

            # **STEP 3: Generate NS3 Integration Plan (from Orchestration Agent)**
            ns3_plan = await self.generate_ns3_integration_plan_from_healing_plan(healing_plan)
            if not ns3_plan:
                logger.error(f"❌ Step 3 failed: NS3 integration plan generation failed")
                return False

            # **STEP 4: Execute Orchestration Deployment (from Orchestration Agent)**
            deployment_config = await self.create_deployment_configuration_from_healing_plan(healing_plan, tosca_template)
            execution_result = await self.execute_orchestration_deployment(tosca_template, deployment_config)

            # **STEP 5: Send All Responses**
            await self.send_healing_response_to_calculation_agent(anomaly_alert, healing_plan)
            await self.send_orchestration_status_update(healing_plan.plan_id, tosca_template, ns3_plan, execution_result)

            # **STEP 6: Generate Comprehensive Report**
            await self.generate_complete_workflow_report(anomaly_alert, healing_plan, tosca_template, ns3_plan, execution_result)

            logger.info(f"✅ Complete workflow successful: {healing_plan.plan_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Complete workflow failed: {e}")
            return False

    # **PRESERVED: All Healing Agent methods for plan generation**
    async def generate_comprehensive_healing_plan(self, anomaly_alert: AnomalyAlert) -> Optional[HealingPlan]:
        """PRESERVED: Generate comprehensive healing plan from Healing Agent"""
        try:
            logger.info(f"💡 Generating healing plan for {anomaly_alert.anomaly_id}...")

            # Analyze network context
            network_analysis = self.analyze_network_context(anomaly_alert)

            # Generate healing actions using multiple strategies
            healing_actions = []

            # 1. Knowledge-based healing actions
            kb_actions = self.generate_knowledge_based_actions(anomaly_alert, network_analysis)
            healing_actions.extend(kb_actions)

            # 2. AI-generated healing actions (if Gemini available)
            if self.gemini_model:
                ai_actions = await self.generate_ai_healing_actions(anomaly_alert, network_analysis)
                healing_actions.extend(ai_actions)

            # 3. Template-based healing actions
            template_actions = self.generate_template_based_actions(anomaly_alert, network_analysis)
            healing_actions.extend(template_actions)

            # Remove duplicates and prioritize
            healing_actions = self.prioritize_and_deduplicate_actions(healing_actions)

            if not healing_actions:
                logger.error(f"❌ No healing actions generated for {anomaly_alert.anomaly_id}")
                return None

            # Create comprehensive healing plan
            healing_plan = HealingPlan(
                plan_id=f"HEAL_{anomaly_alert.node_id}_{int(time.time())}",
                anomaly_id=anomaly_alert.anomaly_id,
                node_id=anomaly_alert.node_id,
                severity=anomaly_alert.severity,
                healing_actions=healing_actions,
                total_estimated_duration=sum(action.estimated_duration for action in healing_actions),
                confidence=self.calculate_plan_confidence(healing_actions),
                requires_approval=anomaly_alert.severity in ['critical', 'high'],
                generated_timestamp=datetime.now().isoformat()
            )

            # Save healing plan
            await self.save_healing_plan(healing_plan)

            # Track active healing plan
            self.active_healing_plans[healing_plan.plan_id] = healing_plan
            self.metrics.healing_plans_generated += 1

            logger.info(f"✅ Comprehensive healing plan generated: {healing_plan.plan_id}")
            logger.info(f"🔧 Actions: {len(healing_actions)} | Duration: {healing_plan.total_estimated_duration}s")
            logger.info(f"📊 Confidence: {healing_plan.confidence:.2f}")

            return healing_plan

        except Exception as e:
            logger.error(f"❌ Error generating healing plan: {e}")
            return None

    def analyze_network_context(self, anomaly_alert: AnomalyAlert) -> Dict[str, Any]:
        """PRESERVED: Analyze network context from Healing Agent"""
        try:
            network_context = anomaly_alert.network_context

            # Determine node type
            node_type = network_context.get('node_type', 'GENERIC')
            fault_pattern = network_context.get('fault_pattern', 'unknown')

            # Get node-specific knowledge
            node_knowledge = self.network_knowledge['node_types'].get(node_type, {})
            fault_knowledge = self.network_knowledge['fault_patterns'].get(fault_pattern, {})

            analysis = {
                'node_type': node_type,
                'fault_pattern': fault_pattern,
                'critical_metrics': node_knowledge.get('critical_metrics', []),
                'common_faults': node_knowledge.get('common_faults', []),
                'healing_strategies': node_knowledge.get('healing_strategies', []),
                'fault_symptoms': fault_knowledge.get('symptoms', []),
                'fault_causes': fault_knowledge.get('causes', []),
                'recommended_actions': fault_knowledge.get('healing_actions', []),
                'severity_level': anomaly_alert.severity,
                'anomaly_score': anomaly_alert.anomaly_score,
                'spatial_context': network_context.get('spatial_context', {})
            }

            return analysis

        except Exception as e:
            logger.error(f"❌ Error analyzing network context: {e}")
            return {}

    def generate_knowledge_based_actions(self, anomaly_alert: AnomalyAlert, analysis: Dict[str, Any]) -> List[HealingAction]:
        """PRESERVED: Generate healing actions based on knowledge base from Healing Agent"""
        actions = []
        try:
            node_type = analysis.get('node_type', 'GENERIC')
            fault_pattern = analysis.get('fault_pattern', 'unknown')

            # Generate actions based on node type and fault pattern
            if node_type == 'CORE' and fault_pattern == 'throughput_loss':
                actions.extend([
                    HealingAction(
                        action_id=f"KB_REROUTE_{int(time.time())}",
                        action_type="traffic_rerouting",
                        priority=1,
                        description="Reroute traffic through backup paths",
                        parameters={
                            'backup_path_priority': 'high',
                            'reroute_percentage': 50,
                            'monitoring_interval': 30
                        },
                        estimated_duration=30,
                        success_probability=0.9
                    ),
                    HealingAction(
                        action_id=f"KB_BALANCE_{int(time.time())}",
                        action_type="load_balancing",
                        priority=2,
                        description="Implement dynamic load balancing",
                        parameters={
                            'load_threshold': 0.8,
                            'balancing_algorithm': 'weighted_round_robin',
                            'monitoring_window': 60
                        },
                        estimated_duration=60,
                        success_probability=0.85
                    )
                ])

            elif node_type == 'DIST' and fault_pattern == 'power_instability':
                actions.extend([
                    HealingAction(
                        action_id=f"KB_POWER_{int(time.time())}",
                        action_type="power_optimization",
                        priority=1,
                        description="Activate backup power and optimize power consumption",
                        parameters={
                            'backup_power_activation': True,
                            'power_saving_mode': 'emergency',
                            'voltage_regulation': 'strict'
                        },
                        estimated_duration=60,
                        success_probability=0.8
                    ),
                    HealingAction(
                        action_id=f"KB_SIGNAL_{int(time.time())}",
                        action_type="signal_boost",
                        priority=2,
                        description="Boost signal strength to maintain connectivity",
                        parameters={
                            'power_increase_db': 3,
                            'antenna_optimization': True,
                            'interference_mitigation': True
                        },
                        estimated_duration=45,
                        success_probability=0.75
                    )
                ])

            elif node_type == 'ACC' and fault_pattern == 'equipment_overload':
                actions.extend([
                    HealingAction(
                        action_id=f"KB_RESOURCE_{int(time.time())}",
                        action_type="resource_reallocation",
                        priority=1,
                        description="Reallocate system resources dynamically",
                        parameters={
                            'cpu_limit_increase': 20,
                            'memory_cleanup': True,
                            'buffer_size_optimization': True
                        },
                        estimated_duration=90,
                        success_probability=0.8
                    ),
                    HealingAction(
                        action_id=f"KB_SHED_{int(time.time())}",
                        action_type="load_shedding",
                        priority=2,
                        description="Implement selective load shedding",
                        parameters={
                            'priority_preservation': 'high_priority_users',
                            'shedding_percentage': 25,
                            'recovery_criteria': 'resource_availability'
                        },
                        estimated_duration=30,
                        success_probability=0.9
                    )
                ])

            logger.info(f"✅ Generated {len(actions)} knowledge-based actions")

        except Exception as e:
            logger.error(f"❌ Error generating knowledge-based actions: {e}")

        return actions

    async def generate_ai_healing_actions(self, anomaly_alert: AnomalyAlert, analysis: Dict[str, Any]) -> List[HealingAction]:
        """PRESERVED: Generate AI-powered healing actions using Gemini from Healing Agent"""
        actions = []
        if not self.gemini_model:
            logger.warning("⚠️ Gemini AI not available, skipping AI-generated actions")
            return actions

        try:
            # Prepare prompt for Gemini
            prompt = self.build_gemini_prompt(anomaly_alert, analysis)

            # Generate response from Gemini
            response = await self.gemini_model.generate_content_async(prompt)

            # Parse Gemini response into healing actions
            ai_actions = self.parse_gemini_response(response.text)
            actions.extend(ai_actions)

            logger.info(f"✅ Generated {len(ai_actions)} AI-powered actions")

        except Exception as e:
            logger.error(f"❌ Error generating AI healing actions: {e}")

        return actions

    def build_gemini_prompt(self, anomaly_alert: AnomalyAlert, analysis: Dict[str, Any]) -> str:
        """PRESERVED: Build detailed prompt for Gemini AI from Healing Agent"""
        prompt = f"""
You are an expert Nokia rural network healing specialist. Generate specific healing actions for the following network anomaly:

ANOMALY DETAILS:
- Node ID: {anomaly_alert.node_id}
- Anomaly Score: {anomaly_alert.anomaly_score:.3f}
- Severity: {anomaly_alert.severity}
- Node Type: {analysis.get('node_type', 'unknown')}
- Fault Pattern: {analysis.get('fault_pattern', 'unknown')}

NETWORK CONTEXT:
- Critical Metrics: {', '.join(analysis.get('critical_metrics', []))}
- Detected Symptoms: {', '.join(analysis.get('fault_symptoms', []))}
- Possible Causes: {', '.join(analysis.get('fault_causes', []))}

Please generate 2-3 specific healing actions in JSON format with the following structure:
{{
  "actions": [
    {{
      "action_type": "specific_action_name",
      "description": "detailed description of the action",
      "priority": 1-3,
      "parameters": {{"key": "value"}},
      "estimated_duration": seconds,
      "success_probability": 0.0-1.0
    }}
  ]
}}

Focus on Nokia rural network best practices and ensure actions are:
1. Technically feasible for rural network infrastructure
2. Prioritized by impact and urgency
3. Include specific parameters for implementation
4. Realistic duration and success probability estimates
"""
        return prompt

    def parse_gemini_response(self, response_text: str) -> List[HealingAction]:
        """PRESERVED: Parse Gemini AI response into healing actions from Healing Agent"""
        actions = []
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                response_data = json.loads(json_match.group())
                action_data_list = response_data.get('actions', [])

                for i, action_data in enumerate(action_data_list):
                    action = HealingAction(
                        action_id=f"AI_{int(time.time())}_{i}",
                        action_type=action_data.get('action_type', 'ai_action'),
                        priority=action_data.get('priority', 3),
                        description=action_data.get('description', 'AI-generated action'),
                        parameters=action_data.get('parameters', {}),
                        estimated_duration=action_data.get('estimated_duration', 60),
                        success_probability=action_data.get('success_probability', 0.7)
                    )
                    actions.append(action)

        except Exception as e:
            logger.error(f"❌ Error parsing Gemini response: {e}")

        return actions

    def generate_template_based_actions(self, anomaly_alert: AnomalyAlert, analysis: Dict[str, Any]) -> List[HealingAction]:
        """PRESERVED: Generate healing actions based on predefined templates from Healing Agent"""
        actions = []
        try:
            severity = anomaly_alert.severity
            node_type = analysis.get('node_type', 'GENERIC')

            # Emergency actions for critical severity
            if severity == 'critical':
                actions.append(HealingAction(
                    action_id=f"EMERG_RESTART_{int(time.time())}",
                    action_type="emergency_restart",
                    priority=1,
                    description="Emergency service restart to restore functionality",
                    parameters={
                        'restart_type': 'graceful',
                        'backup_configuration': True,
                        'health_check_interval': 10
                    },
                    estimated_duration=120,
                    success_probability=0.95
                ))

            # Monitoring enhancement (universal)
            actions.append(HealingAction(
                action_id=f"MONITOR_{int(time.time())}",
                action_type="enhanced_monitoring",
                priority=3,
                description="Increase monitoring frequency and alerting sensitivity",
                parameters={
                    'monitoring_interval': 5,
                    'alert_threshold_reduction': 0.1,
                    'detailed_logging': True
                },
                estimated_duration=30,
                success_probability=0.99
            ))

            logger.info(f"✅ Generated {len(actions)} template-based actions")

        except Exception as e:
            logger.error(f"❌ Error generating template-based actions: {e}")

        return actions

    def prioritize_and_deduplicate_actions(self, actions: List[HealingAction]) -> List[HealingAction]:
        """PRESERVED: Prioritize and remove duplicate healing actions from Healing Agent"""
        try:
            # Remove duplicates based on action_type
            unique_actions = {}
            for action in actions:
                key = action.action_type
                if key not in unique_actions or action.priority < unique_actions[key].priority:
                    unique_actions[key] = action

            # Sort by priority (lower number = higher priority)
            sorted_actions = sorted(unique_actions.values(), key=lambda x: x.priority)

            # Limit to maximum 5 actions to avoid complexity
            final_actions = sorted_actions[:5]

            logger.info(f"✅ Prioritized and deduplicated: {len(final_actions)} final actions")
            return final_actions

        except Exception as e:
            logger.error(f"❌ Error prioritizing actions: {e}")
            return actions

    def calculate_plan_confidence(self, actions: List[HealingAction]) -> float:
        """PRESERVED: Calculate overall confidence for the healing plan from Healing Agent"""
        if not actions:
            return 0.0

        # Weighted average based on priority (higher priority actions have more weight)
        total_weight = 0
        weighted_confidence = 0

        for action in actions:
            weight = (4 - action.priority)  # Priority 1 = weight 3, Priority 3 = weight 1
            weighted_confidence += action.success_probability * weight
            total_weight += weight

        return weighted_confidence / total_weight if total_weight > 0 else 0.0

    async def save_healing_plan(self, healing_plan: HealingPlan):
        """PRESERVED: Save healing plan to disk from Healing Agent"""
        try:
            plan_file = self.healing_plans_dir / f"{healing_plan.plan_id}.json"
            plan_data = {
                'plan_id': healing_plan.plan_id,
                'anomaly_id': healing_plan.anomaly_id,
                'node_id': healing_plan.node_id,
                'severity': healing_plan.severity,
                'generated_timestamp': healing_plan.generated_timestamp,
                'total_estimated_duration': healing_plan.total_estimated_duration,
                'confidence': healing_plan.confidence,
                'requires_approval': healing_plan.requires_approval,
                'healing_actions': [
                    {
                        'action_id': action.action_id,
                        'action_type': action.action_type,
                        'priority': action.priority,
                        'description': action.description,
                        'parameters': action.parameters,
                        'estimated_duration': action.estimated_duration,
                        'success_probability': action.success_probability
                    }
                    for action in healing_plan.healing_actions
                ]
            }

            with open(plan_file, 'w') as f:
                json.dump(plan_data, f, indent=2, default=str)

            logger.info(f"💾 Healing plan saved: {plan_file}")

        except Exception as e:
            logger.error(f"❌ Error saving healing plan: {e}")

    # **ENHANCED: TOSCA generation from healing plan (adapted from Orchestration Agent)**
    async def generate_enhanced_tosca_template_from_healing_plan(self, healing_plan: HealingPlan) -> Optional[ToscaTemplate]:
        """ENHANCED: Generate TOSCA template from healing plan instead of raw data"""
        try:
            logger.info(f"📋 Generating TOSCA template for healing plan {healing_plan.plan_id}...")

            # Get node type for template selection
            node_type = self.determine_node_type(healing_plan.node_id)
            node_template_config = self.network_templates['node_type_mappings'].get(node_type, {})

            # Build TOSCA template structure
            tosca_template_data = {
                **self.network_templates['base_template'],
                'metadata': {
                    **self.network_templates['base_template']['metadata'],
                    'healing_plan_id': healing_plan.plan_id,
                    'target_node_id': healing_plan.node_id,
                    'node_type': node_type,
                    'generated_timestamp': datetime.now().isoformat()
                },
                'topology_template': {
                    'description': f'Self-healing orchestration for {healing_plan.node_id}',
                    'node_templates': self.build_node_templates(healing_plan.node_id, node_type, healing_plan.healing_actions),
                    'policies': self.build_healing_policies_from_actions(healing_plan.healing_actions),
                    'workflows': self.build_healing_workflows_from_actions(healing_plan.healing_actions)
                }
            }

            # Generate unique template filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            template_filename = f"healing_tosca_{healing_plan.node_id}_{timestamp}.yaml"
            template_path = self.tosca_templates_dir / template_filename

            # Save TOSCA template to file
            with open(template_path, 'w') as f:
                yaml.dump(tosca_template_data, f, default_flow_style=False, indent=2)

            # Create ToscaTemplate object
            tosca_template = ToscaTemplate(
                template_id=f"TOSCA_{healing_plan.plan_id}_{int(time.time())}",
                node_id=healing_plan.node_id,
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
            return None

    def determine_node_type(self, node_id: str) -> str:
        """PRESERVED: Determine node type from node ID from Orchestration Agent"""
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

    def build_node_templates(self, node_id: str, node_type: str, healing_actions: List[HealingAction]) -> Dict[str, Any]:
        """ENHANCED: Build TOSCA node templates from healing actions"""
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
                            action.action_type: {
                                'implementation': self.network_templates['healing_action_mappings']
                                .get(action.action_type, {})
                                .get('implementation', 'nokia.implementations.GenericAction'),
                                'inputs': action.parameters
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

    def build_healing_policies_from_actions(self, healing_actions: List[HealingAction]) -> List[Dict[str, Any]]:
        """ENHANCED: Build TOSCA healing policies from healing actions"""
        policies = []

        for i, action in enumerate(healing_actions):
            action_type = action.action_type
            policy_config = self.network_templates['healing_action_mappings'].get(action_type, {})

            policy = {
                f"healing-policy-{i+1}": {
                    'type': policy_config.get('tosca_policy', 'nokia.policies.GenericHealing'),
                    'description': action.description,
                    'properties': {
                        'priority': action.priority,
                        'estimated_duration': action.estimated_duration,
                        'success_probability': action.success_probability,
                        'rollback_enabled': True,
                        'approval_required': action.priority <= 1
                    },
                    'targets': [action.parameters.get('target_node', 'all_nodes')]
                }
            }
            policies.append(policy)

        return policies

    def build_healing_workflows_from_actions(self, healing_actions: List[HealingAction]) -> Dict[str, Any]:
        """ENHANCED: Build TOSCA healing workflows from healing actions"""
        workflow_steps = []

        for i, action in enumerate(healing_actions):
            step = {
                f"step_{i+1}_{action.action_type}": {
                    'target': f"healing-policy-{i+1}",
                    'activities': [
                        {'set_state': 'executing'},
                        {
                            'call_operation': {
                                'operation': f"Nokia.Healing.{action.action_type}",
                                'inputs': action.parameters
                            }
                        },
                        {'set_state': 'completed'}
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

    # **ENHANCED: NS3 integration from healing plan (adapted from Orchestration Agent)**
    async def generate_ns3_integration_plan_from_healing_plan(self, healing_plan: HealingPlan) -> Optional[NS3IntegrationPlan]:
        """ENHANCED: Generate NS3-compatible integration plan from healing plan"""
        try:
            logger.info(f"📊 Generating NS3 integration plan for healing plan {healing_plan.plan_id}...")

            # Build NS3 simulation configuration
            simulation_config = {
                **self.ns3_config['simulation_defaults'],
                'healing_scenario': {
                    'target_node': healing_plan.node_id,
                    'fault_injection_time': 60.0,
                    'healing_start_time': 120.0,
                    'validation_duration': 180.0
                }
            }

            # Generate network topology changes
            topology_changes = self.generate_ns3_topology_changes_from_actions(healing_plan.node_id, healing_plan.healing_actions)

            # Generate routing updates
            routing_updates = self.generate_ns3_routing_updates_from_actions(healing_plan.node_id, healing_plan.healing_actions)

            # Generate configuration changes
            config_changes = self.generate_ns3_config_changes_from_actions(healing_plan.node_id, healing_plan.healing_actions)

            # Generate simulation parameters
            sim_parameters = self.generate_ns3_simulation_parameters_from_healing_plan(healing_plan)

            # Generate validation criteria
            validation_criteria = self.generate_ns3_validation_criteria_from_actions(healing_plan.healing_actions)

            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            ns3_filename = f"ns3_healing_plan_{healing_plan.node_id}_{timestamp}.json"
            ns3_path = self.healing_plans_for_ns3_dir / ns3_filename

            # Create NS3IntegrationPlan object
            ns3_plan = NS3IntegrationPlan(
                plan_id=f"NS3_{healing_plan.plan_id}_{int(time.time())}",
                healing_plan_id=healing_plan.plan_id,
                node_id=healing_plan.node_id,
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
                    'healing_plan_id': healing_plan.plan_id,
                    'target_node': healing_plan.node_id,
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
                'original_healing_plan': {
                    'plan_id': healing_plan.plan_id,
                    'node_id': healing_plan.node_id,
                    'severity': healing_plan.severity,
                    'confidence': healing_plan.confidence,
                    'healing_actions': [
                        {
                            'action_type': action.action_type,
                            'description': action.description,
                            'priority': action.priority,
                            'parameters': action.parameters
                        }
                        for action in healing_plan.healing_actions
                    ]
                },
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
            return None

    def generate_ns3_topology_changes_from_actions(self, node_id: str, healing_actions: List[HealingAction]) -> List[Dict[str, Any]]:
        """ENHANCED: Generate NS3 topology modification commands from healing actions"""
        topology_changes = []

        for action in healing_actions:
            action_type = action.action_type

            if action_type == 'traffic_rerouting':
                topology_changes.append({
                    'command': 'modify_routing_table',
                    'target_node': node_id,
                    'action': 'activate_backup_path',
                    'parameters': {
                        'backup_path_priority': 1,
                        'reroute_percentage': action.parameters.get('reroute_percentage', 50),
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
                        'balancing_algorithm': action.parameters.get('balancing_algorithm', 'round_robin'),
                        'load_threshold': action.parameters.get('load_threshold', 0.8),
                        'rebalancing_interval': 10.0
                    },
                    'validation': {
                        'load_distribution_variance': 0.2,
                        'throughput_improvement': 0.3
                    }
                })

        return topology_changes

    def generate_ns3_routing_updates_from_actions(self, node_id: str, healing_actions: List[HealingAction]) -> List[Dict[str, Any]]:
        """ENHANCED: Generate NS3 routing protocol updates from healing actions"""
        routing_updates = []

        for action in healing_actions:
            if action.action_type in ['traffic_rerouting', 'load_balancing']:
                # Dynamic routing protocol updates
                routing_updates.append({
                    'protocol': 'OLSR',  # OLSR for rural mesh networks
                    'target_node': node_id,
                    'update_type': 'emergency_reroute',
                    'parameters': {
                        'hello_interval': 0.5,  # Faster neighbor detection
                        'tc_interval': 1.0,  # Faster topology updates
                        'neighbor_hold_time': 10.0,
                        'mpr_coverage': 2,  # Redundant multipoint relays
                        'link_quality_threshold': 0.3
                    },
                    'affected_neighbors': self.get_node_neighbors(node_id),
                    'convergence_timeout': 30.0
                })

        return routing_updates

    def generate_ns3_config_changes_from_actions(self, node_id: str, healing_actions: List[HealingAction]) -> List[Dict[str, Any]]:
        """ENHANCED: Generate NS3 configuration changes from healing actions"""
        config_changes = []

        for action in healing_actions:
            action_type = action.action_type

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
                        'cpu_allocation_increase': action.parameters.get('cpu_limit_increase', 20),
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

    def generate_ns3_simulation_parameters_from_healing_plan(self, healing_plan: HealingPlan) -> Dict[str, Any]:
        """ENHANCED: Generate NS3 simulation parameters from healing plan"""
        severity = healing_plan.severity

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
                'animation_file': f"healing_animation_{healing_plan.node_id}.xml",
                'pcap_enabled': True,
                'ascii_trace_enabled': True,
                'flow_monitor_enabled': True,
                'results_directory': f"results/healing_{healing_plan.plan_id}"
            }
        }

    def generate_ns3_validation_criteria_from_actions(self, healing_actions: List[HealingAction]) -> Dict[str, Any]:
        """ENHANCED: Generate NS3 validation criteria from healing actions"""
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
        """PRESERVED: Get neighboring nodes for routing updates from Orchestration Agent"""
        try:
            node_num = int(node_id.split('_')[1])
            if node_num in [0, 1]:  # CORE nodes
                return [f"node_{i:02d}" for i in [2, 3, 4, 5, 6, 7]]
            elif node_num in [5, 7]:  # DIST nodes
                return [f"node_{i:02d}" for i in [0, 1, 8, 9, 10, 20, 21, 22]]
            elif node_num in [20, 25]:  # ACC nodes
                return [f"node_{i:02d}" for i in [5, 7, 18, 19, 23, 24, 26, 27]]
            else:
                return []
        except:
            return []

    def generate_ns3_execution_commands(self, ns3_filename: str) -> List[str]:
        """PRESERVED: Generate NS3 execution commands from Orchestration Agent"""
        return [
            f"# Load healing plan in NS3 simulation:",
            f"# 1. Copy {ns3_filename} to ns3/src/rural-network/examples/",
            f"# 2. Run: ./waf --run 'rural-network-healing --healing-plan={ns3_filename}'",
            f"# 3. Monitor results in ns3/results/healing_validation/",
            f"# 4. Generate reports: python3 scripts/analyze_healing_results.py",
            f"# 5. Visualization: python3 scripts/visualize_healing_performance.py"
        ]

    # **ENHANCED: Deployment configuration from healing plan**
    async def create_deployment_configuration_from_healing_plan(self, healing_plan: HealingPlan, tosca_template: ToscaTemplate) -> Dict[str, Any]:
        """ENHANCED: Create deployment configuration from healing plan"""
        try:
            deployment_config = {
                'deployment_metadata': {
                    'deployment_id': f"DEPLOY_{healing_plan.plan_id}_{int(time.time())}",
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
                    'auto_approve': not healing_plan.requires_approval,
                    'rollback_on_failure': True,
                    'dry_run': False,
                    'validate_before_deploy': True,
                    'notification_endpoints': [
                        'healing-agent@nokia.rural',
                        'orchestration-alerts@nokia.rural'
                    ]
                },
                'resource_requirements': {
                    'compute_resources': self.calculate_compute_requirements_from_healing_plan(healing_plan),
                    'network_resources': self.calculate_network_requirements_from_healing_plan(healing_plan),
                    'storage_resources': self.calculate_storage_requirements_from_healing_plan(healing_plan)
                }
            }

            # Save deployment configuration
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            config_filename = f"deployment_config_{healing_plan.node_id}_{timestamp}.json"
            config_path = self.deployment_configs_dir / config_filename

            with open(config_path, 'w') as f:
                json.dump(deployment_config, f, indent=2, default=str)

            logger.info(f"✅ Deployment configuration created: {config_path}")

            return deployment_config

        except Exception as e:
            logger.error(f"❌ Error creating deployment configuration: {e}")
            raise

    def calculate_compute_requirements_from_healing_plan(self, healing_plan: HealingPlan) -> Dict[str, Any]:
        """ENHANCED: Calculate compute requirements from healing plan"""
        healing_actions = healing_plan.healing_actions
        severity = healing_plan.severity

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

    def calculate_network_requirements_from_healing_plan(self, healing_plan: HealingPlan) -> Dict[str, Any]:
        """ENHANCED: Calculate network requirements from healing plan"""
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

    def calculate_storage_requirements_from_healing_plan(self, healing_plan: HealingPlan) -> Dict[str, Any]:
        """ENHANCED: Calculate storage requirements from healing plan"""
        return {
            'configuration_storage': '50MB',
            'log_storage': '200MB',
            'backup_storage': '100MB',
            'temporary_storage': '50MB',
            'retention_policy': '7_days'
        }

    # **PRESERVED: Orchestration deployment from Orchestration Agent**
    async def execute_orchestration_deployment(self, tosca_template: ToscaTemplate, deployment_config: Dict[str, Any]) -> Dict[str, Any]:
        """PRESERVED: Execute orchestration deployment from Orchestration Agent"""
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
            self.metrics.orchestration_executions += 1
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

    # **PRESERVED: Communication methods from Healing Agent**
    async def send_healing_response_to_calculation_agent(self, anomaly_alert: AnomalyAlert, healing_plan: HealingPlan):
        """PRESERVED: Send healing response back to Calculation Agent from Healing Agent"""
        try:
            response = {
                'message_type': 'healing_response',
                'timestamp': datetime.now().isoformat(),
                'source_agent': 'combined_healing_orchestration_agent',
                'target_agent': 'calculation_agent',
                'original_message_id': anomaly_alert.message_id,
                'anomaly_id': healing_plan.anomaly_id,
                'healing_plan': {
                    'plan_id': healing_plan.plan_id,
                    'node_id': healing_plan.node_id,
                    'severity': healing_plan.severity,
                    'confidence': healing_plan.confidence,
                    'total_estimated_duration': healing_plan.total_estimated_duration,
                    'healing_actions': [
                        {
                            'action_type': action.action_type,
                            'description': action.description,
                            'priority': action.priority,
                            'estimated_duration': action.estimated_duration
                        }
                        for action in healing_plan.healing_actions
                    ]
                },
                'response_metadata': {
                    'processing_time_seconds': time.time() - time.mktime(datetime.fromisoformat(anomaly_alert.detection_timestamp).timetuple()),
                    'confidence': healing_plan.confidence,
                    'requires_approval': healing_plan.requires_approval
                }
            }

            await self.mcp_publisher.send_json(response)
            self.metrics.healing_responses_sent += 1
            logger.info(f"📤 Healing response sent to Calculation Agent: {healing_plan.plan_id}")

        except Exception as e:
            logger.error(f"❌ Failed to send healing response to Calculation Agent: {e}")

    # **ENHANCED: Orchestration status updates**
    async def send_orchestration_status_update(self, plan_id: str, tosca_template: ToscaTemplate,
                                             ns3_plan: NS3IntegrationPlan, execution_result: Optional[Dict[str, Any]]):
        """ENHANCED: Send orchestration status update"""
        try:
            status_update = {
                'message_type': 'orchestration_status',
                'timestamp': datetime.now().isoformat(),
                'source_agent': 'combined_healing_orchestration_agent',
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
                    'successful_deployments': self.metrics.successful_deployments,
                    'end_to_end_completions': self.metrics.end_to_end_completions
                }
            }

            await self.status_publisher.send_json(status_update)
            logger.info(f"📤 Orchestration status update sent for {plan_id}")

        except Exception as e:
            logger.error(f"❌ Failed to send orchestration status update: {e}")

    # **NEW: Complete workflow report generation**
    async def generate_complete_workflow_report(self, anomaly_alert: AnomalyAlert, healing_plan: HealingPlan,
                                              tosca_template: ToscaTemplate, ns3_plan: NS3IntegrationPlan,
                                              execution_result: Optional[Dict[str, Any]]):
        """NEW: Generate comprehensive workflow report"""
        try:
            report = {
                'report_metadata': {
                    'report_id': f"COMPLETE_REPORT_{int(time.time())}",
                    'generated_timestamp': datetime.now().isoformat(),
                    'anomaly_id': anomaly_alert.anomaly_id,
                    'healing_plan_id': healing_plan.plan_id,
                    'node_id': healing_plan.node_id
                },
                'workflow_summary': {
                    'anomaly_alert': {
                        'node_id': anomaly_alert.node_id,
                        'anomaly_score': anomaly_alert.anomaly_score,
                        'severity': anomaly_alert.severity,
                        'detection_timestamp': anomaly_alert.detection_timestamp
                    },
                    'healing_plan': {
                        'plan_id': healing_plan.plan_id,
                        'total_actions': len(healing_plan.healing_actions),
                        'confidence': healing_plan.confidence,
                        'estimated_duration': healing_plan.total_estimated_duration
                    },
                    'tosca_template': {
                        'template_id': tosca_template.template_id,
                        'template_path': tosca_template.file_path,
                        'node_templates_count': len(tosca_template.node_templates)
                    },
                    'ns3_integration': {
                        'plan_id': ns3_plan.plan_id,
                        'integration_path': ns3_plan.file_path,
                        'topology_changes': len(ns3_plan.network_topology_changes),
                        'routing_updates': len(ns3_plan.routing_updates)
                    },
                    'deployment': execution_result if execution_result else {'status': 'not_executed'}
                },
                'combined_metrics': asdict(self.metrics),
                'files_generated': {
                    'healing_plan': f"healing_plans/{healing_plan.plan_id}.json",
                    'tosca_template': tosca_template.file_path,
                    'ns3_integration_plan': ns3_plan.file_path,
                    'deployment_config': f"deployment_configs/deployment_config_{healing_plan.node_id}_*.json"
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
            report_filename = f"complete_workflow_report_{healing_plan.node_id}_{timestamp}.json"
            report_path = self.orchestration_reports_dir / report_filename

            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)

            logger.info(f"📋 Complete workflow report generated: {report_path}")

        except Exception as e:
            logger.error(f"❌ Error generating complete workflow report: {e}")

    # **ENHANCED: Combined performance monitoring**
    async def monitor_combined_performance(self):
        """ENHANCED: Monitor combined agent performance metrics"""
        logger.info("📊 Starting combined performance monitoring...")
        while self.is_running:
            try:
                await asyncio.sleep(60)  # Check every minute

                # Calculate performance metrics
                avg_processing_time = np.mean(self.processing_times) if self.processing_times else 0
                success_rate = (self.metrics.end_to_end_completions / 
                              max(self.metrics.alerts_received, 1)) * 100 if self.metrics.alerts_received > 0 else 0

                # Update average processing time
                self.metrics.avg_processing_time = avg_processing_time

                # Log combined performance summary
                logger.info(f"📊 Combined Agent Performance Summary:")
                logger.info(f" • Alerts Received: {self.metrics.alerts_received}")
                logger.info(f" • Healing Plans Generated: {self.metrics.healing_plans_generated}")
                logger.info(f" • TOSCA Templates Generated: {self.metrics.tosca_templates_generated}")
                logger.info(f" • NS3 Plans Exported: {self.metrics.ns3_plans_exported}")
                logger.info(f" • Orchestration Executions: {self.metrics.orchestration_executions}")
                logger.info(f" • End-to-End Completions: {self.metrics.end_to_end_completions}")
                logger.info(f" • Failed Operations: {self.metrics.failed_operations}")
                logger.info(f" • Avg Processing Time: {avg_processing_time:.2f}s")
                logger.info(f" • Success Rate: {success_rate:.1f}%")
                logger.info(f" • Active Healing Plans: {len(self.active_healing_plans)}")

                # Clean up old processing times (keep last 100)
                if len(self.processing_times) > 100:
                    self.processing_times = self.processing_times[-100:]

            except Exception as e:
                logger.error(f"❌ Error in combined performance monitoring: {e}")

    # **ENHANCED: Combined report generation**
    async def generate_combined_reports(self):
        """ENHANCED: Generate periodic combined reports"""
        logger.info("📋 Starting periodic combined report generation...")
        while self.is_running:
            try:
                await asyncio.sleep(3600)  # Generate report every hour

                combined_report = {
                    'report_timestamp': datetime.now().isoformat(),
                    'reporting_period': '1 hour',
                    'agent_type': 'combined_healing_orchestration',
                    'combined_metrics': asdict(self.metrics),
                    'performance_summary': {
                        'avg_processing_time': self.metrics.avg_processing_time,
                        'end_to_end_success_rate': (
                            (self.metrics.end_to_end_completions /
                             max(self.metrics.alerts_received, 1)) * 100
                        ),
                        'healing_success_rate': (
                            (self.metrics.healing_plans_generated /
                             max(self.metrics.alerts_received, 1)) * 100
                        ),
                        'orchestration_success_rate': (
                            (self.metrics.successful_deployments /
                             max(self.metrics.orchestration_executions, 1)) * 100
                        ),
                        'throughput_per_hour': self.metrics.end_to_end_completions,
                        'error_rate': (
                            (self.metrics.failed_operations /
                             max(self.metrics.alerts_received, 1)) * 100
                        )
                    },
                    'file_generation_summary': {
                        'healing_plans_created': self.metrics.healing_plans_generated,
                        'tosca_templates_generated': self.metrics.tosca_templates_generated,
                        'ns3_plans_exported': self.metrics.ns3_plans_exported,
                        'total_files_created': (
                            self.metrics.healing_plans_generated +
                            self.metrics.tosca_templates_generated +
                            self.metrics.ns3_plans_exported
                        )
                    },
                    'active_items': {
                        'active_healing_plans': len(self.active_healing_plans),
                        'active_orchestrations': len(self.active_orchestrations)
                    }
                }

                # Save combined report
                report_file = self.orchestration_reports_dir / f"combined_periodic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(report_file, 'w') as f:
                    json.dump(combined_report, f, indent=2, default=str)

                logger.info(f"📋 Combined periodic report generated: {report_file}")

            except Exception as e:
                logger.error(f"❌ Error generating combined periodic report: {e}")

    # **PRESERVED: File cleanup from Orchestration Agent**
    async def cleanup_old_files(self):
        """PRESERVED: Cleanup old files periodically from Orchestration Agent"""
        logger.info("🧹 Starting periodic file cleanup...")
        while self.is_running:
            try:
                await asyncio.sleep(86400)  # Cleanup daily

                # Cleanup files older than 7 days
                cutoff_time = time.time() - (7 * 24 * 3600)  # 7 days ago

                directories_to_clean = [
                    self.healing_plans_dir,
                    self.healing_reports_dir,
                    self.tosca_templates_dir,
                    self.ns3_integration_dir,
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

    # **ENHANCED: Combined cleanup**
    async def cleanup(self):
        """ENHANCED: Cleanup resources and connections"""
        try:
            self.is_running = False

            # Close ZeroMQ sockets
            if self.a2a_subscriber:
                self.a2a_subscriber.close()
            if self.mcp_publisher:
                self.mcp_publisher.close()
            if self.status_publisher:
                self.status_publisher.close()
            if self.context:
                self.context.term()

            # Generate final combined report
            final_report = {
                'shutdown_timestamp': datetime.now().isoformat(),
                'agent_type': 'combined_healing_orchestration',
                'final_metrics': asdict(self.metrics),
                'total_active_healing_plans': len(self.active_healing_plans),
                'total_active_orchestrations': len(self.active_orchestrations),
                'avg_processing_time': self.metrics.avg_processing_time,
                'total_files_generated': (
                    self.metrics.healing_plans_generated +
                    self.metrics.tosca_templates_generated +
                    self.metrics.ns3_plans_exported
                ),
                'end_to_end_success_rate': (
                    (self.metrics.end_to_end_completions /
                     max(self.metrics.alerts_received, 1)) * 100
                ) if self.metrics.alerts_received > 0 else 0
            }

            final_report_file = self.orchestration_reports_dir / f"final_combined_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(final_report_file, 'w') as f:
                json.dump(final_report, f, indent=2, default=str)

            logger.info("✅ Combined Healing & Orchestration Agent cleanup completed")
            logger.info(f"📋 Final report saved: {final_report_file}")

        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")


# **MAIN EXECUTION**
async def main():
    """Main execution function for Combined Healing & Orchestration Agent"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize combined agent
    agent = CombinedHealingOrchestrationAgent()

    try:
        print('🏆 Combined Healing & Orchestration Agent starting...')
        print('💻 CPU-OPTIMIZED for 24GB RAM configuration')
        print('🏥 Healing: Gemini AI + Nokia Knowledge Base + Multi-strategy Actions')
        print('🎯 Orchestration: TOSCA Generation + NS3 Integration + Deployment')
        print('🔄 Workflow: Anomaly Alert → Healing Plan → TOSCA → NS3 → Deployment')
        print('👂 Listening: Port 5555 (from Calculation Agent)')
        print('📤 Responding: Port 5556 (to Calculation Agent) + Port 5559 (status)')
        print(f'📁 Healing Plans: {agent.healing_plans_dir}')
        print(f'📁 TOSCA Templates: {agent.tosca_templates_dir}')
        print(f'📁 NS3 Integration: {agent.ns3_integration_dir}')
        print(f'📊 Reports: {agent.orchestration_reports_dir}')
        print('🚀 ITU Competition Ready: All functionalities preserved!')

        await agent.start_combined_agent()

    except KeyboardInterrupt:
        logger.info("🛑 Shutdown requested")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
    finally:
        await agent.cleanup()


if __name__ == '__main__':
    asyncio.run(main())