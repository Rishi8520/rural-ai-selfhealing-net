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
    def __init__(self, context: zmq.Context,
                 calc_agent_pull_address: str = "tcp://127.0.0.1:5557",
                 healing_agent_pull_address: str = "tcp://127.0.0.1:5558"):

        self.context = context
        self.calc_agent_pull_address = calc_agent_pull_address
        self.healing_agent_pull_address = healing_agent_pull_address

        # Socket for pulling messages from Calculation Agent
        self.calc_pull_socket = self.context.socket(zmq.PULL)
        self.calc_pull_socket.bind(self.calc_agent_pull_address) # CORRECTED: .bind()
        logger.info(f"MCP Agent: Calculation Agent PULL bound to {self.calc_agent_pull_address}")

        # Socket for pulling messages from Healing Agent
        self.healing_pull_socket = self.context.socket(zmq.PULL)
        self.healing_pull_socket.bind(self.healing_agent_pull_address) # CORRECTED: .bind()
        logger.info(f"MCP Agent: Healing Agent PULL bound to {self.healing_agent_pull_address}")
        # List to store all raw received alerts (for get_all_received_alerts method)
        self.received_alerts: List[Dict[str, Any]] = []

        # Dictionaries to temporarily store pending anomaly alerts and healing recommendations
        # Keyed by alert_id to facilitate correlation
        self.pending_anomaly_alerts: Dict[str, Dict[str, Any]] = {}
        self.pending_healing_recommendations: Dict[str, Dict[str, Any]] = {}

        logger.info("MCP Agent initialized.")

    async def start(self):
        logger.info("MCP Agent started, waiting for messages...")
        await asyncio.gather(
            self.receive_from_calculation_agent(),
            self.receive_from_healing_agent()
        )

    async def stop(self):
        logger.info("MCP Agent stopping...")
        self.calc_pull_socket.close()
        self.healing_pull_socket.close()
        logger.info("MCP Agent sockets closed.")

    async def receive_from_calculation_agent(self):
        """Receives messages from the Calculation Agent."""
        while True:
            try:
                message = await self.calc_pull_socket.recv_string()
                self.process_message("calculation_agent", message)
            except asyncio.CancelledError:
                logger.info("MCP Agent: Calculation Agent receiver task cancelled.")
                break
            except Exception as e:
                logger.error(f"MCP Agent: Error receiving from Calculation Agent: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def receive_from_healing_agent(self):
        """Receives messages from the Healing Agent."""
        while True:
            try:
                message = await self.healing_pull_socket.recv_string()
                self.process_message("healing_agent", message)
            except asyncio.CancelledError:
                logger.info("MCP Agent: Healing Agent receiver task cancelled.")
                break
            except Exception as e:
                logger.error(f"MCP Agent: Error receiving from Healing Agent: {e}", exc_info=True)
                await asyncio.sleep(1)

    def process_message(self, source_agent: str, message_str: str):
        """Processes incoming messages from different agents."""
        try:
            message_data = json.loads(message_str)
            self.received_alerts.append(message_data)

            if source_agent == "calculation_agent":
                alert_data = message_data
                alert_id = alert_data.get("alert_id")
                if alert_id:
                    self.pending_anomaly_alerts[alert_id] = alert_data
                    logger.info(f"MCP Agent: Received anomaly alert {alert_id} from Calculation Agent.")
                    self._check_and_display_correlated_alert(alert_id)
                else:
                    logger.warning(f"MCP Agent: Received calculation alert without alert_id: {alert_data}")
            elif source_agent == "healing_agent":
                recommendation_data = message_data
                alert_id = recommendation_data.get("alert_id")
                if alert_id:
                    self.pending_healing_recommendations[alert_id] = recommendation_data
                    logger.info(f"MCP Agent: Received healing recommendation for alert {alert_id} from Healing Agent.")
                    self._check_and_display_correlated_alert(alert_id)
                else:
                    logger.warning(f"MCP Agent: Received healing recommendation without alert_id: {recommendation_data}")
            else:
                logger.warning(f"MCP Agent: Received message from unknown source: {source_agent}")
                self.display_alert(message_data) # Fallback to generic display

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

    def _check_and_display_correlated_alert(self, alert_id: str):
        """
        Checks if both an anomaly alert and a healing recommendation for a given alert_id
        are available and displays them together.
        """
        anomaly_alert = self.pending_anomaly_alerts.get(alert_id)
        healing_recommendation = self.pending_healing_recommendations.get(alert_id)

        if anomaly_alert and healing_recommendation:
            node_id = anomaly_alert.get('node_id', 'N/A')
            logger.critical(f"\n--- Correlated Alert & Healing Plan for Node {node_id} (Alert ID: {alert_id}) ---")

            logger.critical("\n--- Calculation Agent Anomaly Output ---")
            logger.critical(f"  Detection Time: {anomaly_alert.get('detection_time', 'N/A')}")
            logger.critical(f"  Simulation Time: {anomaly_alert.get('simulation_time', 'N/A')}")
            logger.critical(f"  Anomaly Score: {anomaly_alert.get('anomaly_score', 'N/A'):.4f}")
            logger.critical(f"  Description: {anomaly_alert.get('description', 'N/A')}")
            logger.critical(f"  Actual Metrics: {anomaly_alert.get('actual_metrics', {})}")
            logger.critical(f"  Predicted Metrics: {anomaly_alert.get('predicted_metrics', {})}")

            logger.critical("\n--- Healing Agent Recommendation Output ---")
            logger.critical(f"  Recommendation: {healing_recommendation.get('recommendation', 'N/A')}")
            logger.critical(f"  Confidence: {healing_recommendation.get('confidence', 'N/A')}")
            logger.critical(f"  Justification: {healing_recommendation.get('justification', 'N/A')}")
            logger.critical(f"  Timestamp: {healing_recommendation.get('timestamp', 'N/A')}")
            logger.critical("------------------------------------------------------------------\n")

            # Clean up the pending alerts after displaying
            self.pending_anomaly_alerts.pop(alert_id, None)
            self.pending_healing_recommendations.pop(alert_id, None)

    def get_all_received_alerts(self) -> List[Dict[str, Any]]:
        return self.received_alerts

# This part is for standalone testing if needed, but typically run via orchestrator
if __name__ == "__main__":
    async def test_mcp_agent_standalone():
        context = zmq.Context()
        mcp = MCPAgent(context)
        try:
            await mcp.start()
        except KeyboardInterrupt:
            await mcp.stop()
        finally:
            context.term()

    logger.warning("MCP Agent is usually run via main_orchestrator.py. If running standalone, ensure other agents are pushing data to it.")
    # asyncio.run(test_mcp_agent_standalone()) # Uncomment to run standalone for testing