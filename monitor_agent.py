#!/usr/bin/env python3
"""
Enhanced Monitor Agent for ITU Competition Rural Network Simulation
ROBUST: Handles any number of NS-3 faults dynamically
EFFICIENT: Only processes real fault injections, no duplicates
COMPLETE: Preserves all existing functionalities
"""

import os
import json
import time
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
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
    
    ROBUST Features:
    - Handles ANY number of NS-3 faults (3, 4, 7, 100+)
    - Only processes REAL fault injections
    - No duplicate file creation
    - Smart fault detection and validation
    - Complete LSTM-ready data formatting
    - Reports ONLY to Calculation Agent
    """
    
    def __init__(self):
        # Directory structure
        self.ns3_simulation_dir = Path("/home/rishi/ns-allinone-3.44/ns-3.44")
        # OR better yet, detect current working directory:
        if Path("ns3_integration/agent_interface").exists():
            self.agent_interface_dir = Path("ns3_integration/agent_interface")
        else:
            self.agent_interface_dir = Path("/home/rishi/ns-allinone-3.44/ns-3.44/ns3_integration/agent_interface")        
        self.calculation_input_dir = Path("calculation_agent_input")
        self.monitoring_reports_dir = Path("calculation_agent_input/monitoring_reports")
        
        # Create directories
        for directory in [self.calculation_input_dir, self.monitoring_reports_dir, self.agent_interface_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Essential files from NS-3
        self.essential_files = {
            'network_metrics': 'itu_competition_network_metrics.csv',
            'fault_events': 'itu_competition_fault_events.log', 
            'topology': 'itu_competition_topology.json',
            'config': 'itu_competition_config.json'
        }
        
        # Real-time files from NS-3
        self.realtime_files = {
            'fault_events_realtime': self.agent_interface_dir / 'fault_events_realtime.json',
            'deployment_status': self.agent_interface_dir / 'deployment_status.json'
        }
        
        # ROBUST fault tracking
        self.last_processed = {}
        self.processed_fault_ids = set()  # Track processed fault IDs to avoid duplicates
        self.file_hashes = {}  # Track file content hashes
        self.last_file_sizes = {}  # Track file sizes for meaningful changes
        
        # Statistics
        self.monitoring_stats = {
            'files_processed': 0,
            'data_points_collected': 0,
            'real_faults_detected': 0,  # Only count REAL faults
            'realtime_events_processed': 0,
            'calculation_agent_notifications': 0,
            'duplicate_faults_avoided': 0,  # Track avoided duplicates
            'last_update': datetime.now().isoformat()
        }
        
        # State management
        self.is_running = False
        self.static_monitoring_active = False
        self.realtime_monitoring_active = False
        
        logger.info("✅ Enhanced ROBUST Monitor Agent initialized")
        logger.info(f"📁 Static monitoring: {self.ns3_simulation_dir}")
        logger.info(f"🔥 Real-time monitoring: {self.agent_interface_dir}")
        logger.info(f"📤 Reporting ONLY to Calculation Agent: {self.calculation_input_dir}")
        logger.info("🎯 ROBUST: Handles ANY number of faults dynamically")

    def generate_file_hash(self, file_path: Path) -> str:
        """Generate hash of file content to detect real changes"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""

    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"

    async def scan_essential_files(self) -> Dict[str, bool]:
        """Scan for essential simulation files"""
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

    async def has_meaningful_file_change(self, file_path: Path, min_size_change: int = 1024) -> bool:
        """Check if file has meaningful changes (size + content)"""
        try:
            if not file_path.exists():
                return False
            
            current_size = file_path.stat().st_size
            last_size = self.last_file_sizes.get(str(file_path), 0)
            
            # Check size change
            if current_size <= last_size + min_size_change:
                return False
            
            # Check content hash
            current_hash = self.generate_file_hash(file_path)
            last_hash = self.file_hashes.get(str(file_path), "")
            
            if current_hash == last_hash:
                return False
            
            # Update tracking
            self.last_file_sizes[str(file_path)] = current_size
            self.file_hashes[str(file_path)] = current_hash
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error checking file changes: {e}")
            return False

    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate processed data before sending to calculation agent"""
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
            
            logger.info("✅ Data validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Data validation error: {e}")
            return False

    async def monitor_realtime_faults(self):
        """ROBUST: Monitor for ANY number of real-time fault injections from NS-3"""
        logger.info("🔥 Starting ROBUST real-time fault monitoring...")
        logger.info("🎯 Handles ANY number of faults: 1, 3, 5, 10, 100+")
        self.realtime_monitoring_active = True
        
        while self.is_running:
            try:
                fault_events_file = self.realtime_files['fault_events_realtime']
                
                if not fault_events_file.exists():
                    logger.debug("📄 No real-time fault file found yet")
                    await asyncio.sleep(10)
                    continue
                
                # Check for meaningful file changes
                if not await self.has_meaningful_file_change(fault_events_file, min_size_change=100):
                    logger.debug("📄 No meaningful fault file changes")
                    await asyncio.sleep(10)
                    continue
                
                # Read and validate fault data
                try:
                    async with aiofiles.open(fault_events_file, 'r') as f:
                        content = await f.read()
                    
                    if not content.strip():
                        logger.debug("📄 Fault file is empty")
                        await asyncio.sleep(10)
                        continue
                    
                    fault_data = json.loads(content)
                    events = fault_data.get('events', [])
                    
                    if not events:
                        logger.debug("📄 No fault events in file")
                        await asyncio.sleep(10)
                        continue
                    
                    # Process only NEW fault events
                    new_events = []
                    for event in events:
                        event_id = event.get('event_id', f"evt_{event.get('timestamp', time.time())}")
                        if event_id not in self.processed_fault_ids:
                            new_events.append(event)
                            self.processed_fault_ids.add(event_id)
                        else:
                            self.monitoring_stats['duplicate_faults_avoided'] += 1
                    
                    if new_events:
                        logger.info(f"🚨 REAL fault injection detected! New events: {len(new_events)}")
                        logger.info(f"📊 Event IDs: {[e.get('event_id', 'unknown') for e in new_events]}")
                        
                        # Process the new real fault events
                        fault_data_new = {'events': new_events, **{k: v for k, v in fault_data.items() if k != 'events'}}
                        await self.process_realtime_fault_event_robust(fault_data_new)
                        
                        self.monitoring_stats['real_faults_detected'] += len(new_events)
                        self.monitoring_stats['realtime_events_processed'] += 1
                    else:
                        logger.debug("📄 All fault events already processed")
                    
                except json.JSONDecodeError as e:
                    logger.debug(f"📄 Fault file not valid JSON yet: {e}")
                except Exception as e:
                    logger.error(f"❌ Error reading fault file: {e}")
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"❌ Real-time fault monitoring error: {e}")
                await asyncio.sleep(5)
        
        self.realtime_monitoring_active = False
        logger.info("🛑 ROBUST real-time fault monitoring stopped")

    async def process_realtime_fault_event_robust(self, fault_data: Dict[str, Any]):
        """Process real-time fault events and send ONLY to Calculation Agent"""
        try:
            timestamp = int(time.time())
            events = fault_data.get('events', [])
            
            logger.info(f"🔄 Processing {len(events)} real fault events...")
            
            # Create file for Calculation Agent with REAL fault data
            calc_file = self.calculation_input_dir / f"realtime_fault_{timestamp}.json"
            calc_data = await self.format_for_calculation_agent_robust(fault_data, is_realtime=True)
            
            # Only create file if there are actual faults
            if calc_data['fault_analysis']['fault_count'] > 0:
                async with aiofiles.open(calc_file, 'w') as f:
                    await f.write(json.dumps(calc_data, indent=2))
                
                self.monitoring_stats['calculation_agent_notifications'] += 1
                
                logger.info(f"📤 Real fault data sent to Calculation Agent: {calc_file.name}")
                logger.info(f"📊 Fault types: {calc_data['fault_analysis']['fault_types']}")
                logger.info(f"📊 Affected nodes: {calc_data['fault_analysis']['affected_node_count']}")
                
                # Create notification for calculation agent
                await self.notify_calculation_agent_of_realtime_fault_robust(calc_data, calc_file)
            else:
                logger.warning("⚠️ No valid faults to process")
            
        except Exception as e:
            logger.error(f"❌ Error processing real-time fault: {e}")

    async def format_for_calculation_agent_robust(self, fault_data: dict, is_realtime: bool = False) -> dict:
        """ROBUST: Format fault data for LSTM Calculation Agent"""
        events = fault_data.get('events', [])
        
        # Enhanced format compatible with calculation agent
        formatted_data = {
            'monitor_metadata': {
                'generated_timestamp': datetime.now().isoformat(),
                'source_agent': 'enhanced_monitor_agent_robust',
                'target_agent': 'calculation_agent',
                'data_type': 'realtime_fault' if is_realtime else 'static_simulation',
                'data_version': '2.0',
                'processing_priority': 'high' if is_realtime else 'normal'
            },
            'lstm_training_data': {
                'network_metrics': {},
                'fault_events': [],
                'ready_for_training': True,
                'data_quality': 'high',
                'sequence_length': 50,
                'data_source': 'realtime_ns3' if is_realtime else 'static_files'
            },
            'fault_analysis': {
                'fault_detected': len(events) > 0,
                'fault_count': len(events),
                'severity_levels': [],
                'fault_types': [],
                'affected_node_count': 0,
                'requires_immediate_processing': is_realtime,
                'fault_event_ids': []  # Track processed fault IDs
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
        
        # Process each REAL fault event
        for event in events:
            event_id = event.get('event_id', f"evt_{int(time.time())}")
            affected_nodes = event.get('affected_nodes', [])
            fault_type = event.get('fault_type', 'unknown')
            severity = event.get('severity', 0.0)
            
            # Add to fault events
            formatted_data['lstm_training_data']['fault_events'].append({
                'event_id': event_id,
                'timestamp': event.get('timestamp', time.time()),
                'node_ids': affected_nodes,
                'fault_type': fault_type,
                'severity': severity,
                'description': event.get('description', ''),
                'requires_immediate_action': severity > 0.8
            })
            
            # Track fault analysis
            formatted_data['fault_analysis']['severity_levels'].append(severity)
            formatted_data['fault_analysis']['fault_event_ids'].append(event_id)
            
            if fault_type not in formatted_data['fault_analysis']['fault_types']:
                formatted_data['fault_analysis']['fault_types'].append(fault_type)
            
            # Set anomaly detection context based on severity
            if severity > 0.8:
                formatted_data['anomaly_detection_context']['requires_immediate_action'] = True
                formatted_data['anomaly_detection_context']['expected_anomaly_score'] = 0.95
            
            # Create enhanced network metrics for affected nodes
            for node_id in affected_nodes:
                affected_nodes_set.add(node_id)
                node_key = f"node_{node_id:02d}" if isinstance(node_id, int) else str(node_id)
                
                # Base metrics with fault impact
                base_metrics = {
                    'timestamp': time.time(),
                    'node_id': node_id,
                    'fault_severity': severity,
                    'fault_type': fault_type,
                    'event_id': event_id,
                    'data_source': 'realtime_fault_injection' if is_realtime else 'static_simulation',
                    'monitoring_agent_confidence': 0.95
                }
                
                # Apply fault-specific metrics
                if fault_type == "fiber_cut":
                    base_metrics.update({
                        'throughput': 50.0 * (1.0 - severity * 0.8),
                        'latency': 10.0 * (1.0 + severity * 2.0),
                        'packet_loss': 0.01 + severity * 0.3,
                        'jitter': 1.0 * (1.0 + severity * 1.5),
                        'connectivity_status': 'degraded' if severity > 0.5 else 'stable'
                    })
                elif fault_type == "power_fluctuation":
                    base_metrics.update({
                        'power_stability': 0.9 * (1.0 - severity * 0.5),
                        'voltage_level': 0.95 * (1.0 - severity * 0.2),
                        'energy_level': 0.8 * (1.0 - severity * 0.1),
                        'power_status': 'unstable' if severity > 0.6 else 'stable'
                    })
                
                formatted_data['lstm_training_data']['network_metrics'][node_key] = base_metrics
        
        # Update affected node count
        formatted_data['fault_analysis']['affected_node_count'] = len(affected_nodes_set)
        
        return formatted_data

    async def notify_calculation_agent_of_realtime_fault_robust(self, calc_data: Dict[str, Any], calc_file: Path):
        """ROBUST: Notify calculation agent of new real-time fault data"""
        try:
            # Handle empty severity_levels safely
            severity_levels = calc_data.get('fault_analysis', {}).get('severity_levels', [])
            max_severity = max(severity_levels) if severity_levels else 0.0
            
            notification = {
                'notification_type': 'realtime_fault_detected',
                'timestamp': datetime.now().isoformat(),
                'source_agent': 'enhanced_monitor_agent_robust',
                'target_agent': 'calculation_agent',
                'priority': 'high',
                'data_file': str(calc_file),
                'fault_summary': {
                    'fault_count': calc_data.get('fault_analysis', {}).get('fault_count', 0),
                    'affected_nodes': calc_data.get('fault_analysis', {}).get('affected_node_count', 0),
                    'max_severity': max_severity,
                    'fault_types': calc_data.get('fault_analysis', {}).get('fault_types', []),
                    'fault_event_ids': calc_data.get('fault_analysis', {}).get('fault_event_ids', []),
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
            
            logger.info(f"📨 Calculation agent notified: {notification_file.name}")
            
        except Exception as e:
            logger.error(f"❌ Error notifying calculation agent: {e}")

    async def static_file_monitoring_robust(self):
        """ROBUST: Static file monitoring with intelligent change detection"""
        logger.info("📊 Starting ROBUST static file monitoring...")
        self.static_monitoring_active = True
        
        while self.is_running:
            try:
                significant_changes = []
                
                # Check each essential file for meaningful changes
                for file_type, filename in self.essential_files.items():
                    file_path = self.ns3_simulation_dir / filename
                    
                    if file_path.exists():
                        # Check for meaningful changes (>2KB for metrics, >100B for others)
                        min_change = 2048 if file_type == 'network_metrics' else 100
                        
                        if await self.has_meaningful_file_change(file_path, min_change):
                            significant_changes.append(file_type)
                            logger.info(f"🔄 Significant change detected in {filename}")
                
                # Only process if there are meaningful changes
                if significant_changes:
                    logger.info(f"⟳ Processing static data changes: {significant_changes}")
                    
                    processed_data = await self.process_simulation_data_robust()
                    
                    if processed_data and self.validate_data(processed_data):
                        # Only create files if there's substantial new data
                        metrics_count = len(processed_data.get('lstm_training_data', {}).get('network_metrics', {}))
                        if metrics_count > 10:  # Minimum threshold for meaningful data
                            output_file = await self.create_calculation_input(processed_data)
                            
                            if output_file:
                                await self.notify_calculation_agent(processed_data, output_file)
                        else:
                            logger.debug(f"⚠️ Insufficient data points: {metrics_count}")
                    else:
                        logger.warning("⚠️ Data validation failed")
                else:
                    logger.debug("📄 No significant static file changes")
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"❌ Static monitoring error: {e}")
                await asyncio.sleep(10)
        
        self.static_monitoring_active = False
        logger.info("🛑 ROBUST static file monitoring stopped")

    async def process_simulation_data_robust(self) -> Optional[Dict[str, Any]]:
        """Process simulation data from static files"""
        try:
            processed_data = {
                'monitor_metadata': {
                    'generated_timestamp': datetime.now().isoformat(),
                    'source_agent': 'enhanced_monitor_agent_robust',
                    'target_agent': 'calculation_agent',
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
                len(processed_data['file_processing_info']['files_processed']) >= 1):
                processed_data['lstm_training_data']['ready_for_training'] = True
            
            self.monitoring_stats['data_points_collected'] += len(processed_data['lstm_training_data']['network_metrics'])
            
            return processed_data
            
        except Exception as e:
            logger.error(f"❌ Error processing simulation data: {e}")
            return None

    async def parse_network_metrics(self, metrics_file: Path) -> Dict[str, Any]:
        """Parse network metrics CSV file"""
        metrics_data = {}
        try:
            async with aiofiles.open(metrics_file, 'r') as f:
                content = await f.read()
                lines = content.strip().split('\n')
                
                if len(lines) < 2:
                    return metrics_data
                
                # Parse recent data points (last 50 lines)
                recent_lines = lines[-50:] if len(lines) > 50 else lines[1:]
                
                for line in recent_lines:
                    values = line.split(',')
                    if len(values) >= 4:
                        node_id = values[1] if len(values) > 1 else 'unknown'
                        node_key = f"node_{node_id}"
                        
                        metrics_data[node_key] = {
                            'timestamp': float(values[0]) if values[0] else time.time(),
                            'node_id': node_id,
                            'throughput': float(values[3]) if len(values) > 3 and values[3] else 0.0,
                            'latency': float(values[4]) if len(values) > 4 and values[4] else 0.0,
                            'packet_loss': float(values[5]) if len(values) > 5 and values[5] else 0.0,
                            'data_source': 'static_metrics_file'
                        }
                        
        except Exception as e:
            logger.error(f"❌ Error parsing network metrics: {e}")
        
        return metrics_data

    async def parse_fault_events(self, fault_file: Path) -> List[Dict[str, Any]]:
        """Parse fault events log file"""
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
        """Create input file for calculation agent"""
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
        """Notify calculation agent of new data"""
        try:
            notification = {
                'notification_type': 'new_static_data_available',
                'timestamp': datetime.now().isoformat(),
                'source_agent': 'enhanced_monitor_agent_robust',
                'target_agent': 'calculation_agent',
                'data_file': str(output_file),
                'data_summary': {
                    'metrics_count': len(data.get('lstm_training_data', {}).get('network_metrics', {})),
                    'fault_events_count': len(data.get('lstm_training_data', {}).get('fault_events', [])),
                    'ready_for_training': data.get('lstm_training_data', {}).get('ready_for_training', False),
                    'data_source': 'static_files'
                }
            }
            
            notification_file = self.calculation_input_dir / f"static_notification_{int(time.time())}.json"
            
            async with aiofiles.open(notification_file, 'w') as f:
                await f.write(json.dumps(notification, indent=2))
            
            logger.info(f"📨 Calculation agent notified: {notification_file.name}")
            
        except Exception as e:
            logger.error(f"❌ Error notifying calculation agent: {e}")

    async def generate_monitoring_report(self):
        """Generate comprehensive monitoring report"""
        try:
            report = {
                'monitoring_report': {
                    'generated_timestamp': datetime.now().isoformat(),
                    'agent_version': 'robust_2.0',
                    'monitoring_status': {
                        'static_monitoring': self.static_monitoring_active,
                        'realtime_monitoring': self.realtime_monitoring_active,
                        'overall_status': 'active' if self.is_running else 'stopped'
                    }
                },
                'statistics': self.monitoring_stats,
                'fault_tracking': {
                    'processed_fault_ids': len(self.processed_fault_ids),
                    'duplicate_faults_avoided': self.monitoring_stats['duplicate_faults_avoided'],
                    'file_hashes_tracked': len(self.file_hashes)
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
                logger.info(f"📊 ROBUST Monitor Status:")
                logger.info(f"   Real faults detected: {self.monitoring_stats['real_faults_detected']}")
                logger.info(f"   Duplicates avoided: {self.monitoring_stats['duplicate_faults_avoided']}")
                logger.info(f"   Static files processed: {self.monitoring_stats['files_processed']}")
                logger.info(f"   Total notifications: {self.monitoring_stats['calculation_agent_notifications']}")
                
            except Exception as e:
                logger.error(f"❌ Error in periodic reporting: {e}")

    async def start_monitoring(self):
        """Start both static and real-time monitoring"""
        logger.info("🚀 Starting ROBUST Enhanced Monitor Agent...")
        logger.info("📊 Static Monitoring: Intelligent change detection")
        logger.info("🔥 Real-time Monitoring: Handles ANY number of faults")
        logger.info("📤 Target: ONLY Calculation Agent")
        logger.info("🎯 ROBUST: No duplicate files, only REAL faults")
        
        # Initial scan
        file_status = await self.scan_essential_files()
        
        # Set running state
        self.is_running = True
        
        # Start all monitoring tasks
        tasks = [
            asyncio.create_task(self.static_file_monitoring_robust()),
            asyncio.create_task(self.monitor_realtime_faults()),
            asyncio.create_task(self.periodic_reporting())
        ]
        
        logger.info("✅ ROBUST Enhanced Monitor Agent started successfully")
        logger.info("⏰ Monitoring intervals: Static 30s, Real-time 10s, Reports 5min")
        logger.info("🎯 Ready to handle ANY number of NS-3 faults dynamically")
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("🛑 Shutdown requested")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Clean shutdown process"""
        logger.info("🧹 Cleaning up ROBUST Enhanced Monitor Agent...")
        
        self.is_running = False
        
        # Generate final report
        await self.generate_monitoring_report()
        
        # Log final statistics
        logger.info("📊 Final ROBUST Statistics:")
        for key, value in self.monitoring_stats.items():
            logger.info(f"  {key}: {value}")
        
        logger.info(f"🎯 Real faults detected: {self.monitoring_stats['real_faults_detected']}")
        logger.info(f"🛡️ Duplicates avoided: {self.monitoring_stats['duplicate_faults_avoided']}")
        logger.info("✅ ROBUST Enhanced Monitor Agent cleanup completed")


# MAIN EXECUTION
async def main():
    """Main execution function for ROBUST Enhanced Monitor Agent"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize and start robust monitor agent
    monitor = EnhancedMonitorAgent()
    
    try:
        print('🏆 ROBUST Enhanced Monitor Agent for ITU Competition')
        print('🎯 Handles ANY number of NS-3 faults: 1, 3, 5, 10, 100+')
        print('📊 Intelligent file monitoring: Only meaningful changes')
        print('🔥 Real-time fault detection: Only REAL fault injections')
        print('🛡️ Duplicate prevention: Advanced fault ID tracking')
        print('📤 Target: ONLY Calculation Agent')
        print('⏰ Monitoring Schedule:')
        print('  - Static files: Every 30 seconds (meaningful changes only)')
        print('  - Real-time faults: Every 10 seconds (real faults only)')
        print('  - Status reports: Every 5 minutes')
        print('🚀 Starting ROBUST monitoring...')
        
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