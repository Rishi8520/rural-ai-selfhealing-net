# main_orchestrator.py (Fixed to import EnhancedMonitorAgent)

import asyncio
import sys
import os
import time
import zmq.asyncio # Import zmq.asyncio for asynchronous operations

# Import all agent classes from their respective files
from salp_swarm_optimizer import SalpSwarmOptimizer
from calculation_agent import CalculationAgent
from healing_agent import HealingAgent
from mcp_agent import MCPAgent
from monitor_agent import EnhancedMonitorAgent 

# Suppress TensorFlow/PyTorch warnings (optional, adjust verbosity as needed)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' # For TensorFlow if used elsewhere
import warnings
warnings.filterwarnings("ignore", category=UserWarning) # For PyTorch warnings

# --- Main Orchestration Function ---
async def main():
    """
    The main function to initialize and start all agents (Monitor, Calculation, Healing, MCP)
    and manage their concurrent execution.
    """
    # Define ZeroMQ addresses for inter-agent communication
    # Ensure these addresses are consistent across all agent configurations.

    # A2A Communication (Calculation Agent PUB -> Healing Agent SUB)
    calc_agent_pub_address_a2a = "tcp://127.0.0.1:5556"

    # Agent -> MCP Communication (Calculation Agent PUSH -> MCP PULL)
    calc_agent_mcp_pull_address = "tcp://127.0.0.1:5557"

    # Agent -> MCP Communication (Healing Agent PUSH -> MCP PULL)
    healing_agent_mcp_pull_address = "tcp://127.0.0.1:5558"

    # Create a single ZeroMQ context for all agents
    zmq_context = zmq.asyncio.Context()

    # Initialize agents
    node_ids = [f"node_{i:02d}" for i in range(50)]

    # 1. Initialize Monitor Agent
    # Monitor Agent uses file-based streaming to Calculation Agent, so no ZMQ context needed here directly.
    monitor_agent_instance = EnhancedMonitorAgent() # *** CORRECTED: Instantiate EnhancedMonitorAgent ***

    # 2. Initialize Calculation Agent
    calculation_agent_instance = CalculationAgent(
        node_ids=node_ids,
        pub_socket_address_a2a=calc_agent_pub_address_a2a,
        push_socket_address_mcp=calc_agent_mcp_pull_address
    )

    # 3. Initialize Healing Agent
    healing_agent_instance = HealingAgent(
        context=zmq_context,
        sub_socket_address_a2a=calc_agent_pub_address_a2a,
        push_socket_address_mcp=healing_agent_mcp_pull_address
    )

    # 4. Initialize MCP Agent
    mcp_agent_instance = MCPAgent(
        context=zmq_context,
        calc_agent_pull_address=calc_agent_mcp_pull_address,
        healing_agent_pull_address=healing_agent_mcp_pull_address
    )

    print("\n--- Network Monitoring and Orchestration System Initialized ---")
    print(f"Calculation Agent (PUB) A2A: {calc_agent_pub_address_a2a}")
    print(f"Calculation Agent (PUSH) to MCP: {calc_agent_mcp_pull_address}")
    print(f"Healing Agent (SUB) from Calc: {calc_agent_pub_address_a2a}")
    print(f"Healing Agent (PUSH) to MCP: {healing_agent_mcp_pull_address}")
    print(f"MCP Agent (PULL) from Calc: {calc_agent_mcp_pull_address}")
    print(f"MCP Agent (PULL) from Healing: {healing_agent_mcp_pull_address}")
    print("\n--- System Running. Press Ctrl+C to stop ---")

    # Start all agents as asyncio tasks
    monitor_task = asyncio.create_task(monitor_agent_instance.start_enhanced_monitoring()) # *** CORRECTED: Call start_enhanced_monitoring ***
    calc_task = asyncio.create_task(calculation_agent_instance.start())
    healing_task = asyncio.create_task(healing_agent_instance.start())
    mcp_task = asyncio.create_task(mcp_agent_instance.start())

    try:
        await asyncio.gather(monitor_task, calc_task, healing_task, mcp_task)
    except asyncio.CancelledError:
        print("One or more agent tasks were cancelled.")
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt detected. Initiating graceful shutdown...")
        monitor_task.cancel()
        calc_task.cancel()
        healing_task.cancel()
        mcp_task.cancel()
        await asyncio.gather(monitor_task, calc_task, healing_task, mcp_task, return_exceptions=True)
        print("All agents shut down gracefully.")
        sys.exit(0)
    except Exception as e:
        print(f"An unexpected error occurred in the main orchestrator: {e}")
        sys.exit(1)
    finally:
        zmq_context.term()
        print("ZeroMQ context terminated.")


if __name__ == "__main__":
    asyncio.run(main())

