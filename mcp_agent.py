# mcp_agent.py 
import zmq
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MCPAgent:
    # IMPORTANT: The context is now passed from the orchestrator
    def __init__(self, context: zmq.Context, 
                 calc_agent_pull_address: str = "tcp://127.0.0.1:5557",
                 healing_agent_pull_address: str = "tcp://127.0.0.1:5558"):
        
        self.context = context
        self.calc_agent_pull_address = calc_agent_pull_address
        self.healing_agent_pull_address = healing_agent_pull_address

        # Socket for pulling messages from Calculation Agent
        self.calc_pull_socket = self.context.socket(zmq.PULL)
        # *** CRITICAL FIX: MCP Agent PULLs from Calculation Agent, so it CONNECTS ***
        self.calc_pull_socket.connect(self.calc_agent_pull_address) 
        logger.info(f"MCP Agent: Calculation Agent PULL connected to {self.calc_agent_pull_address}")

        # Socket for pulling messages from Healing Agent
        self.healing_pull_socket = self.context.socket(zmq.PULL)
        # *** CRITICAL FIX: MCP Agent PULLs from Healing Agent, so it CONNECTS ***
        self.healing_pull_socket.connect(self.healing_agent_pull_address)
        logger.info(f"MCP Agent: Healing Agent PULL connected to {self.healing_agent_pull_address}")

        self.poller = zmq.Poller()
        self.poller.register(self.calc_pull_socket, zmq.POLLIN)
        self.poller.register(self.healing_pull_socket, zmq.POLLIN)

        self.is_running = False
        self.received_alerts: List[Dict[str, Any]] = []

    async def start(self):
        self.is_running = True
        logger.info("MCP Agent started. Listening for alerts...")
        await self.receive_alerts_loop()

    async def stop(self):
        self.is_running = False
        logger.info("MCP Agent stopping...")
        self.calc_pull_socket.close()
        self.healing_pull_socket.close()
        # The context.term() should be handled by the main orchestrator

    async def receive_alerts_loop(self):
        while self.is_running:
            try:
                socks = dict(self.poller.poll(100)) # Poll with a timeout of 100ms

                if self.calc_pull_socket in socks and socks[self.calc_pull_socket] == zmq.POLLIN:
                    message_str = self.calc_pull_socket.recv_string()
                    self._process_alert(message_str, "CalculationAgent")

                if self.healing_pull_socket in socks and socks[self.healing_pull_socket] == zmq.POLLIN:
                    message_str = self.healing_pull_socket.recv_string()
                    self._process_alert(message_str, "HealingAgent")
                
                await asyncio.sleep(0.01) # Small sleep to yield control

            except zmq.Again: # No messages received after timeout
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                logger.info("MCP Agent receive loop cancelled.")
                break
            except Exception as e:
                logger.error(f"Error in MCP Agent receive loop: {e}", exc_info=True)
                await asyncio.sleep(1) # Wait before retrying

    def _process_alert(self, message_str: str, source_agent: str):
        try:
            alert_data = json.loads(message_str)
            alert_data['received_at_mcp'] = datetime.now().isoformat()
            alert_data['source_agent'] = source_agent
            self.received_alerts.append(alert_data)
            logger.info(f"MCP Agent received alert from {source_agent}: {alert_data.get('type', 'Unknown Type')} - {alert_data.get('alert_id', 'N/A')}")
            self.display_alert(alert_data)
        except json.JSONDecodeError:
            logger.error(f"MCP Agent: Failed to decode JSON message from {source_agent}: {message_str}")
        except Exception as e:
            logger.error(f"MCP Agent: Error processing alert from {source_agent}: {e}", exc_info=True)

    def display_alert(self, alert_data: Dict[str, Any]):
        """Simple function to display alerts (can be enhanced for a UI)"""
        logger.critical(f"\n--- MCP ALERT from {alert_data.get('source_agent')} ---")
        for key, value in alert_data.items():
            if key != 'metrics': # Don't print large metric dict directly
                logger.critical(f"  {key.replace('_', ' ').title()}: {value}")
        logger.critical("----------------------------------\n")

    def get_all_received_alerts(self) -> List[Dict[str, Any]]:
        return self.received_alerts

# This part is for standalone testing if needed, but typically run via orchestrator
if __name__ == "__main__":
    async def test_mcp_agent_standalone():
        context = zmq.Context()
        mcp = MCPAgent(context) # Pass the context
        try:
            await mcp.start()
        except KeyboardInterrupt:
            await mcp.stop()
        finally:
            context.term() # Terminate context when done

    logger.warning("MCP Agent is usually run via main_orchestrator.py. If running standalone, ensure other agents are binding to the specified addresses.")
    # asyncio.run(test_mcp_agent_standalone()) # Uncomment to run standalone for testing
