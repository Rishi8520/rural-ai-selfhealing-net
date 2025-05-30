import asyncio
import sys
import os
import time

# Import all agent classes from their respective files
from salp_swarm_optimizer import SalpSwarmOptimizer
from calculation_agent import LSTMAnomalyModel, LSTMAnomalyDetector, CalculationAgent
from healing_agent import RetrievalAugmentedGenerator, HealingAgent # Note: RetrievalAugmentedGenerator is used internally by HealingAgent
from mcp_agent import MCPAgent

# Suppress TensorFlow/PyTorch warnings (optional, adjust verbosity as needed)
# This is usually set in the environment or at the start of the main script.
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' # For TensorFlow if used elsewhere
import warnings
warnings.filterwarnings("ignore", category=UserWarning) # For PyTorch warnings

# --- Main Orchestration Function ---
async def main():
    """
    The main function to initialize and start all agents (Calculation, Healing, MCP)
    and manage their concurrent execution.
    """
    # Define ZeroMQ addresses for inter-agent communication
    # Ensure these addresses are consistent across all agent configurations.

    # A2A Communication (Calculation Agent PUB -> Healing Agent SUB)
    # Calculation Agent will BIND to this address, Healing Agent will CONNECT to it.
    calc_agent_pub_address_a2a = "tcp://127.0.0.1:5556"

    # Agent -> MCP Communication (Calculation Agent PUSH -> MCP PULL)
    # MCP will BIND to this address, Calculation Agent will CONNECT to it.
    calc_agent_mcp_pull_address = "tcp://127.0.0.1:5557"

    # Agent -> MCP Communication (Healing Agent PUSH -> MCP PULL)
    # MCP will BIND to this address, Healing Agent will CONNECT to it.
    healing_agent_mcp_pull_address = "tcp://127.0.0.1:5558"

    # Initialize agents
    node_ids = [f"node_{i}" for i in range(1, 51)] # Monitor 50 network nodes

    # 1. Initialize Calculation Agent
    calculation_agent_instance = CalculationAgent(
        node_ids=node_ids,
        pub_socket_address_a2a=calc_agent_pub_address_a2a,
        push_socket_address_mcp=calc_agent_mcp_pull_address # Calc Agent PUSHes to MCP's PULL
    )

    # 2. Initialize Healing Agent
    healing_agent_instance = HealingAgent(
        sub_socket_address_a2a=calc_agent_pub_address_a2a, # Healing Agent SUBscribes to Calc Agent's PUB
        push_socket_address_mcp=healing_agent_mcp_pull_address # Healing Agent PUSHes to MCP's PULL
    )

    # 3. Initialize MCP Agent
    mcp_agent_instance = MCPAgent(
        calc_agent_pull_address=calc_agent_mcp_pull_address, # MCP PULLs from Calc Agent
        healing_agent_pull_address=healing_agent_mcp_pull_address # MCP PULLs from Healing Agent
    )

    # Start all agents as asyncio tasks
    # asyncio.create_task schedules the coroutine to run concurrently.
    calc_task = asyncio.create_task(calculation_agent_instance.start())
    healing_task = asyncio.create_task(healing_agent_instance.start())
    mcp_task = asyncio.create_task(mcp_agent_instance.start())

    print("\n--- Network Monitoring and Orchestration System Initialized ---")
    print(f"Calculation Agent (PUB) A2A: {calc_agent_pub_address_a2a}")
    print(f"Calculation Agent (PUSH) to MCP: {calc_agent_mcp_pull_address}")
    print(f"Healing Agent (SUB) from Calc: {calc_agent_pub_address_a2a}")
    print(f"Healing Agent (PUSH) to MCP: {healing_agent_mcp_pull_address}")
    print(f"MCP Agent (PULL) from Calc: {calc_agent_mcp_pull_address}")
    print(f"MCP Agent (PULL) from Healing: {healing_agent_mcp_pull_address}")
    print("\n--- System Running. Press Ctrl+C to stop ---")

    try:
        # Await all tasks to complete. This will keep the main loop running indefinitely
        # until a KeyboardInterrupt (Ctrl+C) or an unhandled exception occurs.
        await asyncio.gather(calc_task, healing_task, mcp_task)
    except asyncio.CancelledError:
        print("One or more agent tasks were cancelled.")
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt detected. Initiating graceful shutdown...")
        # Cancel all running tasks
        calc_task.cancel()
        healing_task.cancel()
        mcp_task.cancel()
        # Await tasks to ensure they handle cancellation gracefully and clean up resources
        # `return_exceptions=True` prevents `gather` from stopping if one task raises an exception
        await asyncio.gather(calc_task, healing_task, mcp_task, return_exceptions=True)
        print("All agents shut down gracefully.")
        sys.exit(0) # Exit cleanly
    except Exception as e:
        print(f"An unexpected error occurred in the main orchestrator: {e}")
        sys.exit(1) # Exit with an error code

if __name__ == "__main__":
    # Run the main asynchronous function
    asyncio.run(main())

