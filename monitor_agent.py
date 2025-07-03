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
        self.agent_interface_dir = Path("/media/rishi/Windows-SSD/PROJECT_&_RESEARCH/NOKIA/Buil-a-thon/rural_ai_selfhealing_net/ns3_integration/agent_interface")
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
        
        # ✅ ENHANCED: File state tracking for proper change detection
        self.processed_file_states = {}  # Track file states (size + mtime + hash)
        self.start_time = time.time()  # Track start time for debug logging
        
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
        """FIXED: Monitor with proper file tracking to avoid repeated processing"""
        logger.info("🔥 Starting ROBUST real-time fault monitoring...")
        logger.info("🎯 Handles ANY number of faults: 1, 3, 5, 10, 100+")
        logger.info("🛡️ Enhanced validation: Ignores empty/invalid faults")
        self.realtime_monitoring_active = True
        
        while self.is_running:
            try:
                # **Check for individual fault files first**
                if self.agent_interface_dir.exists():
                    fault_files = list(self.agent_interface_dir.glob("fault_*.json"))
                    
                    for fault_file in fault_files:
                        try:
                            # ✅ ENHANCED: Check file state (size + mtime + hash)
                            current_size = fault_file.stat().st_size
                            current_mtime = fault_file.stat().st_mtime
                            
                            file_key = str(fault_file)
                            last_state = self.processed_file_states.get(file_key, {})
                            
                            # Only process if file has meaningful changes
                            if (current_size != last_state.get('size', -1) or 
                                current_mtime != last_state.get('mtime', -1)) and current_size > 10:
                                
                                # Read and check content hash
                                try:
                                    async with aiofiles.open(fault_file, 'r') as f:
                                        content = await f.read()
                                    
                                    if not content.strip():
                                        logger.debug(f"📄 {fault_file.name} is empty")
                                        continue
                                    
                                    content_hash = hashlib.md5(content.encode()).hexdigest()
                                    
                                    if content_hash == last_state.get('hash', ''):
                                        logger.debug(f"📄 {fault_file.name} content unchanged")
                                        continue
                                    
                                    # ✅ NEW CONTENT: Process the fault
                                    logger.info(f"📄 Processing NEW fault content: {fault_file.name}")
                                    
                                    fault_data = json.loads(content)
                                    await self.process_individual_fault_data(fault_file, fault_data)
                                    
                                    # Update tracking state
                                    self.processed_file_states[file_key] = {
                                        'size': current_size,
                                        'mtime': current_mtime,
                                        'hash': content_hash
                                    }
                                    
                                except json.JSONDecodeError as e:
                                    logger.debug(f"📄 {fault_file.name} not valid JSON: {e}")
                                except Exception as e:
                                    logger.error(f"❌ Error processing {fault_file.name}: {e}")
                            else:
                                logger.debug(f"📄 {fault_file.name} no changes detected")
                                
                        except Exception as e:
                            logger.error(f"❌ Error checking {fault_file}: {e}")

                # **Also check main fault events file**
                fault_events_file = self.realtime_files['fault_events_realtime']
                if fault_events_file.exists():
                    await self.check_main_fault_events_file(fault_events_file)

                await asyncio.sleep(10)  # Check every 10 seconds

            except Exception as e:
                logger.error(f"❌ Real-time fault monitoring error: {e}")
                await asyncio.sleep(5)

        self.realtime_monitoring_active = False
        logger.info("🛑 ROBUST real-time fault monitoring stopped")

    async def process_individual_fault_data(self, fault_file: Path, fault_data: dict):
        """Process individual fault file data with enhanced validation"""
        try:
        # Extract fault information
            event_id = fault_data.get('event_id', f"evt_{fault_file.stem}_{int(time.time())}")
            fault_type = fault_data.get('fault_type', 'unknown')
            affected_nodes = fault_data.get('affected_nodes', [])
            severity = fault_data.get('severity', 0.0)
            description = fault_data.get('description', '')
            timestamp = fault_data.get('timestamp', time.time())
        
        # ✅ ENHANCED VALIDATION: More specific checks
            is_valid_fault = (
            fault_type != 'unknown' and
            fault_type.strip() != '' and
            isinstance(affected_nodes, list) and
            len(affected_nodes) > 0 and
            all(isinstance(node, (int, str)) for node in affected_nodes) and
            isinstance(severity, (int, float)) and
            severity > 0.0 and
            description.strip() != ''
            )
        
            if not is_valid_fault:
                logger.debug(f"📄 Invalid fault data in {fault_file.name}")
                return
        
        # Check if already processed
            if event_id in self.processed_fault_ids:
                logger.debug(f"📄 Fault {event_id} already processed")
                self.monitoring_stats['duplicate_faults_avoided'] += 1
                return
        
        # ✅ PROCESS VALID FAULT
            logger.info(f"🚨 Processing VALID fault: {event_id}")
            logger.info(f"   Type: {fault_type}")
            logger.info(f"   Affected Nodes: {affected_nodes}")
            logger.info(f"   Severity: {severity}")
            logger.info(f"   Description: {description}")
        
        # ✅ NEW: Send fault data in DIRECT format (not wrapped in lstm_training_data)
            await self.send_direct_fault_to_calculation_agent(fault_data)
        
        # Mark as processed
            self.processed_fault_ids.add(event_id)
            self.monitoring_stats['real_faults_detected'] += 1
        
            logger.info(f"✅ VALID fault processed successfully: {event_id}")
        
        except Exception as e:
            logger.error(f"❌ Error processing fault data from {fault_file}: {e}")

    # ✅ ADD THIS MISSING METHOD:
    async def notify_calculation_agent_of_direct_fault(self, fault_data: dict, calc_file: Path):
        """Notify calculation agent of direct fault data"""
        try:
            affected_nodes = fault_data.get('affected_nodes', [])
            fault_types = [fault_data.get('fault_type', 'unknown')]
            severity = fault_data.get('severity', 0.0)
        
            notification = {
            'notification_type': 'realtime_fault_detected',
            'timestamp': datetime.now().isoformat(),
            'source_agent': 'enhanced_monitor_agent_robust',
            'target_agent': 'calculation_agent',
            'priority': 'high',
            'data_file': str(calc_file),
            'fault_summary': {
                'fault_count': 1,
                'affected_nodes': len(affected_nodes),  # Send count, not list
                'max_severity': severity,
                'fault_types': fault_types,
                'fault_event_ids': [fault_data.get('event_id', 'unknown')],
                'requires_immediate_action': True  # ✅ Always true for real faults
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

    async def send_direct_fault_to_calculation_agent(self, fault_data: dict):
        """Send fault data in direct format that calculation agent expects"""
        try:
            timestamp = int(time.time())
        
        # ✅ DIRECT FAULT FORMAT (not wrapped in lstm_training_data)
            direct_fault_data = {
            "fault_type": fault_data.get("fault_type"),
            "affected_nodes": fault_data.get("affected_nodes"),
            "severity": fault_data.get("severity"),
            "timestamp": fault_data.get("timestamp", timestamp),
            "event_id": fault_data.get("event_id"),
            "description": fault_data.get("description"),
            "requires_immediate_action": True,  # Always true for real faults
            "event_type": fault_data.get("event_type", "fault_started"),
            "visual_effect": fault_data.get("visual_effect", "")
            }
        
        # Create direct fault file
            calc_file = self.calculation_input_dir / f"realtime_fault_{timestamp}.json"
            async with aiofiles.open(calc_file, 'w') as f:
                await f.write(json.dumps(direct_fault_data, indent=2))
        
            logger.info(f"📤 Direct fault data sent to Calculation Agent: {calc_file.name}")
        
        # Also create notification
            await self.notify_calculation_agent_of_direct_fault(direct_fault_data, calc_file)
        
        except Exception as e:
            logger.error(f"❌ Error sending direct fault: {e}")

    async def check_main_fault_events_file(self, fault_events_file: Path):
        """Check main fault events file with proper state tracking"""
        try:
            file_key = str(fault_events_file)
            current_size = fault_events_file.stat().st_size
            current_mtime = fault_events_file.stat().st_mtime
            
            last_state = self.processed_file_states.get(file_key, {})
            
            # Only process if file has meaningful changes
            if (current_size != last_state.get('size', -1) or 
                current_mtime != last_state.get('mtime', -1)) and current_size > 10:
                
                async with aiofiles.open(fault_events_file, 'r') as f:
                    content = await f.read()
                
                if content.strip():
                    content_hash = hashlib.md5(content.encode()).hexdigest()
                    
                    if content_hash != last_state.get('hash', ''):
                        logger.info(f"📄 Processing updated main fault file")
                        
                        fault_data = json.loads(content)
                        events = fault_data.get('events', [])
                        
                        if events:
                            for event in events:
                                await self.process_individual_fault_data(fault_events_file, events[0])
                        
                        self.processed_file_states[file_key] = {
                            'size': current_size,
                            'mtime': current_mtime,
                            'hash': content_hash
                        }
        
        except Exception as e:
            logger.debug(f"Error checking main fault file: {e}")

    async def log_fault_detection_debug(self):
        """Enhanced debug logging for fault detection timing"""
        while self.is_running:
            try:
                current_real_time = time.time()
                
                # Check NS-3 metrics file for simulation progress
                metrics_file = self.ns3_simulation_dir / self.essential_files['network_metrics']
                simulation_time = 0.0
                
                if metrics_file.exists():
                    try:
                        # Read last few lines to get current simulation time
                        with open(metrics_file, 'r') as f:
                            lines = f.readlines()
                        
                        if len(lines) > 1:
                            last_line = lines[-1].strip()
                            if last_line and ',' in last_line:
                                simulation_time = float(last_line.split(',')[0])
                    except Exception:
                        pass
                
                # Check for fault files
                fault_files_count = 0
                if self.agent_interface_dir.exists():
                    fault_files = list(self.agent_interface_dir.glob("*.json"))
                    fault_files_count = len(fault_files)
                    
                    # Show file details
                    for file in fault_files:
                        if file.exists():
                            size = file.stat().st_size
                            mtime = file.stat().st_mtime
                            logger.debug(f"   📄 {file.name}: {size} bytes, modified {mtime}")
                
                logger.info(f"⏰ Debug Status:")
                logger.info(f"   🕐 Real time elapsed: {current_real_time - self.start_time:.1f}s")
                logger.info(f"   🕐 NS-3 simulation time: {simulation_time:.1f}s")
                logger.info(f"   📁 Fault files found: {fault_files_count}")
                logger.info(f"   🚨 Real faults detected: {self.monitoring_stats['real_faults_detected']}")
                logger.info(f"   🛡️ Duplicates avoided: {self.monitoring_stats['duplicate_faults_avoided']}")
                
                await asyncio.sleep(30)  # Debug every 30 seconds
                
            except Exception as e:
                logger.error(f"❌ Debug logging error: {e}")
                await asyncio.sleep(5)

    async def process_individual_fault_files(self, fault_files: List[Path]):
        """Process individual fault files detected from NS-3 with VALIDATION"""
        try:
            for fault_file in fault_files:
                logger.info(f"📄 Processing individual fault file: {fault_file.name}")
                try:
                    async with aiofiles.open(fault_file, 'r') as f:
                        content = await f.read()
                    
                    if not content.strip():
                        logger.debug(f"📄 Fault file {fault_file.name} is empty - SKIPPING")
                        continue

                    fault_data = json.loads(content)
                    
                    # **ENHANCED VALIDATION: Check for meaningful fault data**
                    event_id = fault_data.get('event_id', f"evt_{fault_file.stem}")
                    fault_type = fault_data.get('fault_type', 'unknown')
                    affected_nodes = fault_data.get('affected_nodes', [])
                    severity = fault_data.get('severity', 0.0)
                    description = fault_data.get('description', '')
                    
                    # **SKIP INVALID/EMPTY FAULTS**
                    if (fault_type == 'unknown' or 
                        not affected_nodes or 
                        len(affected_nodes) == 0 or
                        severity == 0.0 or
                        not description.strip()):
                        logger.debug(f"📄 Fault file {fault_file.name} contains invalid/empty data - SKIPPING")
                        logger.debug(f"   Type: {fault_type}, Nodes: {affected_nodes}, Severity: {severity}")
                        continue
                    
                    # **ONLY PROCESS VALID FAULTS**
                    if event_id not in self.processed_fault_ids:
                        logger.info(f"🚨 Processing VALID individual fault: {event_id}")
                        logger.info(f"   Type: {fault_type}, Nodes: {affected_nodes}, Severity: {severity}")
                        
                        # Convert individual fault to events format
                        events_data = {
                            'timestamp': fault_data.get('timestamp', time.time()),
                            'events': [fault_data]
                        }

                        # Process as real-time fault
                        await self.process_realtime_fault_event_robust(events_data)

                        # Mark as processed
                        self.processed_fault_ids.add(event_id)
                        self.processed_fault_ids.add(fault_file)
                        self.monitoring_stats['real_faults_detected'] += 1
                        logger.info(f"✅ VALID fault processed: {event_id}")
                    else:
                        logger.debug(f"📄 Fault {event_id} already processed")
                        self.monitoring_stats['duplicate_faults_avoided'] += 1

                except json.JSONDecodeError as e:
                    logger.debug(f"📄 Fault file {fault_file.name} not valid JSON yet: {e}")
                except Exception as e:
                    logger.error(f"❌ Error processing fault file {fault_file.name}: {e}")

        except Exception as e:
            logger.error(f"❌ Error processing individual fault files: {e}")

    # ✅ REPLACE EXISTING METHOD:
    async def process_realtime_fault_event_robust(self, fault_data: Dict[str, Any]):
        """UPDATED: Process real-time fault events and send DIRECT format to Calculation Agent"""
        try:
            timestamp = int(time.time())
            events = fault_data.get('events', [])
        
            logger.info(f"🔄 Processing {len(events)} real fault events...")
        
        # ✅ Process each event individually in direct format
            for event in events:
                await self.send_direct_fault_to_calculation_agent(event)
        
            self.monitoring_stats['calculation_agent_notifications'] += len(events)
        
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
                'requires_immediate_action': True,
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
                        'connectivity_status': 'degraded' if severity > 0.5 else 'stable',
                        # **ADD ALL MISSING FEATURES:**
                        'signal_strength': -60.0 * (1.0 + severity * 0.2),
                        'cpu_usage': 0.3 + severity * 0.1,
                        'memory_usage': 0.4 + severity * 0.1,
                        'buffer_occupancy': 0.2 + severity * 0.3,
                        'active_links': max(1, int(3 * (1.0 - severity))),
                        'neighbor_count': max(1, int(4 * (1.0 - severity))),
                        'link_utilization': 0.5 + severity * 0.4,
                        'critical_load': 0.25 + severity * 0.3,
                        'normal_load': 0.6 + severity * 0.2,
                        'energy_level': 0.8 - severity * 0.1,
                        'x_position': float(node_id * 100),  # Default positioning
                        'y_position': float(node_id * 50),
                        'z_position': 0.0,
                        'power_stability': 0.9 - severity * 0.1,
                        'voltage_level': 0.95 - severity * 0.05
                    })
                elif fault_type == "power_fluctuation":
                    base_metrics.update({
                        'power_stability': 0.9 * (1.0 - severity * 0.5),
                        'voltage_level': 0.95 * (1.0 - severity * 0.2),
                        'energy_level': 0.8 * (1.0 - severity * 0.1),
                        'power_status': 'unstable' if severity > 0.6 else 'stable',
                        # **ADD ALL OTHER FEATURES:**
                        'throughput': 50.0 * (1.0 - severity * 0.3),
                        'latency': 10.0 * (1.0 + severity * 1.0),
                        'packet_loss': 0.01 + severity * 0.1,
                        'jitter': 1.0 * (1.0 + severity * 0.8),
                        'signal_strength': -60.0 * (1.0 + severity * 0.1),
                        'cpu_usage': 0.3 + severity * 0.2,
                        'memory_usage': 0.4 + severity * 0.15,
                        'buffer_occupancy': 0.2 + severity * 0.2,
                        'active_links': max(1, int(3 * (1.0 - severity * 0.3))),
                        'neighbor_count': max(1, int(4 * (1.0 - severity * 0.2))),
                        'link_utilization': 0.5 + severity * 0.2,
                        'critical_load': 0.25 + severity * 0.2,
                        'normal_load': 0.6 + severity * 0.1,
                        'x_position': float(node_id * 100),
                        'y_position': float(node_id * 50),
                        'z_position': 0.0
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
                    'requires_immediate_action': calc_data.get('anomaly_detection_context', {}).get('requires_immediate_action', True)
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
        """Parse network metrics CSV file with ALL required LSTM features"""
        metrics_data = {}
        try:
            async with aiofiles.open(metrics_file, 'r') as f:
                content = await f.read()
            
            lines = content.strip().split('\n')
            if len(lines) < 2:
                return metrics_data
            
            # Parse header to understand column structure
            header = lines[0].split(',')
            logger.info(f"📊 CSV Header: {header}")
            
            # Parse recent data points (last 50 lines)
            recent_lines = lines[-50:] if len(lines) > 50 else lines[1:]
            
            for line in recent_lines:
                values = line.split(',')
                if len(values) >= len(header):
                    # Map CSV columns to expected features
                    node_id = values[1] if len(values) > 1 else 'unknown'
                    node_key = f"node_{node_id}"
                    
                    # **UPDATED: Extract ALL 21 required features**
                    metrics_data[node_key] = {
                        'timestamp': float(values[0]) if values[0] else time.time(),
                        'node_id': node_id,
                        # Core network metrics (columns 3-6)
                        'throughput': float(values[3]) if len(values) > 3 and values[3] else 0.0,
                        'latency': float(values[4]) if len(values) > 4 and values[4] else 0.0,
                        'packet_loss': float(values[5]) if len(values) > 5 and values[5] else 0.0,
                        'jitter': float(values[6]) if len(values) > 6 and values[6] else 0.0,
                        # Signal and system metrics (columns 7-10)
                        'signal_strength': float(values[7]) if len(values) > 7 and values[7] else -60.0,
                        'cpu_usage': float(values[8]) if len(values) > 8 and values[8] else 0.3,
                        'memory_usage': float(values[9]) if len(values) > 9 and values[9] else 0.4,
                        'buffer_occupancy': float(values[10]) if len(values) > 10 and values[10] else 0.2,
                        # Connectivity metrics (columns 11-13)
                        'active_links': int(values[11]) if len(values) > 11 and values[11] else 2,
                        'neighbor_count': int(values[12]) if len(values) > 12 and values[12] else 3,
                        'link_utilization': float(values[13]) if len(values) > 13 and values[13] else 0.5,
                        # Load metrics (columns 14-15)
                        'critical_load': float(values[14]) if len(values) > 14 and values[14] else 0.25,
                        'normal_load': float(values[15]) if len(values) > 15 and values[15] else 0.6,
                        # Energy metric (column 16)
                        'energy_level': float(values[16]) if len(values) > 16 and values[16] else 0.8,
                        # Position metrics (columns 17-19)
                        'x_position': float(values[17]) if len(values) > 17 and values[17] else 0.0,
                        'y_position': float(values[18]) if len(values) > 18 and values[18] else 0.0,
                        'z_position': float(values[19]) if len(values) > 19 and values[19] else 0.0,
                        # Health metrics (columns 21-24)
                        'degradation_level': float(values[23]) if len(values) > 23 and values[23] else 0.0,
                        'fault_severity': float(values[24]) if len(values) > 24 and values[24] else 0.0,
                        # Power metrics (columns 22-23)
                        'power_stability': float(values[22]) if len(values) > 22 and values[22] else 0.9,
                        'voltage_level': float(values[21]) if len(values) > 21 and values[21] else 0.95,
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
                    },
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
        """Start both static and real-time monitoring with enhanced validation"""
        logger.info("🚀 Starting ROBUST Enhanced Monitor Agent...")
        logger.info("📊 Static Monitoring: Intelligent change detection")
        logger.info("🔥 Real-time Monitoring: Handles ANY number of faults")
        logger.info("🛡️ Enhanced Validation: Ignores empty/invalid faults")
        logger.info("📤 Target: ONLY Calculation Agent")
        logger.info("🎯 ROBUST: No duplicate files, only REAL valid faults")
        
        # Initial scan
        file_status = await self.scan_essential_files()
        
        # Set running state
        self.is_running = True
        
        # Start all monitoring tasks
        tasks = [
            asyncio.create_task(self.static_file_monitoring_robust()),
            asyncio.create_task(self.monitor_realtime_faults()),
            asyncio.create_task(self.periodic_reporting()),
            asyncio.create_task(self.log_fault_detection_debug())  # Add debug logging
        ]
        
        logger.info("✅ ROBUST Enhanced Monitor Agent started successfully")
        logger.info("⏰ Monitoring intervals: Static 30s, Real-time 10s, Reports 5min, Debug 30s")
        logger.info("🎯 Ready to handle ANY number of VALID NS-3 faults dynamically")
        
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
            logger.info(f"   {key}: {value}")
        
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
        print('  - Debug logging: Every 30 seconds')
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