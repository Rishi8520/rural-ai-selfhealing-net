# enhanced_monitor_agent.py (COMPLETE ENHANCED VERSION WITH LSTM TRAINING DATA FIX)

import asyncio
import logging
import json
import time
import threading
import pandas as pd
import numpy as np  # ADDED: For statistics calculations in LSTM features
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
import fcntl
import json
from datetime import datetime

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class EnhancedNetworkMetrics:
    """Enhanced network metrics with degradation tracking"""
    node_id: str
    timestamp: datetime
    simulation_time: float
    throughput: float
    latency: float
    packet_loss: float
    voltage_level: float
    operational: bool
    node_type: str
    degradation_level: float  # New: gradual degradation (0.0-1.0)
    fault_severity: float     # New: fault severity (0.0-1.0)
    power_stability: float
    cpu_usage: float
    memory_usage: float
    energy_level: float

@dataclass 
class EnhancedFaultAlert:
    """Enhanced fault alert with degradation information"""
    alert_id: str
    node_id: str
    fault_type: str
    severity: str
    detection_time: datetime
    simulation_time: float
    degradation_level: float
    fault_severity: float
    metrics: Dict[str, Any]
    description: str
    prediction_confidence: float

@dataclass
class DataStreamMessage:
    """Message for streaming to Calculation Agent"""
    timestamp: datetime
    simulation_time: float
    data_type: str  # UPDATED: "comprehensive_metrics" instead of just "enhanced_metrics"
    content: Dict[str, Any]
    source_agent: str = "enhanced_monitor_agent"

class EnhancedNS3Interface:
    """Enhanced NS-3 interface with parallel access support"""
    
    def __init__(self, config: Dict[str, Any]):
        self.metrics_file = config.get('metrics_file', 'rural_network_metrics.csv')
        self.topology_file = config.get('topology_file', 'network_topology.json')
        
        # Parallel access handling
        self.current_time_index = 0
        self.simulation_data = None
        self.topology_info = {}
        self.available_times = []
        self.file_lock = threading.Lock()
        
        logger.info("Enhanced NS-3 Interface initialized")

    async def initialize_simulation(self):
        """Load and prepare enhanced NS-3 simulation data"""
        logger.info("Loading enhanced NS-3 simulation data...")
        
        try:
            if not os.path.exists(self.metrics_file):
                raise FileNotFoundError(f"Enhanced metrics file not found: {self.metrics_file}")
            
            with self.file_lock:
                self.simulation_data = pd.read_csv(self.metrics_file)
                self.available_times = sorted(self.simulation_data['Time'].unique())
            
            logger.info(f"Loaded {len(self.simulation_data)} enhanced data points")
            logger.info(f"Simulation time range: {self.available_times[0]:.0f}s to {self.available_times[-1]:.0f}s")
            logger.info(f"Data collection interval: {self.available_times[1] - self.available_times[0]:.0f}s")
            logger.info(f"Total nodes: {self.simulation_data['NodeId'].nunique()}")
            
            # Load topology
            if os.path.exists(self.topology_file):
                with open(self.topology_file, 'r') as f:
                    self.topology_info = json.load(f)
                logger.info("Enhanced topology information loaded")
            
            logger.info("Enhanced NS-3 simulation data ready for monitoring")
            
        except Exception as e:
            logger.error(f"Failed to load enhanced NS-3 data: {e}")
            raise

    async def get_all_node_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get current enhanced network metrics with parallel access protection"""
        if self.simulation_data is None:
            logger.warning("No enhanced simulation data loaded")
            return {}
        
        with self.file_lock:
            # Get current time slice
            if self.current_time_index >= len(self.available_times):
                logger.info("End of enhanced simulation data reached")
                return {}
            
            current_time = self.available_times[self.current_time_index]
            current_data = self.simulation_data[self.simulation_data['Time'] == current_time]
        
        logger.debug(f"Reading enhanced metrics at time {current_time:.0f}s ({self.current_time_index + 1}/{len(self.available_times)})")
        
        # Convert to enhanced metrics format
        metrics = {}
        for _, row in current_data.iterrows():
            node_id = f"node_{int(row['NodeId']):02d}"
            
            metrics[node_id] = {
                'throughput': float(row['Throughput_Mbps']),
                'latency': float(row['Latency_ms']),
                'packet_loss': float(row['PacketLoss_Rate']),
                'jitter': float(row['Jitter_ms']),
                'signal_strength': float(row['SignalStrength_dBm']),
                'cpu_usage': float(row['CPU_Usage']),
                'memory_usage': float(row['Memory_Usage']),
                'buffer_occupancy': float(row['Buffer_Occupancy']),
                'active_links': int(row['Active_Links']),
                'neighbor_count': int(row['Neighbor_Count']),
                'link_utilization': float(row['Link_Utilization']),
                'critical_load': float(row['Critical_Load']),
                'normal_load': float(row['Normal_Load']),
                'energy_level': float(row['Energy_Level']),
                'operational': bool(row['Operational_Status']),
                'voltage_level': float(row['Voltage_Level']),
                'power_stability': float(row['Power_Stability']),
                'degradation_level': float(row['Degradation_Level']),  # Enhanced field
                'fault_severity': float(row['Fault_Severity']),        # Enhanced field
                'node_type': str(row['NodeType']),
                'position_x': float(row['X_Position']),
                'position_y': float(row['Y_Position']),
                'current_time': current_time
            }
        
        # Move to next time slice for next call
        self.current_time_index += 1
        
        return metrics

    def get_simulation_progress(self) -> Dict[str, Any]:
        """Get enhanced simulation progress information"""
        if not self.available_times:
            return {'progress': 0, 'current_time': 0, 'total_time': 0}
        
        current_time = self.available_times[min(self.current_time_index, len(self.available_times) - 1)]
        total_time = self.available_times[-1]
        progress = (self.current_time_index / len(self.available_times)) * 100
        
        return {
            'progress': min(progress, 100),
            'current_time': current_time,
            'total_time': total_time,
            'time_step': self.current_time_index,
            'total_steps': len(self.available_times)
        }

    async def cleanup(self):
        """Cleanup enhanced interface"""
        logger.info("Enhanced NS-3 interface cleanup completed")

class EnhancedMonitorAgent:
    """Enhanced Monitor Agent with Gradual Fault Detection and Data Streaming"""
    
    def __init__(self, config_file: str = "enhanced_monitor_config.json"):
        self.config = self.load_configuration(config_file)
        
        # Initialize enhanced NS-3 interface
        self.ns3_interface = EnhancedNS3Interface(self.config.get('ns3', {}))
        
        # Data streaming components
        self.data_stream_queue = asyncio.Queue(maxsize=1000)
        self.alert_stream_queue = asyncio.Queue(maxsize=100)
        
        # Monitoring state
        self.is_running = False
        self.streaming_active = False
        self.detected_faults = []
        self.detected_degradations = []
        self.baseline_metrics = {}
        self.fault_history = {}
        
        # Enhanced thresholds
        self.thresholds = self.config['thresholds']
        self.degradation_thresholds = self.config['degradation_thresholds']
        
        logger.info("Enhanced Monitor Agent initialized with gradual fault detection")

    def load_configuration(self, config_file: str) -> Dict[str, Any]:
        """Load enhanced configuration"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            logger.info(f"Enhanced configuration loaded from {config_file}")
            return config
        except FileNotFoundError:
            logger.warning(f"Config file {config_file} not found, using enhanced defaults")
            return self.get_enhanced_default_config()

    def get_enhanced_default_config(self) -> Dict[str, Any]:
        """Enhanced default configuration"""
        return {
            "ns3": {
                "metrics_file": "rural_network_metrics.csv",
                "topology_file": "network_topology.json"
            },
            "calculation_agent": {
                "endpoint": "calculation_agent_data_stream.json",
                "data_push_interval": 15.0,
                "batch_size": 5
            },
            "mcp_agent": {
                "endpoint": "mcp_agent_alerts.json",
                "alert_push_interval": 5.0
            },
            "thresholds": {
                "throughput_min": 15.0,
                "latency_max": 150.0,
                "packet_loss_max": 0.05,
                "voltage_min": 200.0,
                "voltage_max": 240.0,
                "power_stability_min": 0.85
            },
            "degradation_thresholds": {
                "degradation_warning": 0.2,      # 20% degradation triggers warning
                "degradation_critical": 0.5,     # 50% degradation triggers critical
                "fault_severity_high": 0.7,      # 70% severity triggers immediate action
                "prediction_confidence": 0.8     # 80% confidence for predictions
            },
            "monitoring": {
                "check_interval": 3.0,           # More frequent checks for gradual detection
                "baseline_samples": 8,
                "stream_batch_size": 5
            }
        }

    async def start_enhanced_monitoring(self):
        """Start enhanced monitoring with gradual fault detection"""
        logger.info("=" * 80)
        logger.info("STARTING MONITOR AGENT")
        logger.info("WITH GRADUAL FAULT DETECTION AND DATA STREAMING")
        logger.info("=" * 80)
        
        self.is_running = True
        self.streaming_active = True
        
        try:
            # Initialize enhanced NS-3 interface
            await self.ns3_interface.initialize_simulation()
            
            # Establish enhanced baseline
            await self.establish_enhanced_baseline()
            
            # Start data streaming tasks
            data_streaming_task = asyncio.create_task(self.data_streaming_loop())
            alert_streaming_task = asyncio.create_task(self.alert_streaming_loop())
            
            # Start main enhanced monitoring loop
            monitoring_task = asyncio.create_task(self.enhanced_monitoring_loop())
            
            # Wait for monitoring to complete
            await monitoring_task
            
            # Cancel streaming tasks
            data_streaming_task.cancel()
            alert_streaming_task.cancel()
            
        except Exception as e:
            logger.error(f"Error in enhanced monitoring: {e}")
            raise
        finally:
            await self.stop_enhanced_monitoring()

    async def establish_enhanced_baseline(self):
        """Establish enhanced baseline metrics"""
        logger.info("Establishing enhanced baseline metrics...")
        
        baseline_samples = self.config['monitoring']['baseline_samples']
        
        for sample in range(baseline_samples):
            # Get current enhanced metrics
            raw_metrics = await self.ns3_interface.get_all_node_metrics()
            
            if not raw_metrics:
                logger.warning("No enhanced metrics available for baseline")
                break
            
            # Process enhanced metrics
            current_metrics = self.convert_to_enhanced_metrics(raw_metrics)
            
            # Store enhanced baseline data
            for node_id, metrics in current_metrics.items():
                if node_id not in self.baseline_metrics:
                    self.baseline_metrics[node_id] = {
                        'throughput_samples': [],
                        'latency_samples': [],
                        'voltage_samples': [],
                        'degradation_samples': [],
                        'energy_samples': []
                    }
                
                self.baseline_metrics[node_id]['throughput_samples'].append(metrics.throughput)
                self.baseline_metrics[node_id]['latency_samples'].append(metrics.latency)
                self.baseline_metrics[node_id]['voltage_samples'].append(metrics.voltage_level)
                self.baseline_metrics[node_id]['degradation_samples'].append(metrics.degradation_level)
                self.baseline_metrics[node_id]['energy_samples'].append(metrics.energy_level)
            
            logger.info(f"Enhanced baseline sample {sample + 1}/{baseline_samples} collected")
            await asyncio.sleep(1)
        
        # Calculate enhanced baseline statistics
        for node_id, samples in self.baseline_metrics.items():
            if samples['throughput_samples']:
                samples['throughput_avg'] = sum(samples['throughput_samples']) / len(samples['throughput_samples'])
                samples['voltage_avg'] = sum(samples['voltage_samples']) / len(samples['voltage_samples'])
                samples['latency_avg'] = sum(samples['latency_samples']) / len(samples['latency_samples'])
                samples['degradation_avg'] = sum(samples['degradation_samples']) / len(samples['degradation_samples'])
                samples['energy_avg'] = sum(samples['energy_samples']) / len(samples['energy_samples'])
        
        logger.info(f"Enhanced baseline established for {len(self.baseline_metrics)} nodes")

    async def enhanced_monitoring_loop(self):
        """Enhanced monitoring loop with gradual fault detection"""
        logger.info("Starting enhanced monitoring loop with gradual fault detection...")
        
        while self.is_running:
            try:
                # Get current enhanced metrics
                raw_metrics = await self.ns3_interface.get_all_node_metrics()
                
                if not raw_metrics:
                    logger.info("End of enhanced simulation data reached")
                    break
                
                # Convert to enhanced format
                current_metrics = self.convert_to_enhanced_metrics(raw_metrics)
                
                # Enhanced degradation detection
                degradation_alerts = self.detect_gradual_degradation(current_metrics)
                
                # Enhanced fault detection
                fault_alerts = self.detect_enhanced_faults(current_metrics)
                
                # Predictive fault analysis
                prediction_alerts = self.predict_upcoming_faults(current_metrics)
                
                # *** CRITICAL CHANGE: Queue ALL data for LSTM training (not just faults) ***
                await self.queue_comprehensive_data_for_lstm(current_metrics)
                
                # Process all types of alerts
                all_alerts = degradation_alerts + fault_alerts + prediction_alerts
                if all_alerts:
                    await self.process_enhanced_alerts(all_alerts)
                
                # Check for fault recovery
                await self.check_enhanced_recovery(current_metrics)
                
                # Show enhanced progress
                progress = self.ns3_interface.get_simulation_progress()
                if progress['time_step'] % 5 == 0:  # Log every 5th iteration
                    # ADDED: Show data classification in progress
                    has_faults = any(m.fault_severity > 0.1 for m in current_metrics.values())
                    data_status = "FAULT DATA" if has_faults else "NORMAL DATA"
                    logger.info(f"Enhanced monitoring: {progress['progress']:.1f}% "
                               f"(Time: {progress['current_time']:.0f}s) - "
                               f"Sending: {data_status} to LSTM")
                
                await asyncio.sleep(self.config['monitoring']['check_interval'])
                
            except Exception as e:
                logger.error(f"Error in enhanced monitoring loop: {e}")
                await asyncio.sleep(self.config['monitoring']['check_interval'])

    def convert_to_enhanced_metrics(self, raw_metrics: Dict[str, Dict[str, float]]) -> Dict[str, EnhancedNetworkMetrics]:
        """Convert raw metrics to enhanced format"""
        metrics = {}
        current_time = datetime.now()
        
        for node_id, data in raw_metrics.items():
            metrics[node_id] = EnhancedNetworkMetrics(
                node_id=node_id,
                timestamp=current_time,
                simulation_time=data.get('current_time', 0.0),
                throughput=data.get('throughput', 0.0),
                latency=data.get('latency', 0.0),
                packet_loss=data.get('packet_loss', 0.0),
                voltage_level=data.get('voltage_level', 220.0),
                operational=data.get('operational', True),
                node_type=data.get('node_type', 'unknown'),
                degradation_level=data.get('degradation_level', 0.0),  # Enhanced field
                fault_severity=data.get('fault_severity', 0.0),       # Enhanced field
                power_stability=data.get('power_stability', 0.95),
                cpu_usage=data.get('cpu_usage', 0.0),
                memory_usage=data.get('memory_usage', 0.0),
                energy_level=data.get('energy_level', 100.0)
            )
        
        return metrics

    def detect_gradual_degradation(self, metrics: Dict[str, EnhancedNetworkMetrics]) -> List[EnhancedFaultAlert]:
        """Detect gradual degradation patterns"""
        degradation_alerts = []
        
        for node_id, node_metrics in metrics.items():
            # Check degradation level against thresholds
            if node_metrics.degradation_level > self.degradation_thresholds['degradation_warning']:
                # Determine severity based on degradation level
                if node_metrics.degradation_level > self.degradation_thresholds['degradation_critical']:
                    severity = "CRITICAL"
                    confidence = 0.9
                elif node_metrics.degradation_level > self.degradation_thresholds['degradation_warning']:
                    severity = "HIGH"
                    confidence = 0.8
                else:
                    severity = "WARNING"
                    confidence = 0.7
                
                # Check if this is a new degradation or escalation
                existing_degradation = next((d for d in self.detected_degradations 
                                           if d['node_id'] == node_id and d.get('active', False)), None)
                
                if not existing_degradation or existing_degradation['severity'] != severity:
                    alert = EnhancedFaultAlert(
                        alert_id=f"DEG_{int(time.time())}_{node_id}",
                        node_id=node_id,
                        fault_type='gradual_degradation',
                        severity=severity,
                        detection_time=datetime.now(),
                        simulation_time=node_metrics.simulation_time,
                        degradation_level=node_metrics.degradation_level,
                        fault_severity=node_metrics.fault_severity,
                        metrics=asdict(node_metrics),
                        description=f"Gradual degradation detected: {node_metrics.degradation_level*100:.1f}% degraded",
                        prediction_confidence=confidence
                    )
                    
                    degradation_alerts.append(alert)
                    
                    # Update degradation tracking
                    if existing_degradation:
                        existing_degradation['severity'] = severity
                        existing_degradation['last_update'] = node_metrics.simulation_time
                    else:
                        self.detected_degradations.append({
                            'node_id': node_id,
                            'severity': severity,
                            'start_time': node_metrics.simulation_time,
                            'last_update': node_metrics.simulation_time,
                            'active': True
                        })
        
        return degradation_alerts

    def detect_enhanced_faults(self, metrics: Dict[str, EnhancedNetworkMetrics]) -> List[EnhancedFaultAlert]:
        """Detect enhanced faults based on severity and operational status"""
        fault_alerts = []
        
        for node_id, node_metrics in metrics.items():
            # Skip if already in fault state
            if node_id in self.fault_history and self.fault_history[node_id]['active']:
                continue
            
            # Critical fault based on severity
            if node_metrics.fault_severity > self.degradation_thresholds['fault_severity_high']:
                fault_type = "critical_fault"
                if not node_metrics.operational:
                    fault_type = "node_failure"
                    
                alert = EnhancedFaultAlert(
                    alert_id=f"FAULT_{int(time.time())}_{node_id}",
                    node_id=node_id,
                    fault_type=fault_type,
                    severity='CRITICAL',
                    detection_time=datetime.now(),
                    simulation_time=node_metrics.simulation_time,
                    degradation_level=node_metrics.degradation_level,
                    fault_severity=node_metrics.fault_severity,
                    metrics=asdict(node_metrics),
                    description=f"Critical fault detected: {node_metrics.fault_severity*100:.1f}% severity",
                    prediction_confidence=0.95
                )
                
                fault_alerts.append(alert)
            
            # Power fluctuation detection
            elif (node_metrics.voltage_level < self.thresholds['voltage_min'] or 
                  node_metrics.voltage_level > self.thresholds['voltage_max']):
                
                alert = EnhancedFaultAlert(
                    alert_id=f"POWER_{int(time.time())}_{node_id}",
                    node_id=node_id,
                    fault_type='power_fluctuation',
                    severity='HIGH',
                    detection_time=datetime.now(),
                    simulation_time=node_metrics.simulation_time,
                    degradation_level=node_metrics.degradation_level,
                    fault_severity=node_metrics.fault_severity,
                    metrics=asdict(node_metrics),
                    description=f"Power fluctuation: {node_metrics.voltage_level:.1f}V (normal: {self.thresholds['voltage_min']}-{self.thresholds['voltage_max']}V)",
                    prediction_confidence=0.85
                )
                
                fault_alerts.append(alert)
        
        return fault_alerts

    def predict_upcoming_faults(self, metrics: Dict[str, EnhancedNetworkMetrics]) -> List[EnhancedFaultAlert]:
        """Predict upcoming faults based on degradation trends"""
        prediction_alerts = []
        
        for node_id, node_metrics in metrics.items():
            # Predict based on high degradation but not yet critical
            if (0.3 < node_metrics.degradation_level < 0.7 and 
                node_metrics.fault_severity < 0.5):
                
                # Simple trend prediction (in real system, LSTM would do this)
                time_to_fault = (0.8 - node_metrics.degradation_level) / 0.1 * 10  # Rough estimate
                
                if time_to_fault < 60:  # Predict fault within 60 seconds
                    alert = EnhancedFaultAlert(
                        alert_id=f"PRED_{int(time.time())}_{node_id}",
                        node_id=node_id,
                        fault_type='predicted_fault',
                        severity='WARNING',
                        detection_time=datetime.now(),
                        simulation_time=node_metrics.simulation_time,
                        degradation_level=node_metrics.degradation_level,
                        fault_severity=node_metrics.fault_severity,
                        metrics=asdict(node_metrics),
                        description=f"Fault predicted in ~{time_to_fault:.0f}s based on degradation trend",
                        prediction_confidence=min(0.9, node_metrics.degradation_level + 0.2)
                    )
                    
                    prediction_alerts.append(alert)
        
        return prediction_alerts

    # *** CRITICAL CHANGE: NEW METHOD TO SEND ALL DATA TO LSTM ***
    async def queue_comprehensive_data_for_lstm(self, metrics: Dict[str, EnhancedNetworkMetrics]):
        """Queue ALL data (normal + fault) for LSTM training - CRITICAL FOR LSTM LEARNING"""
        try:
            # STEP 1: Classify current network state
            has_faults = any(m.fault_severity > 0.1 for m in metrics.values())
            has_degradation = any(m.degradation_level > 0.1 for m in metrics.values())
            
            # STEP 2: Determine data classification for LSTM
            if has_faults or has_degradation:
                data_classification = "anomalous"
                anomaly_level = max([m.fault_severity for m in metrics.values()])
            else:
                data_classification = "normal"  # CRITICAL: LSTM needs this normal data!
                anomaly_level = 0.0
            
            # STEP 3: Calculate network health metrics for LSTM features
            operational_nodes = len([m for m in metrics.values() if m.operational])
            total_nodes = len(metrics)
            network_health_score = (operational_nodes / total_nodes) * 100
            
            # STEP 4: Extract time-series features for LSTM
            lstm_features = self._extract_lstm_time_series_features(metrics)
            
            # STEP 5: Create comprehensive data stream message
            stream_message = DataStreamMessage(
                timestamp=datetime.now(),
                simulation_time=next(iter(metrics.values())).simulation_time,
                data_type="comprehensive_metrics",  # Changed from "enhanced_metrics"
                content={
                    'simulation_time': next(iter(metrics.values())).simulation_time,
                    
                    # *** CRITICAL: Data classification for LSTM training ***
                    'data_classification': data_classification,  # "normal" or "anomalous"
                    'anomaly_level': anomaly_level,              # 0.0-1.0 quantified anomaly
                    'fault_progression_stage': self._classify_fault_stage(metrics),
                    
                    # *** CRITICAL: Network health summary for LSTM ***
                    'network_health_summary': {
                        'total_nodes': total_nodes,
                        'operational_nodes': operational_nodes,
                        'degraded_nodes': len([m for m in metrics.values() if m.degradation_level > 0.1]),
                        'failed_nodes': len([m for m in metrics.values() if m.fault_severity > 0.8]),
                        'network_health_score': network_health_score,
                        'avg_throughput': sum([m.throughput for m in metrics.values()]) / len(metrics),
                        'avg_latency': sum([m.latency for m in metrics.values()]) / len(metrics),
                        'avg_voltage': sum([m.voltage_level for m in metrics.values()]) / len(metrics),
                        'max_degradation': max([m.degradation_level for m in metrics.values()]),
                        'max_fault_severity': max([m.fault_severity for m in metrics.values()])
                    },
                    
                    # *** CRITICAL: LSTM-specific training features ***
                    'lstm_training_features': {
                        'is_normal_period': not (has_faults or has_degradation),
                        'time_series_features': lstm_features,
                        'trend_indicators': {
                            'degradation_trend': 'increasing' if anomaly_level > 0.3 else 'stable',
                            'network_stability': 'unstable' if network_health_score < 90 else 'stable',
                            'fault_risk_level': 'high' if anomaly_level > 0.6 else 'low'
                        }
                    },
                    
                    # Original detailed metrics for analysis
                    'node_count': len(metrics),
                    'metrics': {node_id: asdict(node_metrics) for node_id, node_metrics in metrics.items()}
                }
            )
            
            # STEP 6: Always queue data (not just during faults) - CRITICAL FOR LSTM
            if not self.data_stream_queue.full():
                await self.data_stream_queue.put(stream_message)
            else:
                logger.warning("Comprehensive data stream queue full, dropping oldest data")
                try:
                    self.data_stream_queue.get_nowait()  # Remove oldest
                    await self.data_stream_queue.put(stream_message)  # Add new
                except:
                    pass
            
            # STEP 7: Log what type of data we're sending to LSTM
            if data_classification == "normal":
                logger.debug(f"📊 Sending NORMAL baseline data to LSTM (Time: {next(iter(metrics.values())).simulation_time:.0f}s, Health: {network_health_score:.1f}%)")
            else:
                logger.debug(f"🚨 Sending ANOMALOUS data to LSTM (Time: {next(iter(metrics.values())).simulation_time:.0f}s, Anomaly: {anomaly_level:.2f})")
                    
        except Exception as e:
            logger.error(f"Error queuing comprehensive LSTM data: {e}")

    # *** ADDED: Helper methods for LSTM feature extraction ***
    def _classify_fault_stage(self, metrics: Dict[str, EnhancedNetworkMetrics]) -> str:
        """Classify the current fault progression stage for LSTM"""
        max_degradation = max([m.degradation_level for m in metrics.values()])
        max_severity = max([m.fault_severity for m in metrics.values()])
        
        if max_severity > 0.8:
            return "critical_fault"
        elif max_degradation > 0.5:
            return "severe_degradation"
        elif max_degradation > 0.2:
            return "moderate_degradation"
        elif max_degradation > 0.05:
            return "early_degradation"
        else:
            return "normal_operation"  # CRITICAL: LSTM needs this classification

    def _extract_lstm_time_series_features(self, metrics: Dict[str, EnhancedNetworkMetrics]) -> Dict[str, Any]:
        """Extract time-series features specifically for LSTM training"""
        # Aggregate network-wide features for LSTM
        throughput_values = [m.throughput for m in metrics.values()]
        latency_values = [m.latency for m in metrics.values()]
        voltage_values = [m.voltage_level for m in metrics.values()]
        degradation_values = [m.degradation_level for m in metrics.values()]
        
        return {
            'network_throughput_stats': {
                'mean': np.mean(throughput_values),
                'std': np.std(throughput_values),
                'min': np.min(throughput_values),
                'max': np.max(throughput_values)
            },
            'network_latency_stats': {
                'mean': np.mean(latency_values),
                'std': np.std(latency_values),
                'min': np.min(latency_values),
                'max': np.max(latency_values)
            },
            'network_voltage_stats': {
                'mean': np.mean(voltage_values),
                'std': np.std(voltage_values),
                'min': np.min(voltage_values),
                'max': np.max(voltage_values)
            },
            'network_degradation_stats': {
                'mean': np.mean(degradation_values),
                'max': np.max(degradation_values),
                'affected_nodes': len([d for d in degradation_values if d > 0.1]),
                'degradation_variance': np.var(degradation_values)
            }
        }

    # *** KEPT: Original enhanced data queuing method (now unused) ***
    async def queue_enhanced_data(self, metrics: Dict[str, EnhancedNetworkMetrics]):
        """DEPRECATED: Original method - replaced by queue_comprehensive_data_for_lstm"""
        # This method is now replaced by queue_comprehensive_data_for_lstm
        # Keeping for reference but not used anymore
        pass

    async def data_streaming_loop(self):
        """Stream comprehensive data to Calculation Agent for LSTM processing"""
        logger.info("Starting comprehensive data streaming to Calculation Agent for LSTM...")
        
        while self.streaming_active:
            try:
                # Collect batch of comprehensive data
                batch = []
                batch_size = self.config['monitoring']['stream_batch_size']
                
                for _ in range(batch_size):
                    if not self.data_stream_queue.empty():
                        message = await asyncio.wait_for(self.data_stream_queue.get(), timeout=1.0)
                        batch.append(message)
                
                if batch:
                    await self.send_comprehensive_data_to_calculation_agent(batch)
                
                # Wait before next batch
                await asyncio.sleep(self.config['calculation_agent']['data_push_interval'])
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in comprehensive data streaming loop: {e}")
                await asyncio.sleep(5.0)

    async def send_comprehensive_data_to_calculation_agent(self, batch: List[DataStreamMessage]):
        """Send comprehensive data batch to Calculation Agent for LSTM processing"""
        try:
            # Count normal vs anomalous data in batch
            normal_count = len([msg for msg in batch if msg.content.get('data_classification') == 'normal'])
            anomalous_count = len([msg for msg in batch if msg.content.get('data_classification') == 'anomalous'])
            
            batch_data = {
                'batch_id': f"comprehensive_batch_{int(time.time())}",
                'timestamp': datetime.now().isoformat(),
                'source': 'enhanced_monitor_agent',
                'message_count': len(batch),
                'batch_type': 'comprehensive_lstm_training_data',  # Updated type
                
                # *** CRITICAL: Batch statistics for LSTM ***
                'batch_statistics': {
                    'normal_data_points': normal_count,
                    'anomalous_data_points': anomalous_count,
                    'data_balance_ratio': normal_count / (normal_count + anomalous_count) if (normal_count + anomalous_count) > 0 else 0,
                    'lstm_training_ready': True
                },
                
                'messages': [
                    {
                        'timestamp': msg.timestamp.isoformat(),
                        'simulation_time': msg.simulation_time,
                        'data_type': msg.data_type,
                        'content': msg.content
                    }
                    for msg in batch
                ]
            }
            
            # Save for Calculation Agent (LSTM processing)
            with open(self.config['calculation_agent']['endpoint'], 'a') as f:
                f.write(json.dumps(batch_data, cls=DateTimeEncoder) + '\n')
            
            # Enhanced logging for LSTM data tracking
            logger.debug(f"📊 Sent comprehensive batch to LSTM: {len(batch)} messages "
                        f"(Normal: {normal_count}, Anomalous: {anomalous_count})")
            
        except Exception as e:
            logger.error(f"Error sending comprehensive data to Calculation Agent: {e}")

    async def alert_streaming_loop(self):
        """Stream alerts to MCP Agent"""
        logger.info("Starting alert streaming to MCP Agent...")
        
        while self.streaming_active:
            try:
                if not self.alert_stream_queue.empty():
                    alert = await self.alert_stream_queue.get()
                    await self.send_alert_to_mcp_agent(alert)
                
                await asyncio.sleep(self.config['mcp_agent']['alert_push_interval'])
                
            except Exception as e:
                logger.error(f"Error in alert streaming loop: {e}")
                await asyncio.sleep(5.0)

    async def send_alert_to_mcp_agent(self, alert: EnhancedFaultAlert):
        """Send alert to MCP Agent"""
        try:
            alert_data = {
                'alert_id': alert.alert_id,
                'timestamp': datetime.now().isoformat(),
                'source': 'enhanced_monitor_agent',
                'target': 'mcp_agent',
                'alert_data': asdict(alert)
            }
            
            # Save for MCP Agent
            with open(self.config['mcp_agent']['endpoint'], 'a') as f:
                f.write(json.dumps(alert_data, cls=DateTimeEncoder) + '\n')
            
            logger.debug(f"Sent alert to MCP Agent: {alert.alert_id}")
            
        except Exception as e:
            logger.error(f"Error sending alert to MCP Agent: {e}")

    async def process_enhanced_alerts(self, alerts: List[EnhancedFaultAlert]):
        """Process enhanced alerts with detailed logging"""
        for alert in alerts:
            logger.warning("=" * 80)
            logger.warning(f"🚨 ENHANCED {alert.fault_type.upper()}: {alert.severity}")
            logger.warning(f"Node: {alert.node_id}")
            logger.warning(f"Simulation Time: {alert.simulation_time:.0f}s")
            logger.warning(f"Degradation Level: {alert.degradation_level*100:.1f}%")
            logger.warning(f"Fault Severity: {alert.fault_severity*100:.1f}%")
            logger.warning(f"Prediction Confidence: {alert.prediction_confidence*100:.1f}%")
            logger.warning(f"Description: {alert.description}")
            logger.warning("=" * 80)
            
            # Update fault history
            if alert.fault_type in ['critical_fault', 'node_failure']:
                self.fault_history[alert.node_id] = {
                    'fault': alert,
                    'active': True,
                    'detection_time': alert.simulation_time
                }
            
            # Store for analysis
            self.detected_faults.append(alert)
            
            # Queue alert for MCP Agent
            if not self.alert_stream_queue.full():
                await self.alert_stream_queue.put(alert)
            
            # Log enhanced integration message
            if alert.fault_type == 'predicted_fault':
                logger.info(f"🔮 PREDICTIVE ALERT sent to Calculation Agent for early intervention")
            else:
                logger.info(f"🔧 ALERT sent to Calculation Agent for LSTM analysis and Healing Agent coordination")

    async def check_enhanced_recovery(self, metrics: Dict[str, EnhancedNetworkMetrics]):
        """Check for enhanced fault recovery"""
        recovered_nodes = []
        
        for node_id, fault_info in self.fault_history.items():
            if not fault_info['active']:
                continue
            
            # Check if node has recovered
            if node_id in metrics:
                node_metrics = metrics[node_id]
                
                # Enhanced recovery conditions
                is_operational = node_metrics.operational
                voltage_ok = (self.thresholds['voltage_min'] <= node_metrics.voltage_level <= self.thresholds['voltage_max'])
                low_severity = node_metrics.fault_severity < 0.3
                low_degradation = node_metrics.degradation_level < 0.2
                
                if is_operational and voltage_ok and low_severity and low_degradation:
                    logger.info("=" * 80)
                    logger.info(f"✅ ENHANCED FAULT RECOVERY DETECTED")
                    logger.info(f"Node: {node_id}")
                    logger.info(f"Original Fault: {fault_info['fault'].fault_type}")
                    logger.info(f"Recovery Time: {node_metrics.simulation_time:.0f}s")
                    logger.info(f"Fault Duration: {node_metrics.simulation_time - fault_info['detection_time']:.0f}s")
                    logger.info(f"Final Degradation: {node_metrics.degradation_level*100:.1f}%")
                    logger.info(f"Final Severity: {node_metrics.fault_severity*100:.1f}%")
                    logger.info("=" * 80)
                    
                    fault_info['active'] = False
                    fault_info['recovery_time'] = node_metrics.simulation_time
                    recovered_nodes.append(node_id)
                    
                    # Update degradation tracking
                    for degradation in self.detected_degradations:
                        if degradation['node_id'] == node_id:
                            degradation['active'] = False

    async def stop_enhanced_monitoring(self):
        """Stop enhanced monitoring and generate comprehensive summary"""
        logger.info("Stopping Monitor Agent...")
        self.is_running = False
        self.streaming_active = False
        
        # Generate enhanced summary
        await self.generate_enhanced_summary()
        
        # Cleanup
        await self.ns3_interface.cleanup()
        
        logger.info("Monitor Agent stopped successfully")

    async def generate_enhanced_summary(self):
        """Generate comprehensive enhanced monitoring summary"""
        logger.info("=" * 80)
        logger.info("ENHANCED MONITORING SUMMARY")
        logger.info("=" * 80)
        
        total_alerts = len(self.detected_faults)
        
        if total_alerts == 0:
            logger.info("✅ No faults detected during enhanced monitoring")
            # *** ADDED: Show that normal data was still sent to LSTM ***
            logger.info("📊 Normal baseline data was continuously sent to LSTM for training")
            return
        
        # Categorize enhanced alerts
        degradation_alerts = [a for a in self.detected_faults if a.fault_type == 'gradual_degradation']
        critical_alerts = [a for a in self.detected_faults if a.fault_type in ['critical_fault', 'node_failure']]
        prediction_alerts = [a for a in self.detected_faults if a.fault_type == 'predicted_fault']
        power_alerts = [a for a in self.detected_faults if a.fault_type == 'power_fluctuation']
        
        logger.info(f"Enhanced Detection Results:")
        logger.info(f"  Total alerts: {total_alerts}")
        logger.info(f"  Gradual degradation alerts: {len(degradation_alerts)}")
        logger.info(f"  Critical fault alerts: {len(critical_alerts)}")
        logger.info(f"  Predictive alerts: {len(prediction_alerts)}")
        logger.info(f"  Power fluctuation alerts: {len(power_alerts)}")
        
        # *** ADDED: LSTM data summary ***
        logger.info(f"\nLSTM Training Data Summary:")
        logger.info(f"  ✅ Normal baseline data: Sent continuously during healthy periods")
        logger.info(f"  ✅ Fault progression data: Sent during degradation and fault periods")
        logger.info(f"  ✅ Recovery data: Sent during fault recovery periods")
        logger.info(f"  📊 LSTM now has complete training dataset (normal + anomalous)")
        
        # Recovery statistics
        active_faults = sum(1 for info in self.fault_history.values() if info['active'])
        recovered_faults = len(self.fault_history) - active_faults
        
        logger.info(f"\nEnhanced Recovery Statistics:")
        logger.info(f"  Active faults: {active_faults}")
        logger.info(f"  Recovered faults: {recovered_faults}")
        logger.info(f"  Recovery rate: {(recovered_faults / len(self.fault_history) * 100):.1f}%" if self.fault_history else "N/A")
        
        # Save enhanced report
        report = {
            'enhanced_monitoring_session': {
                'timestamp': datetime.now().isoformat(),
                'total_alerts': total_alerts,
                'degradation_alerts': len(degradation_alerts),
                'critical_alerts': len(critical_alerts),
                'prediction_alerts': len(prediction_alerts),
                'power_alerts': len(power_alerts),
                'lstm_data_completeness': 'normal_and_anomalous_data_sent'  # Added
            },
            'enhanced_alerts': [asdict(alert) for alert in self.detected_faults],
            'degradation_tracking': self.detected_degradations,
            'fault_history': {
                node_id: {
                    'fault_type': info['fault'].fault_type,
                    'detection_time': info['detection_time'],
                    'active': info['active'],
                    'recovery_time': info.get('recovery_time', None)
                }
                for node_id, info in self.fault_history.items()
            }
        }
        
        with open('enhanced_monitoring_report.json', 'w') as f:
            json.dump(report, f, indent=2,cls=DateTimeEncoder)
        
        logger.info("Enhanced monitoring report saved to 'enhanced_monitoring_report.json'")

# Configuration file creation
def create_enhanced_config():
    """Create enhanced configuration file"""
    config = {
        "ns3": {
            "metrics_file": "rural_network_metrics.csv",
            "topology_file": "network_topology.json"
        },
        "calculation_agent": {
            "endpoint": "calculation_agent_data_stream.json",
            "data_push_interval": 15.0,
            "batch_size": 5
        },
        "mcp_agent": {
            "endpoint": "mcp_agent_alerts.json",
            "alert_push_interval": 5.0
        },
        "thresholds": {
            "throughput_min": 15.0,
            "latency_max": 150.0,
            "packet_loss_max": 0.05,
            "voltage_min": 200.0,
            "voltage_max": 240.0,
            "power_stability_min": 0.85
        },
        "degradation_thresholds": {
            "degradation_warning": 0.2,
            "degradation_critical": 0.5,
            "fault_severity_high": 0.7,
            "prediction_confidence": 0.8
        },
        "monitoring": {
            "check_interval": 3.0,
            "baseline_samples": 8,
            "stream_batch_size": 5
        }
    }
    
    with open('enhanced_monitor_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("Enhanced configuration file created: enhanced_monitor_config.json")

# Main execution
async def main():
    """Main function to run the enhanced monitor agent"""
    # Create config if it doesn't exist
    if not os.path.exists('enhanced_monitor_config.json'):
        create_enhanced_config()
    
    monitor = EnhancedMonitorAgent()
    
    try:
        await monitor.start_enhanced_monitoring()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        await monitor.stop_enhanced_monitoring()

if __name__ == "__main__":
    asyncio.run(main())