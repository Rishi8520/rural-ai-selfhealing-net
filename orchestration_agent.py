"""
Nokia Build-a-thon: AI Self-Healing Network Orchestrator Agent
Complete orchestration system for multi-agent coordination, healing workflows, and NS3 integration
"""
import asyncio
import json
import logging
import time
import os
import sys
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
import threading
from collections import defaultdict, deque
import statistics

# ZeroMQ for inter-agent communication
import zmq.asyncio

# Data processing and analysis
import numpy as np
import pandas as pd

# Environment and configuration management
from dotenv import load_dotenv

# Advanced monitoring and metrics
try:
    import psutil
except ImportError:
    psutil = None
    logging.warning("psutil not available - system monitoring limited")

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('orchestrator_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants and Configuration
ORCHESTRATOR_CONFIG_FILE = "orchestrator_config.json"
HEALING_WORKFLOW_LOG = "healing_workflow_log.json"
NETWORK_STATE_FILE = "network_state_snapshot.json"
PERFORMANCE_METRICS_FILE = "orchestrator_performance_metrics.json"

# ZeroMQ Communication Addresses
HEAL_ORCH_PULL_ADDRESS = "tcp://127.0.0.1:5558"  # Receives healing plans from Healing Agent
ORCH_MCP_PUSH_ADDRESS = "tcp://127.0.0.1:5559"   # Sends reports to MCP Agent
ORCH_NS3_CONTROL_ADDRESS = "tcp://127.0.0.1:5560"  # Controls NS3 simulation
ORCH_STATUS_PUB_ADDRESS = "tcp://127.0.0.1:5561"   # Publishes status updates

class WorkflowStatus(Enum):
    """Enumeration for healing workflow statuses"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

class HealingStrategy(Enum):
    """Types of healing strategies available"""
    TRAFFIC_REROUTING = "traffic_rerouting"
    POWER_STABILIZATION = "power_stabilization"
    FIBER_REPAIR = "fiber_repair"
    NODE_RESTART = "node_restart"
    LOAD_BALANCING = "load_balancing"
    REDUNDANCY_ACTIVATION = "redundancy_activation"
    CONFIGURATION_ROLLBACK = "configuration_rollback"
    EMERGENCY_ISOLATION = "emergency_isolation"

@dataclass
class NetworkTopology:
    """Network topology information"""
    nodes: Dict[str, Dict[str, Any]]
    links: List[Dict[str, Any]]
    core_nodes: List[str]
    distribution_nodes: List[str]
    access_nodes: List[str]
    last_updated: datetime

@dataclass
class HealingWorkflowSpec:
    """Specification for a healing workflow"""
    workflow_id: str
    node_id: str
    strategy: HealingStrategy
    priority: int  # 1-5, where 1 is highest priority
    estimated_duration: float  # seconds
    prerequisites: List[str]
    success_criteria: Dict[str, Any]
    rollback_plan: Optional[str]
    created_at: datetime
    timeout: float = 300.0  # 5 minutes default

@dataclass
class WorkflowExecution:
    """Runtime execution state of a healing workflow"""
    spec: HealingWorkflowSpec
    status: WorkflowStatus
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    progress_percentage: float
    current_step: str
    steps_completed: List[str]
    error_message: Optional[str]
    metrics: Dict[str, Any]
    healing_effectiveness: float = 0.0

@dataclass
class OrchestrationResult:
    """Result of orchestration actions"""
    workflow_id: str
    success: bool
    execution_time: float
    healing_effectiveness: float
    network_impact: Dict[str, Any]
    lessons_learned: List[str]
    recommended_improvements: List[str]

class NetworkStateManager:
    """Manages real-time network state and topology"""
    
    def __init__(self):
        self.topology: Optional[NetworkTopology] = None
        self.node_states: Dict[str, Dict[str, Any]] = {}
        self.link_states: Dict[str, Dict[str, Any]] = {}
        self.state_history: deque = deque(maxlen=1000)
        self.last_update: Optional[datetime] = None
        
    async def update_topology(self, topology_data: Dict[str, Any]):
        """Update network topology from NS3 or configuration"""
        try:
            self.topology = NetworkTopology(
                nodes=topology_data.get('nodes', {}),
                links=topology_data.get('links', []),
                core_nodes=topology_data.get('core_nodes', []),
                distribution_nodes=topology_data.get('distribution_nodes', []),
                access_nodes=topology_data.get('access_nodes', []),
                last_updated=datetime.now()
            )
            logger.info(f"Network topology updated: {len(self.topology.nodes)} nodes, {len(self.topology.links)} links")
        except Exception as e:
            logger.error(f"Error updating network topology: {e}")
    
    async def update_node_state(self, node_id: str, state_data: Dict[str, Any]):
        """Update individual node state"""
        self.node_states[node_id] = {
            **state_data,
            'last_updated': datetime.now(),
            'update_count': self.node_states.get(node_id, {}).get('update_count', 0) + 1
        }
        
        # Store in history
        self.state_history.append({
            'timestamp': datetime.now(),
            'node_id': node_id,
            'state': state_data.copy()
        })
        
        self.last_update = datetime.now()
    
    def get_network_health_summary(self) -> Dict[str, Any]:
        """Generate network health summary"""
        if not self.node_states:
            return {'status': 'unknown', 'reason': 'no_data'}
        
        total_nodes = len(self.node_states)
        operational_nodes = sum(1 for state in self.node_states.values() 
                               if state.get('operational', False))
        
        health_percentage = (operational_nodes / total_nodes) * 100 if total_nodes > 0 else 0
        
        return {
            'status': 'healthy' if health_percentage >= 95 else 
                     'degraded' if health_percentage >= 80 else 'critical',
            'health_percentage': health_percentage,
            'total_nodes': total_nodes,
            'operational_nodes': operational_nodes,
            'last_update': self.last_update.isoformat() if self.last_update else None
        }

class HealingWorkflowEngine:
    """Advanced workflow engine for orchestrating healing actions"""
    
    def __init__(self, network_state_manager: NetworkStateManager):
        self.network_state = network_state_manager
        self.active_workflows: Dict[str, WorkflowExecution] = {}
        self.workflow_queue: List[HealingWorkflowSpec] = []
        self.completed_workflows: List[WorkflowExecution] = []
        self.workflow_history: deque = deque(maxlen=500)
        self.max_concurrent_workflows = 5
        
    def create_workflow_spec(self, healing_action: Dict[str, Any]) -> HealingWorkflowSpec:
        """Create workflow specification from healing agent recommendation"""
        node_id = healing_action.get('node_id', 'unknown')
        action_description = healing_action.get('action', '')
        
        # Determine strategy based on action description
        strategy = self._determine_strategy(action_description)
        priority = self._calculate_priority(healing_action)
        
        workflow_id = f"healing_{node_id}_{int(time.time())}"
        
        return HealingWorkflowSpec(
            workflow_id=workflow_id,
            node_id=node_id,
            strategy=strategy,
            priority=priority,
            estimated_duration=self._estimate_duration(strategy),
            prerequisites=self._get_prerequisites(strategy, node_id),
            success_criteria=self._define_success_criteria(strategy, node_id),
            rollback_plan=self._create_rollback_plan(strategy, node_id),
            created_at=datetime.now(),
            timeout=self._calculate_timeout(strategy)
        )
    
    def _determine_strategy(self, action_description: str) -> HealingStrategy:
        """Determine healing strategy from action description"""
        action_lower = action_description.lower()
        
        if any(keyword in action_lower for keyword in ['route', 'path', 'traffic']):
            return HealingStrategy.TRAFFIC_REROUTING
        elif any(keyword in action_lower for keyword in ['power', 'voltage', 'energy']):
            return HealingStrategy.POWER_STABILIZATION
        elif any(keyword in action_lower for keyword in ['fiber', 'cable', 'link']):
            return HealingStrategy.FIBER_REPAIR
        elif any(keyword in action_lower for keyword in ['restart', 'reboot', 'reset']):
            return HealingStrategy.NODE_RESTART
        elif any(keyword in action_lower for keyword in ['load', 'balance', 'distribute']):
            return HealingStrategy.LOAD_BALANCING
        elif any(keyword in action_lower for keyword in ['redundancy', 'backup', 'failover']):
            return HealingStrategy.REDUNDANCY_ACTIVATION
        elif any(keyword in action_lower for keyword in ['config', 'rollback', 'revert']):
            return HealingStrategy.CONFIGURATION_ROLLBACK
        elif any(keyword in action_lower for keyword in ['isolate', 'emergency', 'disconnect']):
            return HealingStrategy.EMERGENCY_ISOLATION
        else:
            return HealingStrategy.NODE_RESTART  # Default strategy
    
    def _calculate_priority(self, healing_action: Dict[str, Any]) -> int:
        """Calculate workflow priority (1=highest, 5=lowest)"""
        severity = healing_action.get('severity_classification', 'Medium')
        node_type = healing_action.get('node_type', 'access')
        
        if severity == 'Critical':
            return 1
        elif severity == 'High':
            return 2 if node_type == 'core' else 3
        elif severity == 'Medium':
            return 3 if node_type == 'core' else 4
        else:
            return 5
    
    def _estimate_duration(self, strategy: HealingStrategy) -> float:
        """Estimate workflow duration in seconds"""
        duration_map = {
            HealingStrategy.TRAFFIC_REROUTING: 30.0,
            HealingStrategy.POWER_STABILIZATION: 60.0,
            HealingStrategy.FIBER_REPAIR: 300.0,  # 5 minutes
            HealingStrategy.NODE_RESTART: 45.0,
            HealingStrategy.LOAD_BALANCING: 25.0,
            HealingStrategy.REDUNDANCY_ACTIVATION: 20.0,
            HealingStrategy.CONFIGURATION_ROLLBACK: 15.0,
            HealingStrategy.EMERGENCY_ISOLATION: 10.0
        }
        return duration_map.get(strategy, 60.0)
    
    def _get_prerequisites(self, strategy: HealingStrategy, node_id: str) -> List[str]:
        """Get prerequisites for the healing strategy"""
        prereq_map = {
            HealingStrategy.TRAFFIC_REROUTING: [f"verify_alternate_paths_{node_id}"],
            HealingStrategy.POWER_STABILIZATION: [f"check_power_source_{node_id}"],
            HealingStrategy.FIBER_REPAIR: [f"isolate_fiber_link_{node_id}"],
            HealingStrategy.NODE_RESTART: [f"save_node_config_{node_id}"],
            HealingStrategy.LOAD_BALANCING: [f"analyze_current_load_{node_id}"],
            HealingStrategy.REDUNDANCY_ACTIVATION: [f"verify_backup_systems_{node_id}"],
            HealingStrategy.CONFIGURATION_ROLLBACK: [f"backup_current_config_{node_id}"],
            HealingStrategy.EMERGENCY_ISOLATION: []  # No prerequisites for emergency
        }
        return prereq_map.get(strategy, [])
    
    def _define_success_criteria(self, strategy: HealingStrategy, node_id: str) -> Dict[str, Any]:
        """Define success criteria for workflow completion"""
        return {
            'node_operational': True,
            'connectivity_restored': True,
            'performance_threshold': 0.8,
            'error_rate_below': 0.01,
            'validation_time': 30.0
        }
    
    def _create_rollback_plan(self, strategy: HealingStrategy, node_id: str) -> str:
        """Create rollback plan for the strategy"""
        rollback_map = {
            HealingStrategy.TRAFFIC_REROUTING: f"restore_original_routes_{node_id}",
            HealingStrategy.POWER_STABILIZATION: f"reset_power_configuration_{node_id}",
            HealingStrategy.FIBER_REPAIR: f"restore_backup_link_{node_id}",
            HealingStrategy.NODE_RESTART: f"restore_previous_state_{node_id}",
            HealingStrategy.LOAD_BALANCING: f"restore_load_distribution_{node_id}",
            HealingStrategy.REDUNDANCY_ACTIVATION: f"deactivate_redundancy_{node_id}",
            HealingStrategy.CONFIGURATION_ROLLBACK: f"restore_working_config_{node_id}",
            HealingStrategy.EMERGENCY_ISOLATION: f"reconnect_node_{node_id}"
        }
        return rollback_map.get(strategy, f"manual_intervention_{node_id}")
    
    def _calculate_timeout(self, strategy: HealingStrategy) -> float:
        """Calculate workflow timeout"""
        return self._estimate_duration(strategy) * 3  # 3x estimated duration
    
    async def queue_workflow(self, workflow_spec: HealingWorkflowSpec):
        """Add workflow to execution queue"""
        self.workflow_queue.append(workflow_spec)
        self.workflow_queue.sort(key=lambda w: w.priority)  # Sort by priority
        logger.info(f"Workflow queued: {workflow_spec.workflow_id} (Priority: {workflow_spec.priority})")
    
    async def execute_next_workflow(self) -> Optional[WorkflowExecution]:
        """Execute the next workflow in queue"""
        if not self.workflow_queue or len(self.active_workflows) >= self.max_concurrent_workflows:
            return None
        
        workflow_spec = self.workflow_queue.pop(0)
        execution = WorkflowExecution(
            spec=workflow_spec,
            status=WorkflowStatus.PENDING,
            started_at=None,
            completed_at=None,
            progress_percentage=0.0,
            current_step="initializing",
            steps_completed=[],
            error_message=None,
            metrics={}
        )
        
        self.active_workflows[workflow_spec.workflow_id] = execution
        
        # Start execution task
        asyncio.create_task(self._execute_workflow(execution))
        
        return execution
    
    async def _execute_workflow(self, execution: WorkflowExecution):
        """Execute a healing workflow"""
        workflow_id = execution.spec.workflow_id
        logger.info(f"Starting workflow execution: {workflow_id}")
        
        try:
            execution.status = WorkflowStatus.IN_PROGRESS
            execution.started_at = datetime.now()
            execution.current_step = "prerequisite_check"
            
            # Step 1: Prerequisites
            await self._execute_prerequisites(execution)
            execution.progress_percentage = 20.0
            execution.steps_completed.append("prerequisites")
            
            # Step 2: Strategy Implementation
            execution.current_step = "strategy_implementation"
            await self._implement_strategy(execution)
            execution.progress_percentage = 60.0
            execution.steps_completed.append("implementation")
            
            # Step 3: Validation
            execution.current_step = "validation"
            success = await self._validate_healing(execution)
            execution.progress_percentage = 90.0
            execution.steps_completed.append("validation")
            
            # Step 4: Completion
            execution.current_step = "completion"
            if success:
                execution.status = WorkflowStatus.COMPLETED
                execution.healing_effectiveness = await self._calculate_effectiveness(execution)
                logger.info(f"Workflow completed successfully: {workflow_id}")
            else:
                execution.status = WorkflowStatus.FAILED
                execution.error_message = "Validation failed"
                logger.warning(f"Workflow failed validation: {workflow_id}")
            
            execution.progress_percentage = 100.0
            execution.completed_at = datetime.now()
            
        except asyncio.TimeoutError:
            execution.status = WorkflowStatus.TIMEOUT
            execution.error_message = "Workflow timed out"
            logger.error(f"Workflow timed out: {workflow_id}")
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error_message = str(e)
            logger.error(f"Workflow failed with error: {workflow_id} - {e}")
        finally:
            # Move to completed workflows
            if workflow_id in self.active_workflows:
                self.completed_workflows.append(self.active_workflows.pop(workflow_id))
                self.workflow_history.append(execution)
    
    async def _execute_prerequisites(self, execution: WorkflowExecution):
        """Execute workflow prerequisites"""
        for prereq in execution.spec.prerequisites:
            logger.debug(f"Executing prerequisite: {prereq}")
            # Simulate prerequisite execution
            await asyncio.sleep(1.0)
    
    async def _implement_strategy(self, execution: WorkflowExecution):
        """Implement the healing strategy"""
        strategy = execution.spec.strategy
        node_id = execution.spec.node_id
        
        logger.info(f"Implementing strategy {strategy.value} for node {node_id}")
        
        # Simulate strategy implementation based on type
        if strategy == HealingStrategy.TRAFFIC_REROUTING:
            await self._implement_traffic_rerouting(execution)
        elif strategy == HealingStrategy.POWER_STABILIZATION:
            await self._implement_power_stabilization(execution)
        elif strategy == HealingStrategy.NODE_RESTART:
            await self._implement_node_restart(execution)
        # Add other strategies as needed
        else:
            # Default implementation
            await asyncio.sleep(execution.spec.estimated_duration)
    
    async def _implement_traffic_rerouting(self, execution: WorkflowExecution):
        """Implement traffic rerouting strategy"""
        node_id = execution.spec.node_id
        logger.info(f"Rerouting traffic around node {node_id}")
        
        # Simulate rerouting steps
        steps = [
            "analyzing_current_routes",
            "identifying_alternate_paths", 
            "calculating_optimal_routes",
            "updating_routing_tables",
            "verifying_connectivity"
        ]
        
        for step in steps:
            execution.current_step = step
            await asyncio.sleep(execution.spec.estimated_duration / len(steps))
            logger.debug(f"Traffic rerouting: {step} completed for {node_id}")
    
    async def _implement_power_stabilization(self, execution: WorkflowExecution):
        """Implement power stabilization strategy"""
        node_id = execution.spec.node_id
        logger.info(f"Stabilizing power for node {node_id}")
        
        # Simulate power stabilization
        await asyncio.sleep(execution.spec.estimated_duration)
    
    async def _implement_node_restart(self, execution: WorkflowExecution):
        """Implement node restart strategy"""
        node_id = execution.spec.node_id
        logger.info(f"Restarting node {node_id}")
        
        # Simulate restart process
        await asyncio.sleep(execution.spec.estimated_duration)
    
    async def _validate_healing(self, execution: WorkflowExecution) -> bool:
        """Validate that healing was successful"""
        node_id = execution.spec.node_id
        criteria = execution.spec.success_criteria
        
        # Check if node is operational
        node_state = self.network_state.node_states.get(node_id, {})
        is_operational = node_state.get('operational', False)
        
        # Simulate additional validation checks
        await asyncio.sleep(criteria.get('validation_time', 30.0))
        
        # For simulation, assume 85% success rate
        return is_operational and (time.time() % 10 < 8.5)
    
    async def _calculate_effectiveness(self, execution: WorkflowExecution) -> float:
        """Calculate healing effectiveness (0.0 to 1.0)"""
        # Simplified effectiveness calculation
        if execution.status == WorkflowStatus.COMPLETED:
            base_effectiveness = 0.8
            priority_bonus = (6 - execution.spec.priority) * 0.05
            return min(1.0, base_effectiveness + priority_bonus)
        return 0.0

class OrchestrationAgent:
    """Main Orchestration Agent for coordinating multi-agent healing workflows"""
    
    def __init__(self):
        self.config = self.load_config()
        self.network_state = NetworkStateManager()
        self.workflow_engine = HealingWorkflowEngine(self.network_state)
        
        # ZeroMQ Setup
        self.context = zmq.asyncio.Context()
        self.healing_subscriber = None
        self.mcp_publisher = None
        self.ns3_controller = None
        self.status_publisher = None
        
        # Runtime state
        self.is_running = False
        self.orchestration_metrics = {
            'workflows_executed': 0,
            'workflows_successful': 0,
            'workflows_failed': 0,
            'average_healing_time': 0.0,
            'average_effectiveness': 0.0,
            'start_time': None
        }
        
        # Performance monitoring
        self.performance_history = deque(maxlen=1000)
        
        logger.info("Orchestration Agent initialized")
    
    def load_config(self) -> Dict[str, Any]:
        """Load orchestrator configuration"""
        try:
            with open(ORCHESTRATOR_CONFIG_FILE, 'r') as f:
                config = json.load(f)
            logger.info(f"Configuration loaded from {ORCHESTRATOR_CONFIG_FILE}")
            return config
        except FileNotFoundError:
            logger.warning(f"Configuration file {ORCHESTRATOR_CONFIG_FILE} not found. Using defaults.")
            return self.get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "orchestration": {
                "max_concurrent_workflows": 5,
                "workflow_timeout": 300.0,
                "health_check_interval": 10.0,
                "performance_monitoring": True
            },
            "communication": {
                "healing_subscriber_address": HEAL_ORCH_PULL_ADDRESS,
                "mcp_publisher_address": ORCH_MCP_PUSH_ADDRESS,
                "ns3_controller_address": ORCH_NS3_CONTROL_ADDRESS,
                "status_publisher_address": ORCH_STATUS_PUB_ADDRESS
            },
            "network": {
                "total_nodes": 50,
                "core_nodes": ["node_00", "node_01", "node_02", "node_03", "node_04"],
                "distribution_nodes": [f"node_{i:02d}" for i in range(5, 20)],
                "access_nodes": [f"node_{i:02d}" for i in range(20, 50)]
            },
            "healing": {
                "priority_levels": 5,
                "effectiveness_threshold": 0.7,
                "automatic_rollback": True,
                "learning_enabled": True
            },
            "reporting": {
                "nokia_integration": True,
                "real_time_dashboard": True,
                "sla_monitoring": True,
                "performance_analytics": True
            }
        }
    
    async def initialize_communication(self):
        """Initialize ZeroMQ communication sockets"""
        try:
            # Healing Agent subscriber (PULL from Healing Agent)
            self.healing_subscriber = self.context.socket(zmq.PULL)
            self.healing_subscriber.bind(self.config['communication']['healing_subscriber_address'])
            logger.info(f"Healing subscriber bound to {self.config['communication']['healing_subscriber_address']}")
            
            # MCP Agent publisher (PUSH to MCP Agent)
            self.mcp_publisher = self.context.socket(zmq.PUSH)
            self.mcp_publisher.bind(self.config['communication']['mcp_publisher_address'])
            logger.info(f"MCP publisher bound to {self.config['communication']['mcp_publisher_address']}")
            
            # NS3 controller (for simulation control)
            self.ns3_controller = self.context.socket(zmq.REQ)
            self.ns3_controller.bind(self.config['communication']['ns3_controller_address'])
            logger.info(f"NS3 controller bound to {self.config['communication']['ns3_controller_address']}")
            
            # Status publisher (for real-time updates)
            self.status_publisher = self.context.socket(zmq.PUB)
            self.status_publisher.bind(self.config['communication']['status_publisher_address'])
            logger.info(f"Status publisher bound to {self.config['communication']['status_publisher_address']}")
            
        except Exception as e:
            logger.error(f"Error initializing communication: {e}")
            raise
    
    async def initialize_network_topology(self):
        """Initialize network topology from configuration"""
        topology_data = {
            'nodes': {node_id: {'type': 'core', 'id': node_id} 
                     for node_id in self.config['network']['core_nodes']},
            'links': [],
            'core_nodes': self.config['network']['core_nodes'],
            'distribution_nodes': self.config['network']['distribution_nodes'],
            'access_nodes': self.config['network']['access_nodes']
        }
        
        # Add distribution and access nodes
        for node_id in self.config['network']['distribution_nodes']:
            topology_data['nodes'][node_id] = {'type': 'distribution', 'id': node_id}
        
        for node_id in self.config['network']['access_nodes']:
            topology_data['nodes'][node_id] = {'type': 'access', 'id': node_id}
        
        await self.network_state.update_topology(topology_data)
        logger.info("Network topology initialized")
    
    async def healing_message_loop(self):
        """Main loop for processing healing messages"""
        logger.info("Starting healing message processing loop...")
        
        while self.is_running:
            try:
                # Receive healing action from Healing Agent
                message = await asyncio.wait_for(
                    self.healing_subscriber.recv_json(), 
                    timeout=1.0
                )
                
                logger.info(f"Received healing message: {message.get('node_id', 'unknown')}")
                
                # Create workflow specification
                workflow_spec = self.workflow_engine.create_workflow_spec(message)
                
                # Queue workflow for execution
                await self.workflow_engine.queue_workflow(workflow_spec)
                
                # Update metrics
                self.orchestration_metrics['workflows_executed'] += 1
                
                # Send acknowledgment to MCP
                await self.send_workflow_status_to_mcp(workflow_spec.workflow_id, "queued", message)
                
            except asyncio.TimeoutError:
                # No message received, continue
                continue
            except Exception as e:
                logger.error(f"Error processing healing message: {e}")
                await asyncio.sleep(1.0)
    
    async def workflow_execution_loop(self):
        """Main loop for executing workflows"""
        logger.info("Starting workflow execution loop...")
        
        while self.is_running:
            try:
                # Execute next workflow if capacity available
                execution = await self.workflow_engine.execute_next_workflow()
                
                if execution:
                    logger.info(f"Started workflow execution: {execution.spec.workflow_id}")
                    await self.send_workflow_status_to_mcp(
                        execution.spec.workflow_id, 
                        "started", 
                        asdict(execution.spec)
                    )
                
                # Check for completed workflows
                await self.process_completed_workflows()
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error in workflow execution loop: {e}")
                await asyncio.sleep(1.0)
    
    async def process_completed_workflows(self):
        """Process and report completed workflows"""
        for execution in list(self.workflow_engine.completed_workflows):
            if execution.completed_at:
                # Update metrics
                if execution.status == WorkflowStatus.COMPLETED:
                    self.orchestration_metrics['workflows_successful'] += 1
                else:
                    self.orchestration_metrics['workflows_failed'] += 1
                
                # Calculate performance metrics
                execution_time = (execution.completed_at - execution.started_at).total_seconds()
                self.update_performance_metrics(execution, execution_time)
                
                # Send completion report to MCP
                await self.send_completion_report_to_mcp(execution)
                
                # Publish status update
                await self.publish_status_update(execution)
                
                # Remove from completed list (already in history)
                self.workflow_engine.completed_workflows.remove(execution)
    
    def update_performance_metrics(self, execution: WorkflowExecution, execution_time: float):
        """Update orchestration performance metrics"""
        # Update averages
        total_workflows = self.orchestration_metrics['workflows_successful'] + self.orchestration_metrics['workflows_failed']
        
        if total_workflows > 0:
            # Update average healing time
            current_avg_time = self.orchestration_metrics['average_healing_time']
            self.orchestration_metrics['average_healing_time'] = (
                (current_avg_time * (total_workflows - 1) + execution_time) / total_workflows
            )
            
            # Update average effectiveness
            current_avg_eff = self.orchestration_metrics['average_effectiveness']
            self.orchestration_metrics['average_effectiveness'] = (
                (current_avg_eff * (total_workflows - 1) + execution.healing_effectiveness) / total_workflows
            )
        
        # Store in performance history
        self.performance_history.append({
            'timestamp': datetime.now(),
            'workflow_id': execution.spec.workflow_id,
            'execution_time': execution_time,
            'effectiveness': execution.healing_effectiveness,
            'strategy': execution.spec.strategy.value,
            'node_id': execution.spec.node_id
        })
    
    async def send_workflow_status_to_mcp(self, workflow_id: str, status: str, data: Dict[str, Any]):
        """Send workflow status update to MCP Agent"""
        try:
            message = {
                'timestamp': datetime.now().isoformat(),
                'source': 'OrchestrationAgent',
                'type': 'workflow_status',
                'workflow_id': workflow_id,
                'status': status,
                'data': data
            }
            
            await self.mcp_publisher.send_json(message)
            logger.debug(f"Sent workflow status to MCP: {workflow_id} - {status}")
            
        except Exception as e:
            logger.error(f"Error sending workflow status to MCP: {e}")
    
    async def send_completion_report_to_mcp(self, execution: WorkflowExecution):
        """Send detailed completion report to MCP Agent"""
        try:
            execution_time = (execution.completed_at - execution.started_at).total_seconds()
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'source': 'OrchestrationAgent',
                'type': 'workflow_completion_report',
                'workflow_id': execution.spec.workflow_id,
                'node_id': execution.spec.node_id,
                'strategy': execution.spec.strategy.value,
                'status': execution.status.value,
                'execution_time': execution_time,
                'healing_effectiveness': execution.healing_effectiveness,
                'steps_completed': execution.steps_completed,
                'error_message': execution.error_message,
                'network_impact': self.calculate_network_impact(execution),
                'performance_metrics': self.orchestration_metrics.copy()
            }
            
            await self.mcp_publisher.send_json(report)
            logger.info(f"Sent completion report to MCP: {execution.spec.workflow_id}")
            
        except Exception as e:
            logger.error(f"Error sending completion report to MCP: {e}")
    
    def calculate_network_impact(self, execution: WorkflowExecution) -> Dict[str, Any]:
        """Calculate the impact of workflow on network performance"""
        node_id = execution.spec.node_id
        
        # Get current network health
        health_summary = self.network_state.get_network_health_summary()
        
        # Simulate impact calculation
        impact = {
            'affected_node': node_id,
            'healing_strategy': execution.spec.strategy.value,
            'network_health_improvement': execution.healing_effectiveness * 10,  # percentage
            'connectivity_restored': execution.status == WorkflowStatus.COMPLETED,
            'performance_improvement': execution.healing_effectiveness * 100,  # percentage
            'downtime_prevented': execution.healing_effectiveness * 60,  # minutes
        }
        
        return impact
    
    async def publish_status_update(self, execution: WorkflowExecution):
        """Publish real-time status update"""
        try:
            status_update = {
                'timestamp': datetime.now().isoformat(),
                'type': 'orchestration_status',
                'workflow_id': execution.spec.workflow_id,
                'node_id': execution.spec.node_id,
                'status': execution.status.value,
                'progress': execution.progress_percentage,
                'healing_effectiveness': execution.healing_effectiveness,
                'network_health': self.network_state.get_network_health_summary()
            }
            
            await self.status_publisher.send_json(status_update)
            
        except Exception as e:
            logger.error(f"Error publishing status update: {e}")
    
    async def health_monitoring_loop(self):
        """Monitor overall system health and performance"""
        logger.info("Starting health monitoring loop...")
        
        while self.is_running:
            try:
                # Collect system metrics
                system_metrics = self.collect_system_metrics()
                
                # Generate health report
                health_report = await self.generate_health_report()
                
                # Send to MCP for Nokia reporting
                await self.send_health_report_to_mcp(health_report)
                
                # Save performance metrics
                await self.save_performance_metrics()
                
                # Wait for next health check
                await asyncio.sleep(self.config['orchestration']['health_check_interval'])
                
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(10.0)
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system performance metrics"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'orchestration_metrics': self.orchestration_metrics.copy(),
            'active_workflows': len(self.workflow_engine.active_workflows),
            'queued_workflows': len(self.workflow_engine.workflow_queue),
            'completed_workflows': len(self.workflow_engine.completed_workflows)
        }
        
        # Add system resource metrics if available
        if psutil:
            metrics.update({
                'cpu_usage': psutil.cpu_percent(),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent
            })
        
        return metrics
    
    async def generate_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        network_health = self.network_state.get_network_health_summary()
        system_metrics = self.collect_system_metrics()
        
        # Calculate success rate
        total_workflows = (self.orchestration_metrics['workflows_successful'] + 
                          self.orchestration_metrics['workflows_failed'])
        success_rate = (self.orchestration_metrics['workflows_successful'] / total_workflows * 100 
                       if total_workflows > 0 else 0.0)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'source': 'OrchestrationAgent',
            'type': 'health_report',
            'network_health': network_health,
            'system_metrics': system_metrics,
            'orchestration_performance': {
                'total_workflows': total_workflows,
                'success_rate': success_rate,
                'average_healing_time': self.orchestration_metrics['average_healing_time'],
                'average_effectiveness': self.orchestration_metrics['average_effectiveness']
            },
            'recommendations': self.generate_recommendations()
        }
        
        return report
    
    def generate_recommendations(self) -> List[str]:
        """Generate operational recommendations based on performance"""
        recommendations = []
        
        # Analyze success rate
        total_workflows = (self.orchestration_metrics['workflows_successful'] + 
                          self.orchestration_metrics['workflows_failed'])
        if total_workflows > 0:
            success_rate = self.orchestration_metrics['workflows_successful'] / total_workflows
            
            if success_rate < 0.8:
                recommendations.append("Review healing strategies - success rate below 80%")
            if self.orchestration_metrics['average_healing_time'] > 120:
                recommendations.append("Optimize workflow execution - healing time above 2 minutes")
            if self.orchestration_metrics['average_effectiveness'] < 0.7:
                recommendations.append("Improve healing effectiveness - below 70% threshold")
        
        # Analyze queue length
        if len(self.workflow_engine.workflow_queue) > 10:
            recommendations.append("Consider increasing concurrent workflow capacity")
        
        # Network health recommendations
        network_health = self.network_state.get_network_health_summary()
        if network_health['health_percentage'] < 90:
            recommendations.append("Network health degraded - investigate root causes")
        
        return recommendations
    
    async def send_health_report_to_mcp(self, health_report: Dict[str, Any]):
        """Send health report to MCP for Nokia dashboard"""
        try:
            await self.mcp_publisher.send_json(health_report)
            logger.debug("Health report sent to MCP")
            
        except Exception as e:
            logger.error(f"Error sending health report to MCP: {e}")
    
    async def save_performance_metrics(self):
        """Save performance metrics to file"""
        try:
            metrics_data = {
                'timestamp': datetime.now().isoformat(),
                'orchestration_metrics': self.orchestration_metrics,
                'performance_history': list(self.performance_history)[-100:],  # Last 100 entries
                'network_health': self.network_state.get_network_health_summary()
            }
            
            with open(PERFORMANCE_METRICS_FILE, 'w') as f:
                json.dump(metrics_data, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Error saving performance metrics: {e}")
    
    async def start(self):
        """Start the Orchestration Agent"""
        logger.info("=" * 80)
        logger.info("🚀 STARTING NOKIA AI SELF-HEALING NETWORK ORCHESTRATOR")
        logger.info("Purpose: Multi-agent coordination and healing workflow orchestration")
        logger.info("Integration: Monitor → Calculation → Healing → Orchestration")
        logger.info("=" * 80)
        
        try:
            self.is_running = True
            self.orchestration_metrics['start_time'] = datetime.now()
            
            # Initialize communication
            await self.initialize_communication()
            
            # Initialize network topology
            await self.initialize_network_topology()
            
            # Start main loops concurrently
            await asyncio.gather(
                self.healing_message_loop(),
                self.workflow_execution_loop(),
                self.health_monitoring_loop(),
                return_exceptions=True
            )
            
        except Exception as e:
            logger.error(f"Error starting Orchestration Agent: {e}")
            raise
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the Orchestration Agent"""
        logger.info("🛑 Stopping Orchestration Agent...")
        self.is_running = False
        
        # Close ZeroMQ sockets
        if self.healing_subscriber:
            self.healing_subscriber.close()
        if self.mcp_publisher:
            self.mcp_publisher.close()
        if self.ns3_controller:
            self.ns3_controller.close()
        if self.status_publisher:
            self.status_publisher.close()
        
        # Terminate context
        self.context.term()
        
        # Save final metrics
        await self.save_performance_metrics()
        
        logger.info("Orchestration Agent stopped successfully")

# Configuration creation
def create_orchestrator_config():
    """Create default orchestrator configuration file"""
    orchestrator = OrchestrationAgent()
    config = orchestrator.get_default_config()
    
    with open(ORCHESTRATOR_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    
    logger.info(f"Created orchestrator configuration: {ORCHESTRATOR_CONFIG_FILE}")

# Main execution
async def main():
    """Main execution function"""
    try:
        # Create config if it doesn't exist
        if not os.path.exists(ORCHESTRATOR_CONFIG_FILE):
            create_orchestrator_config()
        
        # Initialize and start orchestrator
        orchestrator = OrchestrationAgent()
        await orchestrator.start()
        
    except KeyboardInterrupt:
        logger.info("Orchestration Agent stopped by user")
    except Exception as e:
        logger.error(f"Error in orchestration main: {e}")

if __name__ == "__main__":
    asyncio.run(main())