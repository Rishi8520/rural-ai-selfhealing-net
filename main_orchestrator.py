import asyncio
import logging
import json
import os
import zmq.asyncio
from datetime import datetime

# EXISTING IMPORTS (keep all your current imports)
from mcp_agent import MCPAgent
from calculation_agent import CalculationAgent
from healing_agent import HealingAgent
from monitor_agent import StreamlinedMonitorAgent

# NEW: Add orchestration agent import
from orchestration_agent import NetworkOrchestrationAgent

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Nokia Build-a-thon ZeroMQ Configuration (UPDATED)
SOCKET_ADDRESSES = {
    # EXISTING ADDRESSES (unchanged)
    'ANOMALY_PUBLISHER': 'tcp://127.0.0.1:5555',
    'METRICS_PUBLISHER': 'tcp://127.0.0.1:5556', 
    'MCP_CALC_PULL': 'tcp://127.0.0.1:5557',
    
    # NEW: Orchestration integration
    'HEALING_TO_ORCHESTRATION': 'tcp://127.0.0.1:5558',  # Healing → Orchestration
    'ORCHESTRATION_RECEIVER': 'tcp://127.0.0.1:5558',    # Orchestration listens here
    
    # Status updates
    'STATUS_PUBLISHER': 'tcp://127.0.0.1:5561'
}

class MainOrchestrator:
    def __init__(self):
        self.context = zmq.asyncio.Context()
        self.agents = {}
        self.is_running = False
        
        logger.info("🏆 Nokia Build-a-thon: Rural AI Self-Healing Network Orchestrator")
        logger.info("🔄 Enhanced with TOSCA Orchestration Integration")
        
    async def initialize_agents(self):
        """Initialize all agents with Nokia Build-a-thon configuration + TOSCA orchestration"""
        try:
            # 1. Monitor Agent - detects anomalies from NS3 data (UNCHANGED)
            monitor_config_file = "streamlined_monitor_config.json"
            self.agents['monitor'] = StreamlinedMonitorAgent(monitor_config_file)
            logger.info("✅ Monitor Agent initialized")
            
            # 2. Calculation Agent - analyzes anomalies and triggers healing (UNCHANGED)
            node_ids = [f"node_{i:02d}" for i in range(50)]
            self.agents['calculation'] = CalculationAgent(
                node_ids=node_ids,
                pub_socket_address_a2a=SOCKET_ADDRESSES['METRICS_PUBLISHER'],
                push_socket_address_mcp=SOCKET_ADDRESSES['MCP_CALC_PULL'],
            )
            logger.info("✅ Calculation Agent initialized")
            
            # 3. Healing Agent - generates AI healing plans (UPDATED - now sends to orchestration)
            config = {
                'rag_database_path': 'rural_network_knowledge_base.db',
                'ns3_database_path': 'data/ns3_simulation/database/'
            }
            self.agents['healing'] = HealingAgent(
                context=self.context,
                sub_socket_address_a2a=SOCKET_ADDRESSES['METRICS_PUBLISHER'],  # Listens to calculation
                push_socket_address_mcp=SOCKET_ADDRESSES['HEALING_TO_ORCHESTRATION'],  # NOW: Sends to orchestration
                config=config
            )
            logger.info("✅ Healing Agent initialized with real NS3 data + Orchestration integration")
            
            # 4. MCP Agent - central message processing (UNCHANGED)
            self.agents['mcp'] = MCPAgent(
                context=self.context,
                calc_agent_pull_address=SOCKET_ADDRESSES['MCP_CALC_PULL'],
                healing_agent_pull_address="tcp://127.0.0.1:5999"  # Not used in new flow
            )
            logger.info("✅ MCP Agent initialized")
            
            # 5. 🆕 NEW: TOSCA Orchestration Agent - executes infrastructure workflows
            self.agents['orchestration'] = NetworkOrchestrationAgent(
                
            )
            logger.info("✅ 🚀 TOSCA Orchestration Agent initialized with xOpera integration")
            
            logger.info("🎉 All 5 Nokia Build-a-thon agents initialized successfully!")
            logger.info("📊 Flow: Monitor → Calculation → Healing → 🆕 TOSCA Orchestration → Infrastructure")
            
        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}")
            raise
    
    async def start_all_agents(self):
        """Start all agents including TOSCA orchestration"""
        try:
            self.is_running = True
            
            # Create configuration files if needed
            await self._create_config_files()
            
            logger.info("🚀 Starting Nokia Build-a-thon AI Self-Healing Network...")
            logger.info("🆕 WITH TOSCA ORCHESTRATION INTEGRATION")
            logger.info("=" * 60)
            
            # Start agents in background tasks
            tasks = []
            
            # Start MCP Agent (message processing) - UNCHANGED
            tasks.append(asyncio.create_task(
                self.agents['mcp'].start(), 
                name="mcp_agent"
            ))
            
            # 🆕 NEW: Start TOSCA Orchestration Agent
            tasks.append(asyncio.create_task(
                self.agents['orchestration'].start(), 
                name="tosca_orchestration_agent"
            ))
            
            # Start Healing Agent (AI healing plans) - UNCHANGED
            tasks.append(asyncio.create_task(
                self.agents['healing'].start(), 
                name="healing_agent"
            ))
            
            logger.info("🤖 Background agents started (including TOSCA orchestration)...")
            
            # Train Calculation Agent (blocking) - UNCHANGED
            logger.info("🧠 Training Calculation Agent ML models...")
            await self.agents['calculation'].start()
            logger.info("✅ Calculation Agent training completed")
            
            # Start Monitor Agent (data streaming) - UNCHANGED
            tasks.append(asyncio.create_task(
                self.agents['monitor'].start_streamlined_monitoring(), 
                name="monitor_agent"
            ))
            
            logger.info("📊 Monitor Agent streaming NS3 data...")
            logger.info("=" * 60)
            logger.info("🎭 Nokia Build-a-thon System: FULLY OPERATIONAL WITH TOSCA!")
            logger.info("🔄 Complete Flow: Monitor → Calculation → Healing → 🆕 TOSCA → Infrastructure")
            logger.info("🏆 Enterprise-Grade AI Self-Healing with xOpera Orchestration")
            logger.info("=" * 60)
            
            # Keep system running
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except KeyboardInterrupt:
            logger.info("\n🛑 Nokia Build-a-thon system stopped by user")
        except Exception as e:
            logger.error(f"Error in Nokia Build-a-thon system: {e}")
        finally:
            await self.cleanup()
    
    async def _create_config_files(self):
        """Create necessary configuration files for Nokia Build-a-thon (UNCHANGED)"""
        # Create calculation config (UNCHANGED)
        calc_config = {
            "lstm_sequence_length": 10,
            "lstm_epochs": 20,
            "anomaly_threshold_percentile": 99,
            "alert_debounce_interval": 10,
            "model_training_batch_size": 32,
            "train_on_startup": True,
            "training_data_limit": 10000,
            "lstm_features": [
                'throughput', 'latency', 'packet_loss', 'jitter',
                'signal_strength', 'cpu_usage', 'memory_usage', 'buffer_occupancy',
                'active_links', 'neighbor_count', 'link_utilization', 'critical_load',
                'normal_load', 'energy_level', 'x_position', 'y_position', 'z_position',
                'degradation_level', 'fault_severity', 'power_stability', 'voltage_level'
            ],
            "prediction_horizon": 1,
            "training_data_file": "baseline_network_metrics.csv",
            "testing_data_file": "rural_network_metrics.csv",
            "monitor_ns3_metrics_file": "calculation_agent_data_stream.json"
        }
        
        if not os.path.exists("calculation_config.json"):
            with open("calculation_config.json", 'w') as f:
                json.dump(calc_config, f, indent=2)
            logger.info("📝 Created calculation_config.json")
        
        # Create monitor config (UNCHANGED)
        monitor_config = {
            "node_ids": [f"node_{i:02d}" for i in range(50)],
            "data_interval_seconds": 1,
            "output_file": "calculation_agent_data_stream.json",
            "metrics_mapping": {
                "packet_received": "throughput",
                "latency_avg": "latency",
                "packet_loss_rate": "packet_loss",
                "device_cpu_usage": "cpu_usage",
                "device_memory_usage": "memory_usage",
                "device_energy_level": "energy_level",
                "node_operational": "operational",
                "degradation_severity": "degradation_level",
                "fault_severity_level": "fault_severity",
                "power_stability_index": "power_stability",
                "voltage_level": "voltage_level",
                "node_type": "node_type",
                "pos_x": "position_x",
                "pos_y": "position_y"
            },
            "health_parameters": {
                "throughput_min": 1000.0,
                "latency_max": 50.0,
                "packet_loss_max": 0.01,
                "cpu_usage_max": 80.0,
                "memory_usage_max": 90.0,
                "energy_critical": 0.1,
                "degradation_threshold": 0.7,
                "fault_threshold": 0.5,
                "power_stability_min": 0.9,
                "voltage_min": 200.0,
                "voltage_max": 240.0,
                "operational_threshold": 0.9
            },
            "ns3": {
                "metrics_file": "rural_network_metrics.csv",
                "topology_file": "network_topology.json"
            },
            "logging": {
                "level": "INFO",
                "focus": "data_collection_and_basic_health"
            }
        }
        
        if not os.path.exists("streamlined_monitor_config.json"):
            with open("streamlined_monitor_config.json", 'w') as f:
                json.dump(monitor_config, f, indent=2)
            logger.info("📝 Created streamlined_monitor_config.json")

        # 🆕 NEW: Create TOSCA orchestration config
        tosca_config = {
            "xopera_path": "opera",  # Path to opera executable
            "templates_directory": "tosca_templates/",
            "deployment_timeout_seconds": 300,
            "default_priority": "medium",
            "logging": {
                "level": "INFO",
                "tosca_execution_logs": "tosca_executions.log"
            },
            "healing_strategy_mappings": {
                "reroute_traffic": "traffic_rerouting.yaml",
                "restart_device": "device_restart.yaml",
                "escalate_human": "human_escalation.yaml",
                "apply_policy": "policy_application.yaml",
                "backup_power_switch": "backup_power.yaml"
            }
        }
        
        if not os.path.exists("tosca_orchestration_config.json"):
            with open("tosca_orchestration_config.json", 'w') as f:
                json.dump(tosca_config, f, indent=2)
            logger.info("📝 🆕 Created tosca_orchestration_config.json")
    
    async def cleanup(self):
        """Clean up all agents and resources (ENHANCED)"""
        logger.info("🧹 Cleaning up Nokia Build-a-thon system...")
        
        self.is_running = False
        
        for agent_name, agent in self.agents.items():
            try:
                if hasattr(agent, 'close'):
                    await agent.close()
                elif hasattr(agent, 'db_manager'):
                    agent.db_manager.close()
                logger.info(f"✅ Cleaned up {agent_name}")
            except Exception as e:
                logger.error(f"Error cleaning up {agent_name}: {e}")
        
        self.context.term()
        logger.info("🎉 Nokia Build-a-thon system cleanup complete (with TOSCA)")

async def main():
    """Nokia Build-a-thon Main Entry Point - Enhanced with TOSCA"""
    print("🏆" + "=" * 60 + "🏆")
    print("🚀 NOKIA BUILD-A-THON: RURAL AI SELF-HEALING NETWORK")
    print("🤖 AI-Powered Network Healing with Google Gemini")
    print("🎭 🆕 TOSCA Orchestration with xOpera Integration")
    print("📊 Real NS3 Simulation Data Processing")
    print("🌐 Rural Broadband Infrastructure Focus")
    print("🔄 Complete Flow: AI → TOSCA → Infrastructure Automation")
    print("🏆" + "=" * 60 + "🏆")
    
    orchestrator = MainOrchestrator()
    
    try:
        await orchestrator.initialize_agents()
        await orchestrator.start_all_agents()
        
    except Exception as e:
        logger.error(f"Nokia Build-a-thon system failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())