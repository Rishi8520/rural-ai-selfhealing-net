import asyncio
import logging
import json
import os
import zmq.asyncio
from datetime import datetime

# Assuming agent classes are in the same directory and can be imported directly
from mcp_agent import MCPAgent
from calculation_agent import CalculationAgent
from healing_agent import HealingAgent
from monitor_agent import StreamlinedMonitorAgent

# Set up logging for the orchestrator
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ZeroMQ Addresses - These define how agents communicate
CALC_PUB_A2A_ADDR = "tcp://127.0.0.1:5556" # Calculation Agent publishes anomaly alerts to other agents
HEALING_SUB_A2A_ADDR = "tcp://127.0.0.1:5556" # Healing Agent subscribes to Calc A2A
CALC_PUSH_MCP_ADDR = "tcp://127.0.0.1:5557" # Calculation Agent pushes messages to MCP Agent
HEALING_PUSH_MCP_ADDR = "tcp://127.0.0.1:5558" # Healing Agent pushes messages to MCP Agent
MCP_CALC_PULL_ADDR = "tcp://127.0.0.1:5557" # MCP Agent pulls from Calc Agent
MCP_HEALING_PULL_ADDR = "tcp://127.0.0.1:5558" # MCP Agent pulls from Healing Agent

# --- Configuration File Creation Functions ---
def create_calculation_config():
    """Creates a default calculation_config.json if it doesn't exist."""
    config_file = "calculation_config.json"
    if not os.path.exists(config_file):
        default_config = {
            "prediction_features": [
                "throughput", "latency", "packet_loss", "cpu_usage", "memory_usage",
                "energy_level", "degradation_level", "fault_severity", "power_stability",
                "voltage_level"
            ],
            "input_features": [
                "throughput", "latency", "packet_loss", "cpu_usage", "memory_usage",
                "energy_level", "degradation_level", "fault_severity", "power_stability",
                "voltage_level"
            ],
            "prediction_horizon": 1,
            "train_on_startup": True, # Set to True to ensure training happens on startup
            "training_data_file": "baseline_network_metrics.csv", # Changed back to baseline_network_metrics.csv
            "testing_data_file": "rural_network_metrics.csv",
            "monitor_ns3_metrics_file": "calculation_agent_data_stream.json" # Monitor agent writes here
        }
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        logger.info(f"Created default {config_file}")
    else:
        logger.info(f"{config_file} already exists.")

def create_streamlined_monitor_config(node_ids_list: list[str]): # Added node_ids_list parameter
    """Creates a default streamlined_monitor_config.json if it doesn't exist."""
    config_file = "streamlined_monitor_config.json"
    if not os.path.exists(config_file):
        config = {
            "node_ids": node_ids_list, # Use the passed node_ids_list
            "data_interval_seconds": 1,
            "output_file": "calculation_agent_data_stream.json", # Output file for Calculation Agent to read
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
                "operational_threshold": 0.9,
                "energy_critical": 0.1
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
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"Created default {config_file}")
    else:
        logger.info(f"{config_file} already exists.")


# --- Orchestrator's Output Aggregator Task ---
async def orchestrator_output_aggregator_task(calc_sub_socket: zmq.asyncio.Socket):
    """
    Listens for anomaly alerts from Calculation Agent and formats output.
    Due to the constraint of not modifying other agent files, this task
    cannot directly receive specific output from the Healing Agent.
    """
    logger.info("Orchestrator: Output aggregator task started, listening for anomaly alerts.")
    while True:
        try:
            # Receive anomaly alert messages from Calculation Agent
            message_bytes = await calc_sub_socket.recv()
            alert_message = json.loads(message_bytes.decode('utf-8'))

            if alert_message.get("anomaly_type"): # Check if it's an anomaly alert
                node_id = alert_message.get("node_id", "N/A")
                current_metrics = alert_message.get("current_metrics", {})
                anomaly_details = alert_message.get("details", {})
                
                logger.critical(f"\n{'='*50}\nANOMALY DETECTED FOR NODE: {node_id}\n{'='*50}")
                
                # --- Monitor Agent Output ---
                # This is represented by the 'current_metrics' that led to the anomaly,
                # as collected by the Monitor Agent and passed to the Calculation Agent.
                logger.info("Monitor Agent Output (Metrics Leading to Anomaly):")
                for key, value in current_metrics.items():
                    logger.info(f"  {key}: {value}")
                
                # --- Calculation Agent Output ---
                # This is the anomaly alert message itself.
                logger.info("\nCalculation Agent Output (Anomaly Details):")
                logger.info(f"  Alert ID: {alert_message.get('alert_id')}")
                logger.info(f"  Timestamp: {alert_message.get('timestamp')}")
                logger.info(f"  Anomaly Type: {alert_message.get('anomaly_type')}")
                logger.info(f"  Prediction: {alert_message.get('predicted_metrics')}")
                logger.info(f"  Details: {anomaly_details.get('type', 'N/A')}: {anomaly_details.get('value', 'N/A')}")
                
                # --- Healing Agent Output ---
                # Placeholder: Due to the constraint of not modifying other agents,
                # the orchestrator cannot directly listen to Healing Agent's specific
                # recommendations that it pushes to the MCP Agent.
                logger.info("\nHealing Agent Output (Recommendation Status):")
                logger.info(f"  A healing action for node {node_id} would be recommended by the Healing Agent.")
                logger.info("  (Note: Direct real-time output from Healing Agent's recommendations is not available due to 'main_orchestrator.py' modification constraint.)")
                logger.info(f"{'='*50}\n")
            
            await asyncio.sleep(0.1) # Small delay to prevent busy-waiting
        except asyncio.CancelledError:
            logger.info("Orchestrator output aggregator task cancelled.")
            break
        except json.JSONDecodeError:
            logger.warning("Orchestrator: Received non-JSON message or malformed JSON from Calculation Agent.")
        except Exception as e:
            logger.error(f"Orchestrator: Error in output aggregator task: {e}", exc_info=True)
            await asyncio.sleep(1) # Wait before retrying after an error


async def main():
    """Main orchestration function to run all agents."""
    logger.info("Main Orchestrator: Starting up...")

    # Define the node IDs that your agents will work with
    # Expanded node_ids to cover all nodes from node_00 to node_49 as seen in logs
    node_ids = [f"node_{i:02d}" for i in range(50)]

    # Ensure configuration files exist for the agents, passing the expanded node_ids
    create_calculation_config()
    create_streamlined_monitor_config(node_ids) # Pass the expanded node_ids to config creator

    zmq_context = zmq.asyncio.Context()

    # --- 1. Initialize all Agent instances ---
    # MCP Agent: Central message processing for pushes from other agents
    mcp_agent = MCPAgent(
        context=zmq_context,
        calc_agent_pull_address=MCP_CALC_PULL_ADDR,
        healing_agent_pull_address=MCP_HEALING_PULL_ADDR
    )
    
    # Healing Agent: Subscribes to Calculation Agent's anomaly alerts and pushes recommendations to MCP
    healing_agent = HealingAgent(
        context=zmq_context,
        sub_socket_address_a2a=HEALING_SUB_A2A_ADDR,
        push_socket_address_mcp=HEALING_PUSH_MCP_ADDR
    )

    # Calculation Agent: Publishes anomaly alerts and pushes to MCP
    calc_agent = CalculationAgent(
        node_ids=node_ids, # Pass the expanded node_ids here
        pub_socket_address_a2a=CALC_PUB_A2A_ADDR,
        push_socket_address_mcp=CALC_PUSH_MCP_ADDR
    )

    # Monitor Agent: Streams data to a file that Calculation Agent reads
    monitor_config_file = "streamlined_monitor_config.json"
    monitor_agent = StreamlinedMonitorAgent(monitor_config_file)


    # --- 2. Setup Orchestrator's Listener for Calculation Agent Output ---
    # This socket allows the orchestrator to receive and display anomaly alerts directly
    # from the Calculation Agent's A2A publisher.
    orch_calc_sub_socket = zmq_context.socket(zmq.SUB)
    orch_calc_sub_socket.connect(CALC_PUB_A2A_ADDR)
    orch_calc_sub_socket.setsockopt_string(zmq.SUBSCRIBE, "") # Subscribe to all messages from Calc Agent

    # --- 3. Launch Agent Tasks According to the Desired Flow ---
    tasks = []

    # A. Launch MCP Agent and Healing Agent concurrently in the background.
    # They need to be running to handle messages from the Calculation Agent when it starts.
    tasks.append(asyncio.create_task(mcp_agent.start(), name="MCP_Agent_Task"))
    logger.info("Main Orchestrator: MCP Agent launched.")
    tasks.append(asyncio.create_task(healing_agent.start(), name="Healing_Agent_Task"))
    logger.info("Main Orchestrator: Healing Agent launched.")
    
    # B. Launch the Orchestrator's output aggregator task.
    # This task will start listening for anomaly alerts immediately.
    tasks.append(asyncio.create_task(orchestrator_output_aggregator_task(orch_calc_sub_socket), name="Orchestrator_Output_Aggregator"))
    logger.info("Main Orchestrator: Output aggregator launched.")


    # C. Calculation Agent must finish training first (blocking wait).
    # Calling await on calc_agent.start() will block the orchestrator's flow
    # until the Calculation Agent completes its internal (and synchronous) training process.
    logger.info("Main Orchestrator: Awaiting Calculation Agent training completion...")
    await calc_agent.start() 
    logger.info("Main Orchestrator: Calculation Agent training finished. Ready to process data.")

    # D. Then Monitor Agent can stream data (concurrently).
    # After Calculation Agent's training, the Monitor Agent can start streaming data.
    tasks.append(asyncio.create_task(monitor_agent.start_streamlined_monitoring(), name="Monitor_Agent_Task"))
    logger.info("Main Orchestrator: Monitor Agent launched and streaming data.")

    # Keep the orchestrator and all its launched tasks running indefinitely.
    try:
        await asyncio.gather(*tasks) # This will keep all launched tasks running until cancelled
    except KeyboardInterrupt:
        logger.info("\nMain Orchestrator: Shutting down all agents...")
    finally:
        # Gracefully cancel all launched tasks
        for task in tasks:
            task.cancel()
            try:
                await task # Await to ensure tasks are cleanly cancelled and resources released
            except asyncio.CancelledError:
                pass
        
        # Close ZeroMQ sockets and terminate context
        if orch_calc_sub_socket:
            orch_calc_sub_socket.close()
        if zmq_context:
            zmq_context.term()
        logger.info("Main Orchestrator: All agents and ZeroMQ resources shut down.")

if __name__ == "__main__":
    asyncio.run(main())