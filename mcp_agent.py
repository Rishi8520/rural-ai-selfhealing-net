# --- File: mcp_agent.py ---
import asyncio
import zmq.asyncio
import json
import sys # For sys.exit()

class MCPAgent:
    """
    The Master Control Plane (MCP) Agent acts as a central listener for status updates
    and healing recommendations from other agents (Calculation Agent and Healing Agent).
    It receives messages and can log them, update dashboards, or trigger further orchestration.
    """
    def __init__(self, calc_agent_pull_address, healing_agent_pull_address):
        """
        Initializes the MCP Agent.

        Args:
            calc_agent_pull_address (str): ZeroMQ address for Calculation Agent to PUSH to.
            healing_agent_pull_address (str): ZeroMQ address for Healing Agent to PUSH to.
        """
        self.calc_agent_pull_address = calc_agent_pull_address
        self.healing_agent_pull_address = healing_agent_pull_address

        self.context = zmq.asyncio.Context()
        
        # PULL socket to receive messages from Calculation Agent
        self.calc_pull_socket = self.context.socket(zmq.PULL)
        self.calc_pull_socket.bind(self.calc_agent_pull_address)
        print(f"MCP Agent: PULL socket for Calculation Agent bound to {self.calc_agent_pull_address}")

        # PULL socket to receive messages from Healing Agent
        self.healing_pull_socket = self.context.socket(zmq.PULL)
        self.healing_pull_socket.bind(self.healing_agent_pull_address)
        print(f"MCP Agent: PULL socket for Healing Agent bound to {self.healing_agent_pull_address}")

    async def listen_for_messages(self):
        """
        Continuously listens for messages from both Calculation and Healing Agents
        using a ZeroMQ Poller for efficient handling of multiple sockets.
        """
        poller = zmq.asyncio.Poller()
        poller.register(self.calc_pull_socket, zmq.POLLIN)
        poller.register(self.healing_pull_socket, zmq.POLLIN)

        print("MCP Agent: Listening for messages...")
        while True:
            # Poll for events on registered sockets with a timeout
            # A small timeout prevents blocking indefinitely if no messages arrive.
            socks = await poller.poll(100) # Poll for 100 milliseconds

            for socket, event in socks:
                if socket == self.calc_pull_socket and event == zmq.POLLIN:
                    try:
                        msg_calc = await socket.recv_json()
                        print(f"\n[MCP Received from Calculation Agent]: {json.dumps(msg_calc, indent=2)}")
                        # In a real MCP, this would trigger further orchestration,
                        # logging, UI updates, command execution, etc.
                    except Exception as e:
                        print(f"MCP Agent: Error receiving from Calculation Agent: {e}")
                
                if socket == self.healing_pull_socket and event == zmq.POLLIN:
                    try:
                        msg_healing = await socket.recv_json()
                        print(f"\n[MCP Received from Healing Agent]: {json.dumps(msg_healing, indent=2)}")
                        # In a real MCP, this would process healing recommendations,
                        # potentially initiate automated actions, or alert human operators.
                    except Exception as e:
                        print(f"MCP Agent: Error receiving from Healing Agent: {e}")
            
            # Small sleep to yield control and prevent busy-waiting if no events
            await asyncio.sleep(0.01)

    async def start(self):
        """Starts the MCP Agent's listening process."""
        print("Master Control Plane (MCP) Agent started.")
        await self.listen_for_messages()

# --- Main function to run the MCP Agent (for standalone testing) ---
if __name__ == "__main__":
    print("Running standalone test for MCP Agent...")

    # Define ZeroMQ addresses for standalone testing
    # These should match the addresses used by Calculation Agent and Healing Agent
    test_calc_pull_address = "tcp://127.0.0.1:5557"
    test_healing_pull_address = "tcp://127.0.0.1:5558"

    # Initialize and start the MCP Agent
    mcp_agent = MCPAgent(
        calc_agent_pull_address=test_calc_pull_address,
        healing_agent_pull_address=test_healing_pull_address
    )

    try:
        asyncio.run(mcp_agent.start())
    except KeyboardInterrupt:
        print("\nMCP Agent standalone test stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"An error occurred during standalone MCP Agent run: {e}")
        sys.exit(1)

# --- End of File: mcp_agent.py ---