# Create: tosca_healing_bridge.py
import asyncio
import logging
import json
from orchestration_agent import NetworkOrchestrationAgent
from healing_agent import HealingAgent

logger = logging.getLogger(__name__)

class TOSCAHealingBridge:
    """Bridge between Healing Agent decisions and TOSCA Orchestrator execution"""
    
    def __init__(self, healing_agent: HealingAgent, tosca_orchestrator: NetworkOrchestrationAgent):
        self.healing_agent = healing_agent
        self.tosca_orchestrator = tosca_orchestrator
        
    async def process_healing_decision(self, healing_plan: dict):
        """Convert healing agent decision to TOSCA workflow execution"""
        try:
            # Create workflow spec from healing decision
            workflow_spec = self.tosca_orchestrator.workflow_engine.create_workflow_spec(healing_plan)
            
            # Queue workflow for execution
            await self.tosca_orchestrator.workflow_engine.queue_workflow(workflow_spec)
            
            # Execute workflow
            execution = await self.tosca_orchestrator.workflow_engine.execute_next_workflow()
            
            if execution:
                logger.info(f"✅ TOSCA workflow {execution.spec.workflow_id} executed successfully")
                
                # Store results back in healing agent database
                self.healing_agent.db_manager.store_tosca_execution(
                    workflow_id=execution.spec.workflow_id,
                    workflow_type=execution.spec.strategy.value,
                    template_path=execution.spec.tosca_template,
                    execution_status='SUCCESS' if execution.status.value == 'completed' else 'FAILED',
                    effectiveness_score=execution.healing_effectiveness,
                    execution_duration=int((execution.completed_at - execution.started_at).total_seconds()) if execution.completed_at and execution.started_at else None,
                    parameters=execution.spec.tosca_inputs,
                    results=execution.metrics
                )
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error in TOSCA-Healing bridge: {e}")
            return False