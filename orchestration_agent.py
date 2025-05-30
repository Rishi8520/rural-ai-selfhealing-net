# orchestration_agent.py - COMPLETE MULTI-AGENT ORCHESTRATION SYSTEM
import asyncio
import logging
import json
import time
import threading
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class HealingWorkflowSpec:
    """Healing workflow specification"""
    workflow_id: str
    fault_type: str
    affected_nodes: List[str]
    severity: str
    healing_strategy: str
    execution_steps: List[Dict[str, Any]]
    rollback_plan: List[Dict[str, Any]]
    estimated_duration: float
    priority: int

@dataclass
class OrchestrationResult:
    """Result of orchestration operation"""
    workflow_id: str
    success: bool
    execution_time: float
    steps_completed: int
    steps_failed: int
    healing_effectiveness: float
    error_message: Optional[str] = None

class HealingWorkflowEngine:
    """Engine for executing network healing workflows"""
    
    def __init__(self):
        self.healing_strategies = {
            'fiber_cut_repair': self._coordinate_fiber_restoration,
            'power_stabilization': self._coordinate_power_healing,
            'node_replacement': self._coordinate_node_recovery,
            'traffic_rerouting': self._coordinate_traffic_management,
            'gradual_degradation': self._coordinate_degradation_response,
            'predictive_maintenance': self._coordinate_preventive_action
        }
        
        self.active_workflows = {}
        self.workflow_history = []
        
        logger.info("Healing Workflow Engine initialized")

    async def _coordinate_fiber_restoration(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate fiber cut healing across multiple network layers"""
        logger.info(f"Coordinating fiber restoration for workflow: {workflow_data['workflow_id']}")
        
        steps = [
            {'action': 'isolate_affected_segment', 'priority': 1, 'duration': 30},
            {'action': 'activate_backup_routes', 'priority': 2, 'duration': 45}, 
            {'action': 'redistribute_traffic_load', 'priority': 3, 'duration': 60},
            {'action': 'monitor_network_stability', 'priority': 4, 'duration': 120},
            {'action': 'schedule_physical_repair', 'priority': 5, 'duration': 300}
        ]
        
        return await self._execute_healing_sequence(steps, workflow_data)

    async def _coordinate_power_healing(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate power fluctuation healing"""
        logger.info(f"Coordinating power stabilization for workflow: {workflow_data['workflow_id']}")
        
        steps = [
            {'action': 'switch_to_backup_power', 'priority': 1, 'duration': 20},
            {'action': 'stabilize_voltage_levels', 'priority': 2, 'duration': 60},
            {'action': 'verify_power_quality', 'priority': 3, 'duration': 30},
            {'action': 'restore_normal_operations', 'priority': 4, 'duration': 45}
        ]
        
        return await self._execute_healing_sequence(steps, workflow_data)

    async def _coordinate_node_recovery(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate node replacement/recovery"""
        logger.info(f"Coordinating node recovery for workflow: {workflow_data['workflow_id']}")
        
        steps = [
            {'action': 'diagnose_node_failure', 'priority': 1, 'duration': 45},
            {'action': 'activate_standby_node', 'priority': 2, 'duration': 60},
            {'action': 'transfer_node_configuration', 'priority': 3, 'duration': 90},
            {'action': 'validate_connectivity', 'priority': 4, 'duration': 30},
            {'action': 'update_routing_tables', 'priority': 5, 'duration': 40}
        ]
        
        return await self._execute_healing_sequence(steps, workflow_data)

    async def _coordinate_traffic_management(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate traffic rerouting"""
        logger.info(f"Coordinating traffic management for workflow: {workflow_data['workflow_id']}")
        
        steps = [
            {'action': 'analyze_traffic_patterns', 'priority': 1, 'duration': 30},
            {'action': 'identify_alternative_paths', 'priority': 2, 'duration': 45},
            {'action': 'implement_load_balancing', 'priority': 3, 'duration': 60},
            {'action': 'monitor_performance_metrics', 'priority': 4, 'duration': 120}
        ]
        
        return await self._execute_healing_sequence(steps, workflow_data)

    async def _coordinate_degradation_response(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate response to gradual degradation"""
        logger.info(f"Coordinating degradation response for workflow: {workflow_data['workflow_id']}")
        
        degradation_level = workflow_data.get('degradation_level', 0.0)
        
        if degradation_level > 0.7:
            # High degradation - immediate intervention
            steps = [
                {'action': 'reduce_network_load', 'priority': 1, 'duration': 20},
                {'action': 'optimize_routing_paths', 'priority': 2, 'duration': 40},
                {'action': 'schedule_maintenance', 'priority': 3, 'duration': 60}
            ]
        elif degradation_level > 0.3:
            # Moderate degradation - preventive measures
            steps = [
                {'action': 'optimize_network_parameters', 'priority': 1, 'duration': 30},
                {'action': 'increase_monitoring_frequency', 'priority': 2, 'duration': 15},
                {'action': 'prepare_contingency_plan', 'priority': 3, 'duration': 45}
            ]
        else:
            # Low degradation - monitoring enhancement
            steps = [
                {'action': 'enhance_monitoring', 'priority': 1, 'duration': 10},
                {'action': 'collect_diagnostic_data', 'priority': 2, 'duration': 20}
            ]
        
        return await self._execute_healing_sequence(steps, workflow_data)

    async def _coordinate_preventive_action(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate preventive maintenance based on predictions"""
        logger.info(f"Coordinating preventive action for workflow: {workflow_data['workflow_id']}")
        
        steps = [
            {'action': 'validate_prediction', 'priority': 1, 'duration': 15},
            {'action': 'prepare_resources', 'priority': 2, 'duration': 30},
            {'action': 'implement_preventive_measures', 'priority': 3, 'duration': 60},
            {'action': 'monitor_effectiveness', 'priority': 4, 'duration': 90}
        ]
        
        return await self._execute_healing_sequence(steps, workflow_data)

    async def _execute_healing_sequence(self, steps: List[Dict[str, Any]], workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a sequence of healing steps"""
        workflow_id = workflow_data['workflow_id']
        completed_steps = 0
        failed_steps = 0
        start_time = time.time()
        
        logger.info(f"Executing healing sequence for {workflow_id}: {len(steps)} steps")
        
        for i, step in enumerate(steps):
            try:
                logger.info(f"Step {i+1}/{len(steps)}: {step['action']} (Priority: {step['priority']})")
                
                # Simulate step execution
                await asyncio.sleep(step['duration'] / 10)  # Accelerated for demo
                
                # Simulate step success/failure (90% success rate)
                import random
                if random.random() > 0.1:
                    completed_steps += 1
                    logger.info(f"✅ Step completed: {step['action']}")
                else:
                    failed_steps += 1
                    logger.warning(f"❌ Step failed: {step['action']}")
                    
            except Exception as e:
                failed_steps += 1
                logger.error(f"❌ Step error: {step['action']} - {e}")
        
        execution_time = time.time() - start_time
        healing_effectiveness = completed_steps / len(steps) if steps else 0
        
        result = {
            'workflow_id': workflow_id,
            'success': failed_steps == 0,
            'execution_time': execution_time,
            'steps_completed': completed_steps,
            'steps_failed': failed_steps,
            'healing_effectiveness': healing_effectiveness
        }
        
        logger.info(f"Healing sequence completed for {workflow_id}: "
                   f"{completed_steps}/{len(steps)} steps successful "
                   f"(Effectiveness: {healing_effectiveness*100:.1f}%)")
        
        return result

class NetworkOrchestrationAgent:
    """Main orchestration agent for multi-agent network healing coordination"""
    
    def __init__(self, config_file: str = "orchestration_config.json"):
        self.config = self.load_configuration(config_file)
        
        # Core components
        self.workflow_engine = HealingWorkflowEngine()
        
        # Agent coordination
        self.connected_agents = {
            'monitor_agent': {'endpoint': 'mcp_agent_alerts.json', 'active': False},
            'calculation_agent': {'endpoint': 'calculation_agent_data_stream.json', 'active': False},
            'healing_agent': {'endpoint': 'healing_agent_recommendations.json', 'active': False}
        }
        
        # Orchestration state
        self.is_running = False
        self.active_workflows = {}
        self.orchestration_metrics = {
            'total_workflows': 0,
            'successful_workflows': 0,
            'failed_workflows': 0,
            'average_healing_time': 0.0,
            'network_availability': 100.0
        }
        
        logger.info("Network Orchestration Agent initialized")

    def load_configuration(self, config_file: str) -> Dict[str, Any]:
        """Load orchestration configuration"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            logger.info(f"Configuration loaded from {config_file}")
            return config
        except FileNotFoundError:
            logger.warning(f"Config file {config_file} not found, using defaults")
            return self.get_default_config()

    def get_default_config(self) -> Dict[str, Any]:
        """Default orchestration configuration"""
        return {
            "orchestration": {
                "max_concurrent_workflows": 5,
                "workflow_timeout": 300,
                "healing_effectiveness_threshold": 0.8,
                "monitoring_interval": 10.0
            },
            "healing_strategies": {
                "fiber_cut_repair": {"priority": 1, "timeout": 300},
                "power_stabilization": {"priority": 2, "timeout": 180},
                "node_replacement": {"priority": 1, "timeout": 400},
                "traffic_rerouting": {"priority": 3, "timeout": 120},
                "gradual_degradation": {"priority": 2, "timeout": 200},
                "predictive_maintenance": {"priority": 3, "timeout": 150}
            },
            "agent_integration": {
                "monitor_agent_poll_interval": 5.0,
                "calculation_agent_poll_interval": 15.0,
                "healing_agent_poll_interval": 10.0
            }
        }

    async def start_orchestration(self):
        """Start the orchestration agent"""
        logger.info("=" * 80)
        logger.info("STARTING NETWORK ORCHESTRATION AGENT")
        logger.info("AI-NATIVE SELF-HEALING NETWORK COORDINATOR")
        logger.info("=" * 80)
        
        self.is_running = True
        
        try:
            # Start agent monitoring tasks
            monitor_task = asyncio.create_task(self.monitor_agent_inputs())
            orchestration_task = asyncio.create_task(self.orchestration_loop())
            metrics_task = asyncio.create_task(self.metrics_collection_loop())
            
            # Wait for orchestration to complete
            await orchestration_task
            
            # Cancel other tasks
            monitor_task.cancel()
            metrics_task.cancel()
            
        except Exception as e:
            logger.error(f"Error in orchestration: {e}")
            raise
        finally:
            await self.stop_orchestration()

    async def monitor_agent_inputs(self):
        """Monitor inputs from other agents"""
        logger.info("Starting agent input monitoring...")
        
        while self.is_running:
            try:
                # Check for alerts from Monitor Agent
                await self.process_monitor_agent_alerts()
                
                # Check for recommendations from Calculation Agent (LSTM)
                await self.process_calculation_agent_recommendations()
                
                # Check for healing strategies from Healing Agent
                await self.process_healing_agent_strategies()
                
                await asyncio.sleep(self.config['agent_integration']['monitor_agent_poll_interval'])
                
            except Exception as e:
                logger.error(f"Error monitoring agent inputs: {e}")
                await asyncio.sleep(5.0)

    async def process_monitor_agent_alerts(self):
        """Process alerts from Monitor Agent"""
        alerts_file = self.connected_agents['monitor_agent']['endpoint']
        
        if os.path.exists(alerts_file):
            try:
                with open(alerts_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            alert_data = json.loads(line)
                            await self.handle_monitor_alert(alert_data)
                            
            except Exception as e:
                logger.error(f"Error processing monitor alerts: {e}")

    async def handle_monitor_alert(self, alert_data: Dict[str, Any]):
        """Handle individual alert from Monitor Agent"""
        alert_info = alert_data.get('alert_data', {})
        fault_type = alert_info.get('fault_type', 'unknown')
        severity = alert_info.get('severity', 'LOW')
        node_id = alert_info.get('node_id', 'unknown')
        
        logger.info(f"📢 Received alert: {fault_type} on {node_id} (Severity: {severity})")
        
        # Create healing workflow based on alert
        if severity in ['CRITICAL', 'HIGH']:
            await self.initiate_healing_workflow(alert_info)
        else:
            logger.info(f"Alert severity {severity} - monitoring only")

    async def process_calculation_agent_recommendations(self):
        """Process recommendations from Calculation Agent (LSTM analysis)"""
        calc_file = self.connected_agents['calculation_agent']['endpoint']
        
        if os.path.exists(calc_file):
            try:
                # Read latest LSTM analysis (simplified for demo)
                with open(calc_file, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        latest_data = json.loads(lines[-1])
                        await self.handle_lstm_analysis(latest_data)
                        
            except Exception as e:
                logger.error(f"Error processing calculation agent data: {e}")

    async def handle_lstm_analysis(self, lstm_data: Dict[str, Any]):
        """Handle LSTM analysis from Calculation Agent"""
        # Extract relevant information for orchestration decisions
        batch_stats = lstm_data.get('batch_statistics', {})
        anomalous_count = batch_stats.get('anomalous_data_points', 0)
        
        if anomalous_count > 0:
            logger.info(f"🧠 LSTM detected {anomalous_count} anomalous data points - enhancing monitoring")
            # Could trigger predictive maintenance workflows here

    async def process_healing_agent_strategies(self):
        """Process healing strategies from Healing Agent"""
        # Placeholder for healing agent integration
        # In real implementation, would read from healing agent output
        pass

    async def initiate_healing_workflow(self, alert_info: Dict[str, Any]) -> str:
        """Initiate a healing workflow based on fault information"""
        fault_type = alert_info.get('fault_type', 'unknown')
        node_id = alert_info.get('node_id', 'unknown')
        severity = alert_info.get('severity', 'MEDIUM')
        degradation_level = alert_info.get('degradation_level', 0.0)
        
        workflow_id = f"heal_{int(time.time())}_{node_id}_{fault_type}"
        
        # Determine healing strategy
        strategy_mapping = {
            'power_fluctuation': 'power_stabilization',
            'node_failure': 'node_replacement',
            'critical_fault': 'node_replacement',
            'gradual_degradation': 'gradual_degradation',
            'predicted_fault': 'predictive_maintenance'
        }
        
        healing_strategy = strategy_mapping.get(fault_type, 'traffic_rerouting')
        
        # Create workflow specification
        workflow_spec = HealingWorkflowSpec(
            workflow_id=workflow_id,
            fault_type=fault_type,
            affected_nodes=[node_id],
            severity=severity,
            healing_strategy=healing_strategy,
            execution_steps=[],  # Will be generated by workflow engine
            rollback_plan=[],    # Will be generated by workflow engine
            estimated_duration=self.config['healing_strategies'][healing_strategy]['timeout'],
            priority=self.config['healing_strategies'][healing_strategy]['priority']
        )
        
        logger.info(f"🔧 Initiating healing workflow: {workflow_id}")
        logger.info(f"   Strategy: {healing_strategy}")
        logger.info(f"   Priority: {workflow_spec.priority}")
        logger.info(f"   Estimated duration: {workflow_spec.estimated_duration}s")
        
        # Execute workflow
        result = await self.execute_healing_workflow(workflow_spec, alert_info)
        
        # Update metrics
        self.orchestration_metrics['total_workflows'] += 1
        if result.success:
            self.orchestration_metrics['successful_workflows'] += 1
        else:
            self.orchestration_metrics['failed_workflows'] += 1
        
        return workflow_id

    async def execute_healing_workflow(self, workflow_spec: HealingWorkflowSpec, context: Dict[str, Any]) -> OrchestrationResult:
        """Execute a healing workflow"""
        workflow_id = workflow_spec.workflow_id
        strategy = workflow_spec.healing_strategy
        
        logger.info(f"🚀 Executing healing workflow: {workflow_id}")
        
        # Store active workflow
        self.active_workflows[workflow_id] = {
            'spec': workflow_spec,
            'start_time': time.time(),
            'status': 'executing'
        }
        
        try:
            # Execute strategy using workflow engine
            if strategy in self.workflow_engine.healing_strategies:
                strategy_func = self.workflow_engine.healing_strategies[strategy]
                
                # Prepare workflow data
                workflow_data = {
                    'workflow_id': workflow_id,
                    'fault_type': workflow_spec.fault_type,
                    'affected_nodes': workflow_spec.affected_nodes,
                    'severity': workflow_spec.severity,
                    'degradation_level': context.get('degradation_level', 0.0),
                    'context': context
                }
                
                # Execute healing strategy
                result_data = await strategy_func(workflow_data)
                
                # Create orchestration result
                result = OrchestrationResult(
                    workflow_id=workflow_id,
                    success=result_data['success'],
                    execution_time=result_data['execution_time'],
                    steps_completed=result_data['steps_completed'],
                    steps_failed=result_data['steps_failed'],
                    healing_effectiveness=result_data['healing_effectiveness']
                )
                
            else:
                logger.error(f"Unknown healing strategy: {strategy}")
                result = OrchestrationResult(
                    workflow_id=workflow_id,
                    success=False,
                    execution_time=0.0,
                    steps_completed=0,
                    steps_failed=1,
                    healing_effectiveness=0.0,
                    error_message=f"Unknown strategy: {strategy}"
                )
            
            # Update workflow status
            self.active_workflows[workflow_id]['status'] = 'completed' if result.success else 'failed'
            self.active_workflows[workflow_id]['result'] = result
            
            # Log result
            if result.success:
                logger.info(f"✅ Healing workflow completed successfully: {workflow_id}")
                logger.info(f"   Healing effectiveness: {result.healing_effectiveness*100:.1f}%")
                logger.info(f"   Execution time: {result.execution_time:.1f}s")
            else:
                logger.error(f"❌ Healing workflow failed: {workflow_id}")
                logger.error(f"   Error: {result.error_message}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error executing workflow {workflow_id}: {e}")
            
            result = OrchestrationResult(
                workflow_id=workflow_id,
                success=False,
                execution_time=0.0,
                steps_completed=0,
                steps_failed=1,
                healing_effectiveness=0.0,
                error_message=str(e)
            )
            
            self.active_workflows[workflow_id]['status'] = 'error'
            self.active_workflows[workflow_id]['result'] = result
            
            return result

    async def orchestration_loop(self):
        """Main orchestration monitoring loop"""
        logger.info("Starting orchestration monitoring loop...")
        
        while self.is_running:
            try:
                # Check workflow timeouts
                await self.check_workflow_timeouts()
                
                # Update orchestration metrics
                await self.update_orchestration_metrics()
                
                # Log periodic status
                active_count = len([w for w in self.active_workflows.values() if w['status'] == 'executing'])
                if active_count > 0:
                    logger.info(f"📊 Active healing workflows: {active_count}")
                
                await asyncio.sleep(self.config['orchestration']['monitoring_interval'])
                
            except Exception as e:
                logger.error(f"Error in orchestration loop: {e}")
                await asyncio.sleep(5.0)

    async def check_workflow_timeouts(self):
        """Check for timed out workflows"""
        current_time = time.time()
        timeout_threshold = self.config['orchestration']['workflow_timeout']
        
        for workflow_id, workflow_info in list(self.active_workflows.items()):
            if workflow_info['status'] == 'executing':
                elapsed_time = current_time - workflow_info['start_time']
                if elapsed_time > timeout_threshold:
                    logger.warning(f"⏰ Workflow timeout: {workflow_id} (elapsed: {elapsed_time:.1f}s)")
                    workflow_info['status'] = 'timeout'

    async def update_orchestration_metrics(self):
        """Update orchestration performance metrics"""
        if self.orchestration_metrics['total_workflows'] > 0:
            success_rate = (self.orchestration_metrics['successful_workflows'] / 
                          self.orchestration_metrics['total_workflows']) * 100
            
            # Calculate network availability based on successful healing
            base_availability = 95.0  # Base network availability
            healing_bonus = (success_rate / 100) * 5.0  # Up to 5% bonus for good healing
            self.orchestration_metrics['network_availability'] = min(100.0, base_availability + healing_bonus)

    async def metrics_collection_loop(self):
        """Collect and log orchestration metrics"""
        while self.is_running:
            try:
                metrics = self.orchestration_metrics
                
                logger.info("=" * 60)
                logger.info("ORCHESTRATION METRICS SUMMARY")
                logger.info(f"Total workflows: {metrics['total_workflows']}")
                logger.info(f"Successful workflows: {metrics['successful_workflows']}")
                logger.info(f"Failed workflows: {metrics['failed_workflows']}")
                logger.info(f"Network availability: {metrics['network_availability']:.1f}%")
                logger.info("=" * 60)
                
                # Save metrics to file
                metrics_data = {
                    'timestamp': datetime.now().isoformat(),
                    'orchestration_metrics': metrics,
                    'active_workflows': len([w for w in self.active_workflows.values() if w['status'] == 'executing'])
                }
                
                with open('orchestration_metrics.json', 'w') as f:
                    json.dump(metrics_data, f, indent=2)
                
                await asyncio.sleep(60)  # Update every minute
                
            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
                await asyncio.sleep(30)

    async def stop_orchestration(self):
        """Stop orchestration agent"""
        logger.info("Stopping Network Orchestration Agent...")
        self.is_running = False
        
        # Generate final report
        await self.generate_orchestration_report()
        
        logger.info("Network Orchestration Agent stopped successfully")

    async def generate_orchestration_report(self):
        """Generate final orchestration report"""
        logger.info("=" * 80)
        logger.info("NETWORK ORCHESTRATION FINAL REPORT")
        logger.info("=" * 80)
        
        metrics = self.orchestration_metrics
        
        if metrics['total_workflows'] > 0:
            success_rate = (metrics['successful_workflows'] / metrics['total_workflows']) * 100
            logger.info(f"📊 Orchestration Performance:")
            logger.info(f"   Total healing workflows: {metrics['total_workflows']}")
            logger.info(f"   Successful healings: {metrics['successful_workflows']}")
            logger.info(f"   Failed healings: {metrics['failed_workflows']}")
            logger.info(f"   Success rate: {success_rate:.1f}%")
            logger.info(f"   Final network availability: {metrics['network_availability']:.1f}%")
        else:
            logger.info("📊 No healing workflows were executed during this session")
        
        # Save detailed report
        report = {
            'orchestration_session': {
                'timestamp': datetime.now().isoformat(),
                'session_metrics': metrics,
                'workflow_details': [
                    {
                        'workflow_id': wid,
                        'status': winfo['status'],
                        'start_time': winfo['start_time'],
                        'result': asdict(winfo.get('result', OrchestrationResult('', False, 0, 0, 0, 0)))
                    }
                    for wid, winfo in self.active_workflows.items()
                ]
            }
        }
        
        with open('orchestration_final_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info("Orchestration report saved to 'orchestration_final_report.json'")

# Configuration creation
def create_orchestration_config():
    """Create orchestration configuration file"""
    config = {
        "orchestration": {
            "max_concurrent_workflows": 5,
            "workflow_timeout": 300,
            "healing_effectiveness_threshold": 0.8,
            "monitoring_interval": 10.0
        },
        "healing_strategies": {
            "fiber_cut_repair": {"priority": 1, "timeout": 300},
            "power_stabilization": {"priority": 2, "timeout": 180},
            "node_replacement": {"priority": 1, "timeout": 400},
            "traffic_rerouting": {"priority": 3, "timeout": 120},
            "gradual_degradation": {"priority": 2, "timeout": 200},
            "predictive_maintenance": {"priority": 3, "timeout": 150}
        },
        "agent_integration": {
            "monitor_agent_poll_interval": 5.0,
            "calculation_agent_poll_interval": 15.0,
            "healing_agent_poll_interval": 10.0
        }
    }
    
    with open('orchestration_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("Orchestration configuration file created: orchestration_config.json")

# Main execution
async def main():
    """Main function to run the orchestration agent"""
    # Create config if it doesn't exist
    if not os.path.exists('orchestration_config.json'):
        create_orchestration_config()
    
    orchestrator = NetworkOrchestrationAgent()
    
    try:
        await orchestrator.start_orchestration()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        await orchestrator.stop_orchestration()

if __name__ == "__main__":
    asyncio.run(main())