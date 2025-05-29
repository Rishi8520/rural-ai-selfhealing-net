# a2a_protocol_client.py
import asyncio
import logging
import json
import time
import websockets
import ssl
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class A2AProtocolClient:
    """Enhanced A2A Protocol Client with robust communication and failover"""
    
    def __init__(self, config: Dict[str, Any]):
        self.agent_id = config.get('agent_id', 'monitor_agent_001')
        self.communication_port = config.get('communication_port', 9001)
        self.target_agents = config.get('target_agents', ['calculation_agent', 'resolution_agent'])
        
        # Enhanced configuration
        self.server_host = config.get('server_host', 'localhost')
        self.use_ssl = config.get('use_ssl', False)
        self.authentication_token = config.get('authentication_token', '')
        self.heartbeat_interval = config.get('heartbeat_interval', 30)
        self.message_timeout = config.get('message_timeout', 60)
        
        # Connection management
        self.connected = False
        self.websocket_connections = {}
        self.message_queue = []
        self.pending_responses = {}
        self.message_handlers = {}
        
        # Reliability features
        self.connection_retry_attempts = 3
        self.connection_retry_delay = 5
        self.message_acknowledgments = {}
        
        # Statistics
        self.messages_sent = 0
        self.messages_received = 0
        self.connection_failures = 0
        
        logger.info(f"A2A Protocol Client initialized for agent {self.agent_id}")

    async def start_communication(self):
        """Start A2A communication with enhanced connectivity"""
        logger.info(f"Starting A2A communication on port {self.communication_port} for agent {self.agent_id}")
        
        try:
            # Start WebSocket server for incoming connections
            await self._start_websocket_server()
            
            # Connect to target agents
            await self._connect_to_target_agents()
            
            # Start background tasks
            asyncio.create_task(self._heartbeat_task())
            asyncio.create_task(self._message_processor())
            asyncio.create_task(self._cleanup_pending_messages())
            
            self.connected = True
            logger.info("A2A communication started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start A2A communication: {e}")
            raise

    async def _start_websocket_server(self):
        """Start WebSocket server for incoming A2A connections"""
        ssl_context = None
        if self.use_ssl:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        
        self.websocket_server = await websockets.serve(
            self._handle_incoming_connection,
            self.server_host,
            self.communication_port,
            ssl=ssl_context
        )
        
        logger.info(f"A2A WebSocket server listening on {self.server_host}:{self.communication_port}")

    async def _handle_incoming_connection(self, websocket, path):
        """Handle incoming WebSocket connections from other agents"""
        try:
            # Authenticate the connection
            auth_message = await websocket.recv()
            auth_data = json.loads(auth_message)
            
            if not self._authenticate_agent(auth_data):
                await websocket.send(json.dumps({'status': 'authentication_failed'}))
                await websocket.close()
                return
            
            remote_agent_id = auth_data['agent_id']
            self.websocket_connections[remote_agent_id] = websocket
            
            logger.info(f"Established A2A connection with {remote_agent_id}")
            
            # Send authentication success
            await websocket.send(json.dumps({'status': 'authenticated', 'agent_id': self.agent_id}))
            
            # Handle messages from this agent
            async for message in websocket:
                await self._process_incoming_message(remote_agent_id, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"A2A connection closed with {remote_agent_id}")
        except Exception as e:
            logger.error(f"Error handling A2A connection: {e}")
        finally:
            # Clean up connection
            if remote_agent_id in self.websocket_connections:
                del self.websocket_connections[remote_agent_id]

    def _authenticate_agent(self, auth_data: Dict[str, Any]) -> bool:
        """Authenticate incoming agent connection"""
        # In production, implement proper authentication
        required_fields = ['agent_id', 'authentication_token']
        
        for field in required_fields:
            if field not in auth_data:
                return False
        
        # Verify token (placeholder - implement proper verification)
        if auth_data['authentication_token'] != self.authentication_token:
            logger.warning(f"Authentication failed for agent {auth_data.get('agent_id')}")
            return False
        
        return True

    async def _connect_to_target_agents(self):
        """Connect to target agents with retry logic"""
        for target_agent in self.target_agents:
            await self._connect_to_agent(target_agent)

    async def _connect_to_agent(self, agent_id: str):
        """Connect to a specific agent with retry logic"""
        # Calculate target port (simple mapping for demo)
        port_mapping = {
            'calculation_agent': 9002,
            'resolution_agent': 9004,
            'healing_agent': 9003
        }
        
        target_port = port_mapping.get(agent_id, 9000)
        target_url = f"{'wss' if self.use_ssl else 'ws'}://{self.server_host}:{target_port}"
        
        for attempt in range(self.connection_retry_attempts):
            try:
                # Connect to target agent
                websocket = await websockets.connect(target_url)
                
                # Send authentication
                auth_message = {
                    'agent_id': self.agent_id,
                    'authentication_token': self.authentication_token,
                    'timestamp': datetime.now().isoformat()
                }
                
                await websocket.send(json.dumps(auth_message))
                
                # Wait for authentication response
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                auth_response = json.loads(response)
                
                if auth_response.get('status') == 'authenticated':
                    self.websocket_connections[agent_id] = websocket
                    logger.info(f"Connected to {agent_id}")
                    
                    # Start message handler for this connection
                    asyncio.create_task(self._handle_agent_messages(agent_id, websocket))
                    break
                else:
                    logger.error(f"Authentication failed with {agent_id}")
                    await websocket.close()
                    
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} to {agent_id} failed: {e}")
                if attempt < self.connection_retry_attempts - 1:
                    await asyncio.sleep(self.connection_retry_delay * (2 ** attempt))
                else:
                    logger.error(f"Failed to connect to {agent_id} after {self.connection_retry_attempts} attempts")
                    self.connection_failures += 1

    async def _handle_agent_messages(self, agent_id: str, websocket):
        """Handle messages from a specific agent"""
        try:
            async for message in websocket:
                await self._process_incoming_message(agent_id, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection closed with {agent_id}")
        except Exception as e:
            logger.error(f"Error handling messages from {agent_id}: {e}")
        finally:
            # Clean up connection
            if agent_id in self.websocket_connections:
                del self.websocket_connections[agent_id]

    async def _process_incoming_message(self, sender_agent: str, message: str):
        """Process incoming message from another agent"""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            message_id = data.get('message_id')
            
            self.messages_received += 1
            
            # Send acknowledgment
            if message_id:
                ack_message = {
                    'type': 'acknowledgment',
                    'message_id': message_id,
                    'agent_id': self.agent_id,
                    'timestamp': datetime.now().isoformat()
                }
                
                if sender_agent in self.websocket_connections:
                    await self.websocket_connections[sender_agent].send(json.dumps(ack_message))
            
            # Handle different message types
            if message_type == 'healing_response':
                await self._handle_healing_response(data)
            elif message_type == 'status_update':
                await self._handle_status_update(sender_agent, data)
            elif message_type == 'acknowledgment':
                await self._handle_acknowledgment(data)
            else:
                # Queue message for processing
                self.message_queue.append({
                    'sender': sender_agent,
                    'data': data,
                    'timestamp': datetime.now()
                })
                
            logger.debug(f"Processed {message_type} message from {sender_agent}")
            
        except Exception as e:
            logger.error(f"Error processing message from {sender_agent}: {e}")

    async def send_alert(self, alert_message):
        """Send alert to target agents with enhanced reliability"""
        message_id = str(uuid.uuid4())
        
        alert_data = {
            'type': 'anomaly_alert',
            'message_id': message_id,
            'source_agent': self.agent_id,
            'alert_id': alert_message.alert_id,
            'severity': alert_message.severity,
            'anomaly_score': alert_message.anomaly_score,
            'affected_nodes': alert_message.affected_nodes,
            'metrics_snapshot': alert_message.metrics_snapshot,
            'timestamp': alert_message.timestamp.isoformat(),
            'requires_immediate_action': alert_message.requires_immediate_action
        }
        
        # Send to all target agents
        successful_sends = 0
        for target_agent in self.target_agents:
            if await self._send_message_to_agent(target_agent, alert_data):
                successful_sends += 1
        
        # Store for acknowledgment tracking
        self.pending_responses[message_id] = {
            'alert_data': alert_data,
            'sent_at': datetime.now(),
            'acknowledgments_received': 0,
            'expected_acknowledgments': successful_sends
        }
        
        logger.info(f"Sent alert {alert_message.alert_id} to {successful_sends} agents")
        self.messages_sent += successful_sends

    async def _send_message_to_agent(self, agent_id: str, message_data: Dict[str, Any]) -> bool:
        """Send message to specific agent with error handling"""
        if agent_id not in self.websocket_connections:
            logger.warning(f"No active connection to {agent_id}")
            return False
        
        try:
            websocket = self.websocket_connections[agent_id]
            await websocket.send(json.dumps(message_data))
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message to {agent_id}: {e}")
            # Remove failed connection
            if agent_id in self.websocket_connections:
                del self.websocket_connections[agent_id]
            
            # Attempt to reconnect
            asyncio.create_task(self._connect_to_agent(agent_id))
            return False

    async def check_for_response(self) -> Optional[Dict[str, Any]]:
        """Check for responses from other agents"""
        if self.message_queue:
            # Process next message in queue
            message = self.message_queue.pop(0)
            
            # Check if it's a healing response
            if message['data'].get('type') == 'healing_response':
                return message['data']
        
        return None

    async def _handle_healing_response(self, response_data: Dict[str, Any]):
        """Handle healing response from calculation/healing agents"""
        logger.info(f"Received healing response: {response_data.get('session_id')}")
        
        # Process the response immediately rather than queuing
        if 'session_id' in response_data:
            # This will be picked up by check_for_response()
            healing_response = {
                'healing_initiated': response_data.get('healing_initiated', False),
                'session_id': response_data['session_id'],
                'healing_plan': response_data.get('healing_plan', {}),
                'target_nodes': response_data.get('target_nodes', []),
                'estimated_completion_time': response_data.get('estimated_completion_time')
            }
            
            # Add to front of queue for immediate processing
            self.message_queue.insert(0, {
                'sender': response_data.get('source_agent'),
                'data': healing_response,
                'timestamp': datetime.now()
            })

    async def _handle_acknowledgment(self, ack_data: Dict[str, Any]):
        """Handle message acknowledgments"""
        message_id = ack_data.get('message_id')
        
        if message_id in self.pending_responses:
            self.pending_responses[message_id]['acknowledgments_received'] += 1
            logger.debug(f"Received acknowledgment for message {message_id}")

    async def _heartbeat_task(self):
        """Send periodic heartbeat messages to maintain connections"""
        while self.connected:
            try:
                heartbeat_message = {
                    'type': 'heartbeat',
                    'agent_id': self.agent_id,
                    'timestamp': datetime.now().isoformat(),
                    'status': 'active'
                }
                
                # Send heartbeat to all connected agents
                for agent_id in list(self.websocket_connections.keys()):
                    await self._send_message_to_agent(agent_id, heartbeat_message)
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in heartbeat task: {e}")
                await asyncio.sleep(5)

    async def _message_processor(self):
        """Background task to process queued messages"""
        while self.connected:
            try:
                if self.message_queue:
                    # Process messages that have been waiting
                    current_time = datetime.now()
                    processed_messages = 0
                    
                    # Process up to 10 messages per cycle
                    for _ in range(min(10, len(self.message_queue))):
                        if self.message_queue:
                            message = self.message_queue.pop(0)
                            await self._route_message(message)
                            processed_messages += 1
                    
                    if processed_messages > 0:
                        logger.debug(f"Processed {processed_messages} queued messages")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in message processor: {e}")
                await asyncio.sleep(5)

    async def _route_message(self, message: Dict[str, Any]):
        """Route message to appropriate handler"""
        message_type = message['data'].get('type')
        
        if message_type in self.message_handlers:
            try:
                await self.message_handlers[message_type](message)
            except Exception as e:
                logger.error(f"Error in message handler for {message_type}: {e}")

    async def _cleanup_pending_messages(self):
        """Clean up expired pending messages"""
        while self.connected:
            try:
                current_time = datetime.now()
                expired_messages = []
                
                for message_id, message_info in self.pending_responses.items():
                    age = (current_time - message_info['sent_at']).total_seconds()
                    
                    if age > self.message_timeout:
                        expired_messages.append(message_id)
                
                # Remove expired messages
                for message_id in expired_messages:
                    logger.warning(f"Message {message_id} expired without full acknowledgment")
                    del self.pending_responses[message_id]
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(30)

    def register_message_handler(self, message_type: str, handler: Callable):
        """Register handler for specific message types"""
        self.message_handlers[message_type] = handler
        logger.info(f"Registered handler for message type: {message_type}")

    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status and statistics"""
        return {
            'connected': self.connected,
            'active_connections': list(self.websocket_connections.keys()),
            'messages_sent': self.messages_sent,
            'messages_received': self.messages_received,
            'connection_failures': self.connection_failures,
            'pending_responses': len(self.pending_responses),
            'queued_messages': len(self.message_queue)
        }

    async def stop_communication(self):
        """Enhanced stop with proper cleanup"""
        logger.info(f"Stopping A2A communication for agent {self.agent_id}")
        
        self.connected = False
        
        try:
            # Close all WebSocket connections
            for agent_id, websocket in self.websocket_connections.items():
                try:
                    await websocket.close()
                except Exception as e:
                    logger.warning(f"Error closing connection to {agent_id}: {e}")
            
            # Stop WebSocket server
            if hasattr(self, 'websocket_server'):
                self.websocket_server.close()
                await self.websocket_server.wait_closed()
            
            # Clear data structures
            self.websocket_connections.clear()
            self.message_queue.clear()
            self.pending_responses.clear()
            
            logger.info("A2A communication stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping A2A communication: {e}")
