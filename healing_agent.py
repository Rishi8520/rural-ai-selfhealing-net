import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'  # Hide GPU from TensorFlow
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'   # Reduce TensorFlow logging

import asyncio
import logging
import json
import time
import zmq
import zmq.asyncio
import google.generativeai as genai
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Import your existing healing agent base class
try:
    from healing_agent import HealingAgent
except ImportError:
    # Fallback base class if original doesn't exist
    class HealingAgent:
        def __init__(self, *args, **kwargs):
            self.context = zmq.asyncio.Context()
            self.is_running = False
            pass

logger = logging.getLogger(__name__)

@dataclass
class AnomalyAlert:
    """Structured anomaly alert data"""
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
    """Individual healing action"""
    action_id: str
    action_type: str
    priority: int
    description: str
    parameters: Dict[str, Any]
    estimated_duration: int
    success_probability: float

@dataclass
class HealingPlan:
    """Complete healing plan"""
    plan_id: str
    anomaly_id: str
    node_id: str
    severity: str
    healing_actions: List[HealingAction]
    total_estimated_duration: int
    confidence: float
    requires_approval: bool
    generated_timestamp: str

class EnhancedHealingAgent(HealingAgent):
    """Enhanced Healing Agent with Gemini AI integration and robust communication"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 🤖 Gemini AI Configuration
        self.gemini_api_key = os.getenv('GEMINI_API_KEY', 'YOUR_GEMINI_API_KEY_HERE')
        self.gemini_model = None
        self.initialize_gemini()
        
        # 🔗 Communication Setup
        self.context = zmq.asyncio.Context()
        self.a2a_subscriber = None    # Receive anomaly alerts from Calculation Agent
        self.mcp_publisher = None     # Send healing responses back
        self.orchestrator_publisher = None  # Send to Orchestrator
        
        # 📊 Communication Metrics
        self.comm_metrics = {
            'alerts_received': 0,
            'healing_plans_generated': 0,
            'responses_sent': 0,
            'failed_operations': 0
        }
        
        # 📁 Storage Setup
        self.healing_plans_dir = Path("healing_plans")
        self.healing_reports_dir = Path("healing_reports")
        self.healing_plans_dir.mkdir(exist_ok=True)
        self.healing_reports_dir.mkdir(exist_ok=True)
        
        # 🎯 Nokia Rural Network Knowledge Base
        self.network_knowledge = self.initialize_network_knowledge()
        
        # 🔄 Processing Queue
        self.processing_queue = asyncio.Queue()
        self.active_healing_plans = {}
        
        # ⏱️ Performance Tracking
        self.processing_times = []
        self.success_rates = {}
        
        logger.info("✅ Enhanced Healing Agent initialized")
        logger.info(f"📁 Healing plans directory: {self.healing_plans_dir}")
        logger.info(f"📊 Reports directory: {self.healing_reports_dir}")

    def initialize_gemini(self):
        """Initialize Gemini AI for healing plan generation"""
        try:
            if self.gemini_api_key and self.gemini_api_key != 'YOUR_GEMINI_API_KEY_HERE':
                genai.configure(api_key=self.gemini_api_key)
                self.gemini_model = genai.GenerativeModal('gemini-2.0-flash',)
                logger.info("✅ Gemini AI initialized successfully")
            else:
                logger.warning("⚠️ Gemini API key not provided, using fallback healing generation")
                self.gemini_model = None
        except Exception as e:
            logger.error(f"❌ Gemini AI initialization failed: {e}")
            self.gemini_model = None

    def initialize_network_knowledge(self) -> Dict[str, Any]:
        """Initialize Nokia Rural Network specific knowledge base"""
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

    async def initialize_communication(self):
        """Initialize ZeroMQ communication channels"""
        try:
            # 👂 A2A Subscriber - Receive anomaly alerts from Calculation Agent
            self.a2a_subscriber = self.context.socket(zmq.SUB)
            self.a2a_subscriber.connect("tcp://127.0.0.1:5555")
            self.a2a_subscriber.setsockopt_string(zmq.SUBSCRIBE, "")
            
            # 📤 MCP Publisher - Send healing responses back to Calculation Agent
            self.mcp_publisher = self.context.socket(zmq.PUB)
            self.mcp_publisher.bind("tcp://127.0.0.1:5556")
            
            # 📡 Orchestrator Publisher - Send healing plans to Orchestrator
            self.orchestrator_publisher = self.context.socket(zmq.PUB)
            self.orchestrator_publisher.bind("tcp://127.0.0.1:5558")
            
            logger.info("✅ Enhanced Healing Agent communication initialized")
            logger.info("👂 A2A Subscriber: Port 5555 (from Calculation Agent)")
            logger.info("📤 MCP Publisher: Port 5556 (to Calculation Agent)")
            logger.info("📡 Orchestrator Publisher: Port 5558 (to Orchestrator)")
            
            # Give time for socket binding
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"❌ Communication initialization failed: {e}")
            raise

    async def start_with_enhanced_communication(self):
        """Start Enhanced Healing Agent with full communication setup"""
        logger.info("🚀 Starting Enhanced Healing Agent...")
        
        # Initialize communication
        await self.initialize_communication()
        
        # Start processing tasks
        self.is_running = True
        
        # Create background tasks
        tasks = [
            asyncio.create_task(self.listen_for_anomaly_alerts()),
            asyncio.create_task(self.process_healing_queue()),
            asyncio.create_task(self.monitor_healing_performance()),
            asyncio.create_task(self.generate_periodic_reports())
        ]
        
        logger.info("✅ Enhanced Healing Agent started successfully")
        logger.info("👂 Listening for anomaly alerts...")
        logger.info("🔄 Processing queue active...")
        logger.info("📊 Performance monitoring active...")
        
        try:
            # Wait for all tasks
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("🛑 Shutdown requested")
        finally:
            await self.cleanup()

    async def listen_for_anomaly_alerts(self):
        """Enhanced anomaly alert listener with robust error handling"""
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
                self.comm_metrics['failed_operations'] += 1
                await asyncio.sleep(1)

    async def handle_incoming_anomaly_alert(self, alert_message: Dict[str, Any]):
        """Handle incoming anomaly alert with validation and queuing"""
        try:
            # Parse and validate alert
            anomaly_alert = self.parse_anomaly_alert(alert_message)
            
            if anomaly_alert is None:
                logger.error("❌ Invalid anomaly alert received")
                return
                
            logger.info(f"🚨 Anomaly alert received: {anomaly_alert.anomaly_id}")
            logger.info(f"📍 Node: {anomaly_alert.node_id} | Severity: {anomaly_alert.severity}")
            logger.info(f"📊 Score: {anomaly_alert.anomaly_score:.3f}")
            
            self.comm_metrics['alerts_received'] += 1
            
            # Add to processing queue
            await self.processing_queue.put(anomaly_alert)
            
        except Exception as e:
            logger.error(f"❌ Error handling anomaly alert: {e}")
            self.comm_metrics['failed_operations'] += 1

    def parse_anomaly_alert(self, alert_message: Dict[str, Any]) -> Optional[AnomalyAlert]:
        """Parse and validate incoming anomaly alert"""
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

    async def process_healing_queue(self):
        """Process healing requests from the queue"""
        logger.info("🔄 Starting healing queue processor...")
        
        while self.is_running:
            try:
                # Get anomaly alert from queue (with timeout)
                anomaly_alert = await asyncio.wait_for(
                    self.processing_queue.get(),
                    timeout=5.0
                )
                
                # Process the healing request
                start_time = time.time()
                healing_plan = await self.generate_comprehensive_healing_plan(anomaly_alert)
                processing_time = time.time() - start_time
                
                if healing_plan:
                    # Send healing plan responses
                    await self.send_healing_responses(anomaly_alert, healing_plan)
                    
                    # Track performance
                    self.processing_times.append(processing_time)
                    self.comm_metrics['healing_plans_generated'] += 1
                    
                    logger.info(f"✅ Healing plan generated in {processing_time:.2f}s: {healing_plan.plan_id}")
                else:
                    logger.error(f"❌ Failed to generate healing plan for {anomaly_alert.anomaly_id}")
                    self.comm_metrics['failed_operations'] += 1
                
                # Mark task as done
                self.processing_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"❌ Error processing healing queue: {e}")
                self.comm_metrics['failed_operations'] += 1

    async def generate_comprehensive_healing_plan(self, anomaly_alert: AnomalyAlert) -> Optional[HealingPlan]:
        """Generate comprehensive healing plan using AI and knowledge base"""
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
            
            logger.info(f"✅ Comprehensive healing plan generated: {healing_plan.plan_id}")
            logger.info(f"🔧 Actions: {len(healing_actions)} | Duration: {healing_plan.total_estimated_duration}s")
            logger.info(f"📊 Confidence: {healing_plan.confidence:.2f}")
            
            return healing_plan
            
        except Exception as e:
            logger.error(f"❌ Error generating healing plan: {e}")
            return None

    def analyze_network_context(self, anomaly_alert: AnomalyAlert) -> Dict[str, Any]:
        """Analyze network context from anomaly alert"""
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
        """Generate healing actions based on knowledge base"""
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
        """Generate AI-powered healing actions using Gemini"""
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
        """Build detailed prompt for Gemini AI"""
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
        """Parse Gemini AI response into healing actions"""
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
        """Generate healing actions based on predefined templates"""
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
        """Prioritize and remove duplicate healing actions"""
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
        """Calculate overall confidence for the healing plan"""
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
        """Save healing plan to disk"""
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

    async def send_healing_responses(self, anomaly_alert: AnomalyAlert, healing_plan: HealingPlan):
        """Send healing responses to multiple destinations"""
        try:
            # 1. Send response back to Calculation Agent
            await self.send_healing_response_to_calculation_agent(anomaly_alert, healing_plan)
            
            # 2. Send healing plan to Orchestrator
            await self.send_healing_plan_to_orchestrator(healing_plan)
            
            self.comm_metrics['responses_sent'] += 1
            
        except Exception as e:
            logger.error(f"❌ Error sending healing responses: {e}")
            self.comm_metrics['failed_operations'] += 1

    async def send_healing_response_to_calculation_agent(self, anomaly_alert: AnomalyAlert, healing_plan: HealingPlan):
        """Send healing response back to Calculation Agent"""
        try:
            response = {
                'message_type': 'healing_response',
                'timestamp': datetime.now().isoformat(),
                'source_agent': 'healing_agent',
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
            logger.info(f"📤 Healing response sent to Calculation Agent: {healing_plan.plan_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to send healing response to Calculation Agent: {e}")

    async def send_healing_plan_to_orchestrator(self, healing_plan: HealingPlan):
        """Send healing plan to Orchestrator for execution"""
        try:
            orchestrator_message = {
                'message_type': 'healing_plan',
                'timestamp': datetime.now().isoformat(),
                'source_agent': 'healing_agent',
                'target_agent': 'orchestration_agent',
                'healing_plan_data': {
                    'plan_id': healing_plan.plan_id,
                    'anomaly_id': healing_plan.anomaly_id,
                    'node_id': healing_plan.node_id,
                    'severity': healing_plan.severity,
                    'generated_timestamp': healing_plan.generated_timestamp,
                    'confidence': healing_plan.confidence,
                    'requires_approval': healing_plan.requires_approval,
                    'total_estimated_duration': healing_plan.total_estimated_duration,
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
                },
                'execution_metadata': {
                    'auto_execute': not healing_plan.requires_approval,
                    'priority_level': healing_plan.severity,
                    'estimated_completion_time': (
                        datetime.now().timestamp() + healing_plan.total_estimated_duration
                    )
                }
            }
            
            await self.orchestrator_publisher.send_json(orchestrator_message)
            logger.info(f"📡 Healing plan sent to Orchestrator: {healing_plan.plan_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to send healing plan to Orchestrator: {e}")

    async def monitor_healing_performance(self):
        """Monitor healing agent performance metrics"""
        logger.info("📊 Starting performance monitoring...")
        
        while self.is_running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Calculate performance metrics
                avg_processing_time = np.mean(self.processing_times) if self.processing_times else 0
                success_rate = len([t for t in self.processing_times if t < 300]) / len(self.processing_times) if self.processing_times else 0
                
                # Log performance summary
                logger.info(f"📊 Performance Summary:")
                logger.info(f"   • Alerts Received: {self.comm_metrics['alerts_received']}")
                logger.info(f"   • Healing Plans Generated: {self.comm_metrics['healing_plans_generated']}")
                logger.info(f"   • Responses Sent: {self.comm_metrics['responses_sent']}")
                logger.info(f"   • Failed Operations: {self.comm_metrics['failed_operations']}")
                logger.info(f"   • Avg Processing Time: {avg_processing_time:.2f}s")
                logger.info(f"   • Success Rate: {success_rate:.2%}")
                logger.info(f"   • Active Healing Plans: {len(self.active_healing_plans)}")
                
                # Clean up old processing times (keep last 100)
                if len(self.processing_times) > 100:
                    self.processing_times = self.processing_times[-100:]
                
            except Exception as e:
                logger.error(f"❌ Error in performance monitoring: {e}")

    async def generate_periodic_reports(self):
        """Generate periodic healing reports"""
        logger.info("📋 Starting periodic report generation...")
        
        while self.is_running:
            try:
                await asyncio.sleep(3600)  # Generate report every hour
                
                report = {
                    'report_timestamp': datetime.now().isoformat(),
                    'reporting_period': '1 hour',
                    'communication_metrics': self.comm_metrics.copy(),
                    'performance_metrics': {
                        'avg_processing_time': np.mean(self.processing_times) if self.processing_times else 0,
                        'total_processing_attempts': len(self.processing_times),
                        'active_healing_plans': len(self.active_healing_plans),
                        'success_rate': (
                            (self.comm_metrics['healing_plans_generated'] / 
                             max(self.comm_metrics['alerts_received'], 1)) * 100
                        )
                    },
                    'active_healing_plans': [
                        {
                            'plan_id': plan.plan_id,
                            'node_id': plan.node_id,
                            'severity': plan.severity,
                            'generated_timestamp': plan.generated_timestamp
                        }
                        for plan in self.active_healing_plans.values()
                    ]
                }
                
                # Save report
                report_file = self.healing_reports_dir / f"healing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(report_file, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
                
                logger.info(f"📋 Periodic report generated: {report_file}")
                
            except Exception as e:
                logger.error(f"❌ Error generating periodic report: {e}")

    async def cleanup(self):
        """Cleanup resources and connections"""
        try:
            self.is_running = False
            
            # Close ZeroMQ sockets
            if self.a2a_subscriber:
                self.a2a_subscriber.close()
            if self.mcp_publisher:
                self.mcp_publisher.close()
            if self.orchestrator_publisher:
                self.orchestrator_publisher.close()
            if self.context:
                self.context.term()
            
            # Generate final report
            final_report = {
                'shutdown_timestamp': datetime.now().isoformat(),
                'final_metrics': self.comm_metrics.copy(),
                'total_active_plans': len(self.active_healing_plans),
                'avg_processing_time': np.mean(self.processing_times) if self.processing_times else 0
            }
            
            final_report_file = self.healing_reports_dir / f"final_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(final_report_file, 'w') as f:
                json.dump(final_report, f, indent=2, default=str)
            
            logger.info("✅ Enhanced Healing Agent cleanup completed")
            logger.info(f"📋 Final report saved: {final_report_file}")
            
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")

# Main execution function
async def main():
    """Main execution function for Enhanced Healing Agent"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize agent
    agent = EnhancedHealingAgent()
    
    try:
        print('🏥 Enhanced Healing Agent starting...')
        print('👂 Listening for anomaly alerts from Calculation Agent')
        print('📤 Ready to send healing plans to Orchestrator')
        print('🤖 AI-powered healing with Nokia rural network knowledge')
        print(f'📁 Healing plans: {agent.healing_plans_dir}')
        print(f'📊 Reports: {agent.healing_reports_dir}')
        
        await agent.start_with_enhanced_communication()
        
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown requested")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
    finally:
        await agent.cleanup()

if __name__ == '__main__':
    asyncio.run(main())