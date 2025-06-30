import os
import json
import time
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import aiofiles
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedMonitorAgent:
    """
    🏆 ITU Competition Ready: Enhanced Monitor Agent
    
    Features:
    - Static file monitoring (existing functionality)
    - Real-time fault detection from NS-3
    - Reports ONLY to Calculation Agent
    - Smart file tracking and validation
    - LSTM-ready data formatting
    
    Data Flow: NS-3 → Monitor Agent → Calculation Agent → Healing Agent
    """
    
    def __init__(self):
        # **PRESERVED: Your existing directory structure**
        self.ns3_simulation_dir = Path("/home/rishi/ns-allinone-3.44/ns-3.44")
        self.faults_dir = self.ns3_simulation_dir / "Faults"
        self.metrics_dir = self.ns3_simulation_dir / "NetworkMetrics"
        self.config_dir = self.ns3_simulation_dir / "Config"
        
        # **Real-time integration directories**
        self.agent_interface_dir = Path("ns3_integration/agent_interface")  # NS-3 real-time output
        self.calculation_input_dir = Path("calculation_agent_input")  # ONLY output to calculation agent
        self.monitoring_reports_dir = Path("calculation_input/monitoring_reports")
        
        # Create directories
        for directory in [self.calculation_input_dir, self.monitoring_reports_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        self.agent_interface_dir.mkdir(parents=True, exist_ok=True)
        # **PRESERVED: Your file tracking system**
        self.last_processed = {}
        self.file_hashes = {}
        self.processed_files = set()
        
        # **PRESERVED: Your essential vs optional files**
        self.essential_files = {
            'network_metrics': 'itu_competition_network_metrics.csv',
            'fault_events': 'itu_competition_fault_events.log', 
            'topology': 'itu_competition_topology.json',
            'config': 'itu_competition_config.json'
        }
        
        self.optional_files = {
            'flow_monitor': 'itu_competition_flowmon.xml',
            'animation': 'itu_competition_animation.xml'
        }
        
        # **Real-time file tracking**
        self.realtime_files = {
            'fault_events_realtime': self.agent_interface_dir / 'fault_events_realtime.json',
            'deployment_status': self.agent_interface_dir / 'deployment_status.json'
        }
        
        # **PRESERVED: Your monitoring statistics**
        self.monitoring_stats = {
            'files_processed': 0,
            'data_points_collected': 0,
            'faults_detected': 0,
            'realtime_events_processed': 0,
            'calculation_agent_notifications': 0,
            'last_update': datetime.now().isoformat()
        }
        
        # **Enhanced monitoring state**
        self.is_running = False
        self.static_monitoring_active = False
        self.realtime_monitoring_active = False
        
        logger.info("✅ Enhanced Monitor Agent initialized")
        logger.info(f"📁 Static monitoring: {self.ns3_simulation_dir}")
        logger.info(f"🔥 Real-time monitoring: {self.agent_interface_dir}")
        logger.info(f"📤 Reporting ONLY to Calculation Agent: {self.calculation_input_dir}")
        logger.info("🔗 Data Flow: NS-3 → Monitor Agent → Calculation Agent → Healing Agent")

    # **PRESERVED: Your existing file validation methods**
    async def scan_essential_files(self) -> Dict[str, bool]:
        """PRESERVED: Scan for essential simulation files"""
        file_status = {}
        
        logger.info("🔍 Scanning for essential simulation files...")
        
        for file_type, filename in self.essential_files.items():
            file_path = self.ns3_simulation_dir / filename
            
            if file_path.exists():
                file_size = file_path.stat().st_size
                file_status[file_type] = {
                    'exists': True,
                    'path': str(file_path),
                    'size': self.format_file_size(file_size),
                    'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                }
                logger.info(f"✅ {file_type}: {filename} ({file_status[file_type]['size']})")
            else:
                file_status[file_type] = {'exists': False, 'path': str(file_path)}
                logger.warning(f"❌ {file_type}: {filename} - NOT FOUND")
        
        return file_status

    def format_file_size(self, size_bytes: int) -> str:
        """PRESERVED: Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"

    async def check_for_new_data(self) -> bool:
        """PRESERVED: Check if new simulation data is available"""
        new_data_available = False
        
        for file_type, filename in self.essential_files.items():
            file_path = self.ns3_simulation_dir / filename
            
            if file_path.exists():
                current_mod_time = file_path.stat().st_mtime
                last_mod_time = self.last_processed.get(filename, 0)
                
                if current_mod_time > last_mod_time:
                    logger.info(f"🔄 New data detected in {filename}")
                    new_data_available = True
                    self.last_processed[filename] = current_mod_time
        
        return new_data_available

    def validate_data(self, data: Dict[str, Any]) -> bool:
        """PRESERVED: Validate processed data before sending to calculation agent"""
        try:
            # Check monitor metadata
            if 'monitor_metadata' not in data:
                logger.error("❌ Missing monitor_metadata")
                return False
            
            metadata = data['monitor_metadata']
            required_metadata = ['generated_timestamp', 'source_agent', 'target_agent']
            
            for field in required_metadata:
                if field not in metadata:
                    logger.error(f"❌ Missing metadata field: {field}")
                    return False
            
            # Ensure target is calculation agent only
            if metadata.get('target_agent') != 'calculation_agent':
                logger.error("❌ Invalid target agent - must be calculation_agent")
                return False
            
            # Check training data structure
            if 'lstm_training_data' in data:
                training_data = data['lstm_training_data']
                
                if 'ready_for_training' not in training_data:
                    logger.warning("⚠️ Training readiness not specified")
                
                if training_data.get('ready_for_training', False):
                    if not training_data.get('network_metrics', {}):
                        logger.warning("⚠️ No network metrics for training")
                        return False
            
            logger.info("✅ Data validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Data validation error: {e}")
            return False

    # **Real-time fault monitoring methods**
    async def monitor_realtime_faults(self):
        """Monitor real-time fault injection from NS-3 every 10 seconds"""
        logger.info("🔥 Starting real-time fault monitoring...")
        self.realtime_monitoring_active = True
        
        while self.is_running:
            try:
                fault_events_file = self.realtime_files['fault_events_realtime']
                
                if fault_events_file.exists():
                    # Check if file was updated
                    mod_time = fault_events_file.stat().st_mtime
                    last_mod = self.last_processed.get('fault_events_realtime.json', 0)
                    
                    if mod_time > last_mod:
                        logger.info("🚨 Real-time fault detected!")
                        
                        # Process real-time fault data
                        await self.process_realtime_fault_event(fault_events_file)
                        
                        self.last_processed['fault_events_realtime.json'] = mod_time
                        self.monitoring_stats['realtime_events_processed'] += 1
                
                # Also check for deployment status updates
                await self.check_deployment_status_updates()
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"❌ Real-time fault monitoring error: {e}")
                await asyncio.sleep(5)
        
        self.realtime_monitoring_active = False
        logger.info("🛑 Real-time fault monitoring stopped")

    async def process_realtime_fault_event(self, fault_file: Path):
        """Process real-time fault from NS-3 and send ONLY to Calculation Agent"""
        try:
            async with aiofiles.open(fault_file, 'r') as f:
                content = await f.read()
                fault_data = json.loads(content)
            
            timestamp = int(time.time())
            
            # **ONLY create file for Calculation Agent**
            calc_file = self.calculation_input_dir / f"realtime_fault_{timestamp}.json"
            calc_data = await self.format_for_calculation_agent(fault_data, is_realtime=True)
            
            async with aiofiles.open(calc_file, 'w') as f:
                await f.write(json.dumps(calc_data, indent=2))
            
            self.monitoring_stats['faults_detected'] += 1
            self.monitoring_stats['calculation_agent_notifications'] += 1
            
            logger.info(f"📤 Real-time fault sent to Calculation Agent: {calc_file.name}")
            
            # **Create notification for calculation agent**
            await self.notify_calculation_agent_of_realtime_fault(calc_data, calc_file)
            
        except Exception as e:
            logger.error(f"❌ Error processing real-time fault: {e}")

    async def format_for_calculation_agent(self, fault_data: dict, is_realtime: bool = False) -> dict:
        """Format fault data for LSTM Calculation Agent"""
        events = fault_data.get('events', [])
        
        # Enhanced format compatible with your existing calculation agent
        formatted_data = {
            'monitor_metadata': {
                'generated_timestamp': datetime.now().isoformat(),
                'source_agent': 'enhanced_monitor_agent',
                'target_agent': 'calculation_agent',  # ONLY target calculation agent
                'data_type': 'realtime_fault' if is_realtime else 'static_simulation',
                'data_version': '2.0',
                'processing_priority': 'high' if is_realtime else 'normal'
            },
            'lstm_training_data': {
                'network_metrics': {},
                'fault_events': [],
                'ready_for_training': True,
                'data_quality': 'high',
                'sequence_length': 50,  # For LSTM training
                'data_source': 'realtime_ns3' if is_realtime else 'static_files'
            },
            'fault_analysis': {
                'fault_detected': len(events) > 0,
                'fault_count': len(events),
                'severity_levels': [],
                'fault_types': [],
                'affected_node_count': 0,
                'requires_immediate_processing': is_realtime
            },
            'anomaly_detection_context': {
                'expected_anomaly_score': 0.8,
                'confidence_threshold': 0.7,
                'requires_immediate_action': False,
                'suggested_lstm_parameters': {
                    'learning_rate': 0.001,
                    'batch_size': 32,
                    'epochs': 100
                }
            }
        }
        
        affected_nodes_set = set()
        
        # Process each fault event for LSTM
        for event in events:
            affected_nodes = event.get('affected_nodes', [])
            fault_type = event.get('fault_type', '')
            severity = event.get('severity', 0.0)
            
            # Add to fault events
            formatted_data['lstm_training_data']['fault_events'].append({
                'event_id': event.get('event_id', f"evt_{int(time.time())}"),
                'timestamp': event.get('timestamp', time.time()),
                'node_ids': affected_nodes,
                'fault_type': fault_type,
                'severity': severity,
                'description': event.get('description', ''),
                'requires_immediate_action': event.get('requires_immediate_action', False)
            })
            
            # Track severity and fault types
            formatted_data['fault_analysis']['severity_levels'].append(severity)
            if fault_type not in formatted_data['fault_analysis']['fault_types']:
                formatted_data['fault_analysis']['fault_types'].append(fault_type)
            
            # Set anomaly detection context based on severity
            if severity > 0.8:
                formatted_data['anomaly_detection_context']['requires_immediate_action'] = True
                formatted_data['anomaly_detection_context']['expected_anomaly_score'] = 0.95
            
            # Create enhanced network metrics for affected nodes (LSTM format)
            for node_id in affected_nodes:
                affected_nodes_set.add(node_id)
                node_key = f"node_{node_id:02d}" if isinstance(node_id, int) else str(node_id)
                
                # Base metrics with timestamp
                base_metrics = {
                    'timestamp': time.time(),
                    'node_id': node_id,
                    'fault_severity': severity,
                    'fault_type': fault_type,
                    'data_source': 'realtime_fault_injection' if is_realtime else 'static_simulation',
                    'monitoring_agent_confidence': 0.95
                }
                
                # Apply fault-specific metric modifications for LSTM training
                if fault_type == "fiber_cut":
                    base_metrics.update({
                        'throughput': 50.0 * (1.0 - severity * 0.8),  # Reduced throughput
                        'latency': 10.0 * (1.0 + severity * 2.0),     # Increased latency
                        'packet_loss': 0.01 + severity * 0.3,         # Increased packet loss
                        'jitter': 1.0 * (1.0 + severity * 1.5),      # Increased jitter
                        'active_links': max(1, int(3 * (1.0 - severity))), # Reduced links
                        'link_utilization': min(1.0, 0.5 + severity * 0.4),
                        'cpu_usage': 0.3,
                        'memory_usage': 0.4,
                        'buffer_occupancy': 0.2 + severity * 0.3,
                        'degradation_level': severity,
                        'connectivity_status': 'degraded' if severity > 0.5 else 'stable',
                        'signal_strength': -60.0 - severity * 10.0,
                        'energy_level': 0.8,
                        'power_stability': 0.9
                    })
                elif fault_type == "power_fluctuation":
                    base_metrics.update({
                        'throughput': 50.0,
                        'latency': 10.0,
                        'packet_loss': 0.01,
                        'jitter': 1.0,
                        'active_links': 3,
                        'link_utilization': 0.5,
                        'cpu_usage': min(1.0, 0.3 + severity * 0.3),  # Increased CPU
                        'memory_usage': min(1.0, 0.4 + severity * 0.2), # Increased memory
                        'buffer_occupancy': min(1.0, 0.2 + severity * 0.4), # Increased buffer
                        'power_stability': 0.9 * (1.0 - severity * 0.5), # Reduced stability
                        'voltage_level': 0.95 * (1.0 - severity * 0.2),  # Reduced voltage
                        'energy_level': 0.8 * (1.0 - severity * 0.1),    # Reduced energy
                        'degradation_level': severity,
                        'power_status': 'unstable' if severity > 0.6 else 'stable',
                        'signal_strength': -60.0 - severity * 5.0
                    })
                
                formatted_data['lstm_training_data']['network_metrics'][node_key] = base_metrics
        
        # Update affected node count
        formatted_data['fault_analysis']['affected_node_count'] = len(affected_nodes_set)
        
        return formatted_data

    async def notify_calculation_agent_of_realtime_fault(self, calc_data: Dict[str, Any], calc_file: Path):
        """Notify calculation agent of new real-time fault data"""
        try:
            # Create notification file
            notification = {
                'notification_type': 'realtime_fault_detected',
                'timestamp': datetime.now().isoformat(),
                'source_agent': 'enhanced_monitor_agent',
                'target_agent': 'calculation_agent',
                'priority': 'high',
                'data_file': str(calc_file),
                'fault_summary': {
                    'fault_count': calc_data.get('fault_analysis', {}).get('fault_count', 0),
                    'affected_nodes': calc_data.get('fault_analysis', {}).get('affected_node_count', 0),
                    'max_severity': max(calc_data.get('fault_analysis', {}).get('severity_levels', [0])),
                    'fault_types': calc_data.get('fault_analysis', {}).get('fault_types', []),
                    'requires_immediate_action': calc_data.get('anomaly_detection_context', {}).get('requires_immediate_action', False)
                },
                'processing_instructions': {
                    'suggested_lstm_priority': 'high',
                    'suggested_anomaly_threshold': 0.7,
                    'suggested_confidence_threshold': 0.8
                }
            }
            
            notification_file = self.calculation_input_dir / f"fault_notification_{int(time.time())}.json"
            
            async with aiofiles.open(notification_file, 'w') as f:
                await f.write(json.dumps(notification, indent=2))
            
            logger.info(f"📨 Calculation agent notified of real-time fault: {notification_file.name}")
            
        except Exception as e:
            logger.error(f"❌ Error notifying calculation agent: {e}")

    async def check_deployment_status_updates(self):
        """Check for deployment status updates from orchestration"""
        try:
            status_file = self.realtime_files['deployment_status']
            
            if status_file.exists():
                mod_time = status_file.stat().st_mtime
                last_mod = self.last_processed.get('deployment_status.json', 0)
                
                if mod_time > last_mod:
                    async with aiofiles.open(status_file, 'r') as f:
                        content = await f.read()
                        status_data = json.loads(content)
                    
                    logger.info(f"📋 Deployment status update: {status_data.get('deployment_status', {}).get('success', 'unknown')}")
                    self.last_processed['deployment_status.json'] = mod_time
                    
                    # Inform calculation agent about deployment status
                    await self.inform_calculation_agent_of_deployment_status(status_data)
                    
        except Exception as e:
            logger.error(f"❌ Error checking deployment status: {e}")

    async def inform_calculation_agent_of_deployment_status(self, status_data: dict):
        """Inform calculation agent about deployment status for learning"""
        try:
            timestamp = int(time.time())
            
            deployment_info = {
                'monitor_metadata': {
                    'generated_timestamp': datetime.now().isoformat(),
                    'source_agent': 'enhanced_monitor_agent',
                    'target_agent': 'calculation_agent',
                    'data_type': 'deployment_feedback',
                    'data_version': '2.0'
                },
                'deployment_feedback': {
                    'deployment_success': status_data.get('deployment_status', {}).get('success', False),
                    'plan_id': status_data.get('deployment_status', {}).get('plan_id', 'unknown'),
                    'deployment_timestamp': status_data.get('deployment_status', {}).get('timestamp', time.time()),
                    'details': status_data.get('deployment_status', {}).get('details', ''),
                    'healing_effectiveness': 'pending_evaluation'
                },
                'learning_context': {
                    'use_for_model_validation': True,
                    'deployment_success_rate_tracking': True,
                    'healing_plan_effectiveness_feedback': True
                }
            }
            
            feedback_file = self.calculation_input_dir / f"deployment_feedback_{timestamp}.json"
            
            async with aiofiles.open(feedback_file, 'w') as f:
                await f.write(json.dumps(deployment_info, indent=2))
            
            logger.info(f"📋 Deployment feedback sent to Calculation Agent: {feedback_file.name}")
            
        except Exception as e:
            logger.error(f"❌ Error sending deployment feedback: {e}")

    # **PRESERVED: Your existing static file monitoring**
    async def static_file_monitoring(self):
        """PRESERVED: Your existing static file monitoring logic"""
        logger.info("📊 Starting static file monitoring...")
        self.static_monitoring_active = True
        
        while self.is_running:
            try:
                if await self.check_for_new_data():
                    logger.info("⟳ Processing static simulation data...")
                    
                    processed_data = await self.process_simulation_data()
                    
                    if processed_data and self.validate_data(processed_data):
                        output_file = await self.create_calculation_input(processed_data)
                        
                        if output_file:
                            await self.notify_calculation_agent(processed_data, output_file)
                    else:
                        logger.warning("⚠️ Data validation failed")
                
                await asyncio.sleep(10)  # Your 10-second interval
                
            except Exception as e:
                logger.error(f"❌ Static monitoring error: {e}")
                await asyncio.sleep(5)
        
        self.static_monitoring_active = False
        logger.info("🛑 Static file monitoring stopped")

    async def process_simulation_data(self) -> Optional[Dict[str, Any]]:
        """PRESERVED: Process simulation data from static files"""
        try:
            processed_data = {
                'monitor_metadata': {
                    'generated_timestamp': datetime.now().isoformat(),
                    'source_agent': 'enhanced_monitor_agent',
                    'target_agent': 'calculation_agent',  # ONLY calculation agent
                    'data_type': 'static_simulation',
                    'data_version': '2.0'
                },
                'lstm_training_data': {
                    'network_metrics': {},
                    'fault_events': [],
                    'ready_for_training': False,
                    'data_source': 'static_files'
                },
                'file_processing_info': {
                    'files_processed': [],
                    'processing_timestamp': datetime.now().isoformat()
                }
            }
            
            # Process network metrics
            metrics_file = self.ns3_simulation_dir / self.essential_files['network_metrics']
            if metrics_file.exists():
                network_metrics = await self.parse_network_metrics(metrics_file)
                processed_data['lstm_training_data']['network_metrics'] = network_metrics
                processed_data['file_processing_info']['files_processed'].append('network_metrics')
            
            # Process fault events
            fault_file = self.ns3_simulation_dir / self.essential_files['fault_events']
            if fault_file.exists():
                fault_events = await self.parse_fault_events(fault_file)
                processed_data['lstm_training_data']['fault_events'] = fault_events
                processed_data['file_processing_info']['files_processed'].append('fault_events')
            
            # Check if ready for training
            if (processed_data['lstm_training_data']['network_metrics'] and 
                len(processed_data['file_processing_info']['files_processed']) >= 2):
                processed_data['lstm_training_data']['ready_for_training'] = True
            
            self.monitoring_stats['data_points_collected'] += len(processed_data['lstm_training_data']['network_metrics'])
            
            return processed_data
            
        except Exception as e:
            logger.error(f"❌ Error processing simulation data: {e}")
            return None

    async def parse_network_metrics(self, metrics_file: Path) -> Dict[str, Any]:
        """PRESERVED: Parse network metrics CSV file"""
        metrics_data = {}
        try:
            async with aiofiles.open(metrics_file, 'r') as f:
                content = await f.read()
                lines = content.strip().split('\n')
                
                if len(lines) < 2:
                    return metrics_data
                
                # Parse header
                headers = lines[0].split(',')
                
                # Parse recent data points (last 100 lines for LSTM)
                recent_lines = lines[-100:] if len(lines) > 100 else lines[1:]
                
                for line in recent_lines:
                    values = line.split(',')
                    if len(values) >= len(headers):
                        node_id = values[1] if len(values) > 1 else 'unknown'
                        node_key = f"node_{node_id}"
                        
                        metrics_data[node_key] = {
                            'timestamp': float(values[0]) if values[0] else time.time(),
                            'node_id': node_id,
                            'throughput': float(values[3]) if len(values) > 3 and values[3] else 0.0,
                            'latency': float(values[4]) if len(values) > 4 and values[4] else 0.0,
                            'packet_loss': float(values[5]) if len(values) > 5 and values[5] else 0.0,
                            'cpu_usage': float(values[8]) if len(values) > 8 and values[8] else 0.0,
                            'memory_usage': float(values[9]) if len(values) > 9 and values[9] else 0.0,
                            'data_source': 'static_metrics_file'
                        }
                        
        except Exception as e:
            logger.error(f"❌ Error parsing network metrics: {e}")
        
        return metrics_data

    async def parse_fault_events(self, fault_file: Path) -> List[Dict[str, Any]]:
        """PRESERVED: Parse fault events log file"""
        fault_events = []
        try:
            async with aiofiles.open(fault_file, 'r') as f:
                content = await f.read()
                lines = content.strip().split('\n')
                
                for line in lines:
                    if line.strip():
                        parts = line.split(',')
                        if len(parts) >= 4:
                            fault_events.append({
                                'timestamp': float(parts[0]) if parts[0] else time.time(),
                                'event_type': parts[1],
                                'fault_type': parts[2],
                                'affected_nodes': parts[3].split(';') if parts[3] else [],
                                'description': parts[4] if len(parts) > 4 else '',
                                'data_source': 'static_fault_log'
                            })
                            
        except Exception as e:
            logger.error(f"❌ Error parsing fault events: {e}")
        
        return fault_events

    async def create_calculation_input(self, processed_data: Dict[str, Any]) -> Optional[Path]:
        """PRESERVED: Create input file for calculation agent"""
        try:
            timestamp = int(time.time())
            filename = f"calculation_input_{timestamp}.json"
            output_file = self.calculation_input_dir / filename
            
            async with aiofiles.open(output_file, 'w') as f:
                await f.write(json.dumps(processed_data, indent=2, default=str))
            
            self.monitoring_stats['files_processed'] += 1
            self.monitoring_stats['calculation_agent_notifications'] += 1
            logger.info(f"📄 Calculation input created: {filename}")
            
            return output_file
            
        except Exception as e:
            logger.error(f"❌ Error creating calculation input: {e}")
            return None

    async def notify_calculation_agent(self, data: Dict[str, Any], output_file: Path):
        """PRESERVED: Notify calculation agent of new data"""
        try:
            # Create notification file
            notification = {
                'notification_type': 'new_static_data_available',
                'timestamp': datetime.now().isoformat(),
                'source_agent': 'enhanced_monitor_agent',
                'target_agent': 'calculation_agent',  # ONLY calculation agent
                'data_file': str(output_file),
                'data_summary': {
                    'metrics_count': len(data.get('lstm_training_data', {}).get('network_metrics', {})),
                    'fault_events_count': len(data.get('lstm_training_data', {}).get('fault_events', [])),
                    'ready_for_training': data.get('lstm_training_data', {}).get('ready_for_training', False),
                    'data_source': 'static_files'
                },
                'processing_suggestions': {
                    'priority': 'normal',
                    'lstm_batch_processing': True,
                    'anomaly_detection_mode': 'batch_training'
                }
            }
            
            notification_file = self.calculation_input_dir / f"static_notification_{int(time.time())}.json"
            
            async with aiofiles.open(notification_file, 'w') as f:
                await f.write(json.dumps(notification, indent=2))
            
            logger.info(f"📨 Calculation agent notified of static data: {notification_file.name}")
            
        except Exception as e:
            logger.error(f"❌ Error notifying calculation agent: {e}")

    # **Enhanced monitoring and reporting**
    async def generate_monitoring_report(self):
        """Generate comprehensive monitoring report"""
        try:
            report = {
                'monitoring_report': {
                    'generated_timestamp': datetime.now().isoformat(),
                    'monitoring_duration': 'continuous',
                    'agent_version': '2.0_calculation_agent_only',
                    'data_flow': 'NS-3 → Monitor Agent → Calculation Agent ONLY',
                    'monitoring_status': {
                        'static_monitoring': self.static_monitoring_active,
                        'realtime_monitoring': self.realtime_monitoring_active,
                        'overall_status': 'active' if self.is_running else 'stopped'
                    }
                },
                'statistics': self.monitoring_stats,
                'file_tracking': {
                    'last_processed_files': len(self.last_processed),
                    'processed_files_set': len(self.processed_files),
                    'file_hashes_tracked': len(self.file_hashes)
                },
                'calculation_agent_communication': {
                    'total_notifications': self.monitoring_stats['calculation_agent_notifications'],
                    'realtime_faults_sent': self.monitoring_stats['realtime_events_processed'],
                    'static_data_sent': self.monitoring_stats['files_processed'],
                    'communication_directory': str(self.calculation_input_dir)
                }
            }
            
            report_file = self.monitoring_reports_dir / f"monitoring_report_{int(time.time())}.json"
            
            async with aiofiles.open(report_file, 'w') as f:
                await f.write(json.dumps(report, indent=2))
            
            logger.info(f"📊 Monitoring report generated: {report_file.name}")
            
        except Exception as e:
            logger.error(f"❌ Error generating monitoring report: {e}")

    async def periodic_reporting(self):
        """Generate reports every 5 minutes"""
        while self.is_running:
            try:
                await asyncio.sleep(300)  # 5 minutes
                await self.generate_monitoring_report()
                
                # Update stats
                self.monitoring_stats['last_update'] = datetime.now().isoformat()
                
                # Log current status
                logger.info(f"📊 Monitor Status - Static Files: {self.monitoring_stats['files_processed']}, "
                           f"Real-time Faults: {self.monitoring_stats['faults_detected']}, "
                           f"Calculation Agent Notifications: {self.monitoring_stats['calculation_agent_notifications']}")
                
            except Exception as e:
                logger.error(f"❌ Error in periodic reporting: {e}")

    # **ENHANCED: Main execution methods**
    async def start_monitoring(self):
        """Start both static and real-time monitoring"""
        logger.info("🚀 Starting Enhanced Monitor Agent...")
        logger.info("📊 Static Monitoring: Network Metrics + Fault Events + Config")
        logger.info("🔥 Real-time Monitoring: Live fault injection from NS-3")
        logger.info("📤 Target: ONLY Calculation Agent")
        logger.info("🔗 Data Flow: NS-3 → Monitor Agent → Calculation Agent → Healing Agent")
        
        # Initial scan
        file_status = await self.scan_essential_files()
        
        # Set running state
        self.is_running = True
        
        # Start all monitoring tasks
        tasks = [
            asyncio.create_task(self.static_file_monitoring()),     # Static file monitoring
            asyncio.create_task(self.monitor_realtime_faults()),    # Real-time fault monitoring
            asyncio.create_task(self.periodic_reporting())          # Periodic reporting
        ]
        
        logger.info("✅ Enhanced Monitor Agent started successfully")
        logger.info("⏰ Monitoring intervals: Static 10s, Real-time 10s, Reports 5min")
        logger.info("📤 All outputs directed to Calculation Agent only")
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("🛑 Shutdown requested")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Clean shutdown process"""
        logger.info("🧹 Cleaning up Enhanced Monitor Agent...")
        
        self.is_running = False
        
        # Generate final report
        await self.generate_monitoring_report()
        
        # Log final statistics
        logger.info("📊 Final Statistics:")
        for key, value in self.monitoring_stats.items():
            logger.info(f"  {key}: {value}")
        
        logger.info(f"📤 Total files sent to Calculation Agent: {self.monitoring_stats['calculation_agent_notifications']}")
        logger.info("✅ Enhanced Monitor Agent cleanup completed")


# **MAIN EXECUTION**
async def main():
    """Main execution function for Enhanced Monitor Agent"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize and start enhanced monitor agent
    monitor = EnhancedMonitorAgent()
    
    try:
        print('🏆 Enhanced Monitor Agent for ITU Competition')
        print('📊 Static File Monitoring: Traditional NS-3 output files')
        print('🔥 Real-time Monitoring: Live fault injection detection')
        print('📤 Target: ONLY Calculation Agent')
        print('🔗 Data Flow: NS-3 → Monitor Agent → Calculation Agent → Healing Agent')
        print('⏰ Monitoring Schedule:')
        print('  - Static files: Every 10 seconds')
        print('  - Real-time faults: Every 10 seconds')
        print('  - Status reports: Every 5 minutes')
        print('🚀 Starting enhanced monitoring...')
        
        await monitor.start_monitoring()
        
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown requested")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
    finally:
        if monitor.is_running:
            await monitor.cleanup()


if __name__ == '__main__':
    asyncio.run(main())