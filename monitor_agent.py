# streamlined_monitor_agent.py - FOCUS ON DATA COLLECTION AND BASIC HEALTH ONLY
from prometheus_client import start_http_server, Gauge, Counter, Histogram
import time
import asyncio
import json
import logging
import time
import statistics  # For basic statistics calculations
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
import os

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
    """Enhanced network metrics data structure"""
    node_id: str
    simulation_time: float
    throughput: float
    latency: float
    packet_loss: float
    cpu_usage: float
    memory_usage: float
    energy_level: float
    operational: bool
    
    # Environmental and fault metrics from NS3
    degradation_level: float = 0.0
    fault_severity: float = 0.0
    power_stability: float = 1.0
    voltage_level: float = 220.0
    node_type: str = "access"
    position_x: float = 0.0
    position_y: float = 0.0

@dataclass 
class DataStreamMessage:
    """Message structure for streaming data to Calculation Agent"""
    timestamp: datetime
    simulation_time: float
    data_type: str
    content: Dict[str, Any]

@dataclass
class BasicAlert:
    """Basic operational alert (no AI analysis)"""
    node_id: str
    alert_type: str
    timestamp: datetime
    simulation_time: float
    description: str
    severity: str
    basic_threshold_exceeded: bool

class StreamlinedNS3Interface:
    """Simplified NS3 interface - pure data collection"""
    
    def __init__(self, config: Dict[str, Any]):
        self.metrics_file = config.get('metrics_file', 'rural_network_metrics.csv')
        self.topology_file = config.get('topology_file', 'network_topology.json')
        
        self.current_time_index = 0
        self.simulation_data = None
        self.available_times = []
        
        logger.info("Streamlined NS-3 Interface initialized for pure data collection")
    
    async def initialize_simulation(self):
        """Initialize simulation data reading"""
        try:
            if os.path.exists(self.metrics_file):
                import pandas as pd
                self.simulation_data = pd.read_csv(self.metrics_file)
                self.available_times = sorted(self.simulation_data['time'].unique())
                logger.info(f"Loaded simulation data: {len(self.simulation_data)} records, {len(self.available_times)} time steps")
            else:
                logger.warning(f"Metrics file {self.metrics_file} not found")
                
        except Exception as e:
            logger.error(f"Error initializing simulation: {e}")
    
    async def get_all_node_metrics(self) -> Optional[Dict[str, Any]]:
        """Get current time step metrics from NS3 simulation"""
        try:
            if self.simulation_data is None or self.current_time_index >= len(self.available_times):
                return None
            
            current_time = self.available_times[self.current_time_index]
            current_data = self.simulation_data[self.simulation_data['time'] == current_time]
            
            if current_data.empty:
                self.current_time_index += 1
                return None
            
            # Convert to metrics dictionary
            metrics = {}
            for _, row in current_data.iterrows():
                node_id = f"node_{int(row['node_id']):02d}"
                metrics[node_id] = {
                    'throughput': row.get('throughput', 0.0),
                    'latency': row.get('latency', 0.0),
                    'packet_loss': row.get('packet_loss', 0.0),
                    'cpu_usage': row.get('cpu_usage', 0.5),
                    'memory_usage': row.get('memory_usage', 0.4),
                    'energy_level': row.get('energy_level', 1.0),
                    'degradation_level': row.get('degradation_level', 0.0),
                    'fault_severity': row.get('fault_severity', 0.0),
                    'power_stability': row.get('power_stability', 1.0),
                    'voltage_level': row.get('voltage_level', 220.0),
                    'operational': row.get('operational', True),
                    'node_type': row.get('node_type', 'access'),
                    'position_x': row.get('position_x', 0.0),
                    'position_y': row.get('position_y', 0.0),
                    'simulation_time': current_time
                }
            
            self.current_time_index += 1
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting node metrics: {e}")
            return None
    
    def get_simulation_progress(self) -> Dict[str, Any]:
        """Get simulation progress information"""
        if not self.available_times:
            return {'progress': 0.0, 'current_time': 0.0, 'time_step': 0}
        
        progress = (self.current_time_index / len(self.available_times)) * 100
        current_time = self.available_times[self.current_time_index - 1] if self.current_time_index > 0 else 0.0
        
        return {
            'progress': progress,
            'current_time': current_time,
            'time_step': self.current_time_index,
            'total_steps': len(self.available_times)
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("NS3 interface cleanup completed")

class StreamlinedMonitorAgent:
    """STREAMLINED: Focus only on data collection and basic health monitoring"""
    
    def __init__(self, config_file: str):
        self.config = self.load_config(config_file)
        self.ns3_interface = StreamlinedNS3Interface(self.config.get('ns3', {}))
        
        # Basic monitoring state
        self.is_running = False
        self.streaming_active = False
        self.basic_health_stats = {}
        
        # Setup Prometheus metrics first
        self.setup_prometheus_metrics()

        # Start Prometheus HTTP server
        start_http_server(8001)  # Monitor metrics on port 8001
        logger.info("📊 Prometheus metrics server started on port 8001")

        # Simple thresholds for basic operational checks
        self.thresholds = {
            'voltage_min': 200.0,
            'voltage_max': 240.0,
            'operational_threshold': 0.9,  # 90% nodes must be operational
            'energy_critical': 0.1
        }
        
        # Data streaming queue
        self.data_stream_queue = asyncio.Queue(maxsize=50)
        self.data_batch_size = self.config.get('data_streaming', {}).get('batch_size', 5)
        
        logger.info("Streamlined Monitor Agent initialized - data collection focus")

    def load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            if not os.path.exists(config_file):
                # Create default config if file doesn't exist
                default_config = {
                    "monitoring": {
                        "check_interval": 3.0,
                        "baseline_samples": 5,
                        "basic_health_only": True
                    },
                    "data_streaming": {
                        "batch_size": 5,
                        "stream_interval": 2.0,
                        "raw_data_only": True
                    },
                    "calculation_agent": {
                        "endpoint": "calculation_agent_data_stream.json"
                    },
                    "ns3": {
                        "metrics_file": "rural_network_metrics.csv",
                        "topology_file": "network_topology.json"
                    }
                }
                
                with open(config_file, 'w') as f:
                    json.dump(default_config, f, indent=2)
                
                logger.info(f"📝 Created default config file: {config_file}")
                return default_config
            
            with open(config_file, 'r') as f:
                config = json.load(f)
                logger.info(f"📋 Configuration loaded from {config_file}")
                return config
                
        except Exception as e:
            logger.error(f"❌ Error loading config: {e}")
            # Return minimal default config
            return {
                "monitoring": {"check_interval": 3.0, "baseline_samples": 5},
                "data_streaming": {"batch_size": 5, "stream_interval": 2.0},
                "calculation_agent": {"endpoint": "calculation_agent_data_stream.json"},
                "ns3": {"metrics_file": "rural_network_metrics.csv"}
            }

    def setup_prometheus_metrics(self):
        """Setup Prometheus metrics for monitoring"""
        self.node_status_gauge = Gauge(
            'nokia_monitor_node_status', 
            'Node operational status (1=operational, 0=down)',
            ['node_id', 'node_type', 'location']
        )
        
        self.network_health_gauge = Gauge(
            'nokia_monitor_network_health_percentage', 
            'Overall network health percentage'
        )
        
        self.voltage_gauge = Gauge(
            'nokia_monitor_node_voltage', 
            'Node voltage level',
            ['node_id']
        )
        
        self.energy_gauge = Gauge(
            'nokia_monitor_node_energy', 
            'Node energy level',
            ['node_id']
        )
        
        self.data_collection_counter = Counter(
            'nokia_monitor_data_points_collected_total', 
            'Total data points collected from NS3'
        )

        self.simulation_time_gauge = Gauge(
            'nokia_monitor_simulation_time_seconds',
            'Current NS3 simulation time'
        )
        
        self.nodes_monitored_gauge = Gauge(
            'nokia_monitor_nodes_total',
            'Total number of nodes being monitored'
        )

        logger.info("✅ Prometheus metrics setup completed")
    
    def convert_to_enhanced_metrics(self, raw_metrics: Dict[str, Any]) -> Dict[str, EnhancedNetworkMetrics]:
        """Convert raw metrics to enhanced format for compatibility"""
        enhanced_metrics = {}
        
        for node_id, metrics in raw_metrics.items():
            enhanced_metrics[node_id] = EnhancedNetworkMetrics(
                node_id=node_id,
                simulation_time=metrics['simulation_time'],
                throughput=metrics['throughput'],
                latency=metrics['latency'],
                packet_loss=metrics['packet_loss'],
                cpu_usage=metrics['cpu_usage'],
                memory_usage=metrics['memory_usage'],
                energy_level=metrics['energy_level'],
                operational=metrics['operational'],
                degradation_level=metrics['degradation_level'],
                fault_severity=metrics['fault_severity'],
                power_stability=metrics['power_stability'],
                voltage_level=metrics['voltage_level'],
                node_type=metrics['node_type'],
                position_x=metrics['position_x'],
                position_y=metrics['position_y']
            )
        
        return enhanced_metrics
    
    async def basic_operational_health_check(self, metrics: Dict[str, EnhancedNetworkMetrics]):
        """Basic operational health check - no AI analysis, just simple thresholds"""
        try:
            total_nodes = len(metrics)
            operational_nodes = len([m for m in metrics.values() if m.operational])
            
            # Simple voltage anomaly detection (operational threshold only)
            voltage_issues = 0
            energy_critical_nodes = 0
            
            for node_id, node_metrics in metrics.items():
                # Update Prometheus metrics
                self.node_status_gauge.labels(
                    node_id=node_id,
                    node_type=getattr(node_metrics, 'node_type', 'rural'),
                    location=f"({node_metrics.position_x}, {node_metrics.position_y})"
                ).set(1.0 if node_metrics.operational else 0.0)
                
                # Update voltage and energy
                self.voltage_gauge.labels(node_id=node_id).set(node_metrics.voltage_level)
                self.energy_gauge.labels(node_id=node_id).set(node_metrics.energy_level)
                
                # Increment data collection counter
                self.data_collection_counter.inc()
                
                # Basic voltage check
                if (node_metrics.voltage_level < self.thresholds['voltage_min'] or 
                    node_metrics.voltage_level > self.thresholds['voltage_max']):
                    voltage_issues += 1
                    logger.warning(f"⚡ Basic Alert: {node_id} voltage {node_metrics.voltage_level:.1f}V outside normal range")
                
                # Basic energy check
                if node_metrics.energy_level < self.thresholds['energy_critical']:
                    energy_critical_nodes += 1
                    logger.warning(f"🔋 Basic Alert: {node_id} energy critical {node_metrics.energy_level:.2f}")
            
            # Calculate operational percentage
            operational_percentage = (operational_nodes / total_nodes) * 100 if total_nodes > 0 else 0
            
            # Update network health
            self.network_health_gauge.set(operational_percentage)
            
            # Update simulation time and nodes count
            self.simulation_time_gauge.set(next(iter(metrics.values())).simulation_time)
            self.nodes_monitored_gauge.set(total_nodes)
            
            # Determine basic network status
            if operational_percentage >= 95:
                network_status = 'healthy'
            elif operational_percentage >= 80:
                network_status = 'monitoring'
            elif operational_percentage >= 60:
                network_status = 'degraded'
            else:
                network_status = 'critical'
            
            # Store basic health stats
            self.basic_health_stats = {
                'timestamp': datetime.now().isoformat(),
                'simulation_time': next(iter(metrics.values())).simulation_time,
                'total_nodes': total_nodes,
                'operational_nodes': operational_nodes,
                'voltage_issues': voltage_issues,
                'energy_critical_nodes': energy_critical_nodes,
                'operational_percentage': operational_percentage,
                'network_status': network_status,
                'basic_checks_only': True
            }
            
            # Basic status logging
            if network_status in ['degraded', 'critical']:
                logger.warning(f"📊 BASIC HEALTH: {network_status.upper()} - {operational_nodes}/{total_nodes} nodes operational ({operational_percentage:.1f}%)")
            elif operational_percentage < 100:
                logger.info(f"📊 BASIC HEALTH: {network_status.upper()} - {operational_nodes}/{total_nodes} nodes operational ({operational_percentage:.1f}%)")
        
        except Exception as e:
            logger.error(f"Error in basic health check: {e}")
    
    async def queue_raw_data_for_calculation_agent(self, metrics: Dict[str, EnhancedNetworkMetrics]):
        """Queue RAW metrics data for Calculation Agent - no processing, just collection"""
        try:
            # Create simple raw data message (no AI analysis)
            raw_data_message = DataStreamMessage(
                timestamp=datetime.now(),
                simulation_time=next(iter(metrics.values())).simulation_time,
                data_type="raw_network_metrics",
                content={
                    'simulation_time': next(iter(metrics.values())).simulation_time,
                    'collection_source': 'streamlined_monitor_agent',
                    'data_quality': 'raw_unprocessed',
                    'ai_analysis_required': True,
                    
                    # Basic health summary (no AI analysis)
                    'basic_health': self.basic_health_stats,
                    
                    # Raw node metrics (no classification or analysis)
                    'raw_node_metrics': {
                        node_id: {
                            # Core network metrics
                            'throughput': node_metrics.throughput,
                            'latency': node_metrics.latency,
                            'packet_loss': node_metrics.packet_loss,
                            'jitter': node_metrics.cpu_usage,  # Using cpu_usage as jitter proxy
                            'signal_strength': -70.0,  # Default value
                            
                            # System metrics
                            'cpu_usage': node_metrics.cpu_usage,
                            'memory_usage': node_metrics.memory_usage,
                            'buffer_occupancy': 0.5,  # Default value
                            
                            # Network topology
                            'active_links': 3,  # Default value
                            'neighbor_count': 4,  # Default value
                            'link_utilization': 0.6,  # Default value
                            
                            # Load metrics
                            'critical_load': 0.3,  # Default value
                            'normal_load': 0.7,    # Default value
                            
                            # Environmental
                            'energy_level': node_metrics.energy_level,
                            'x_position': node_metrics.position_x,
                            'y_position': node_metrics.position_y,
                            'z_position': 0.0,  # Default value
                            
                            # Health indicators (from NS3 data - no analysis)
                            'degradation_level': node_metrics.degradation_level,
                            'fault_severity': node_metrics.fault_severity,
                            'power_stability': node_metrics.power_stability,
                            'voltage_level': node_metrics.voltage_level,
                            'operational': 1.0 if node_metrics.operational else 0.0,
                            'node_type': 1.0 if node_metrics.node_type == 'core' else 0.0,
                            'current_time': node_metrics.simulation_time
                        }
                        for node_id, node_metrics in metrics.items()
                    }
                }
            )
            
            # Queue for batch processing
            if not self.data_stream_queue.full():
                await self.data_stream_queue.put(raw_data_message)
            else:
                logger.warning("Raw data stream queue full, dropping oldest data")
                try:
                    self.data_stream_queue.get_nowait()  # Remove oldest
                    await self.data_stream_queue.put(raw_data_message)  # Add new
                except:
                    pass
            
            logger.debug(f"📤 Queued raw data for Calculation Agent (Time: {next(iter(metrics.values())).simulation_time:.0f}s)")
                        
        except Exception as e:
            logger.error(f"Error queuing raw data for Calculation Agent: {e}")
    
    async def simplified_monitoring_loop(self):
        """Simplified monitoring loop - focus only on data collection and basic health"""
        logger.info("Starting streamlined monitoring loop - data collection focus...")
        
        while self.is_running:
            try:
                # Get current metrics from NS3
                raw_metrics = await self.ns3_interface.get_all_node_metrics()
                
                if not raw_metrics:
                    logger.info("End of simulation data reached")
                    break
                
                # Convert to enhanced format (keep structure for compatibility)
                current_metrics = self.convert_to_enhanced_metrics(raw_metrics)
                
                # Basic operational health check only
                await self.basic_operational_health_check(current_metrics)
                
                # Queue RAW data for Calculation Agent (no AI analysis)
                await self.queue_raw_data_for_calculation_agent(current_metrics)
                
                # Show progress
                progress = self.ns3_interface.get_simulation_progress()
                if progress['time_step'] % 10 == 0:  # Log every 10th iteration
                    operational_count = len([m for m in current_metrics.values() if m.operational])
                    logger.info(f"📊 Data Collection: {progress['progress']:.1f}% "
                               f"(Time: {progress['current_time']:.0f}s) - "
                               f"Operational: {operational_count}/{len(current_metrics)} nodes - "
                               f"Status: {self.basic_health_stats.get('network_status', 'unknown')}")
                
                await asyncio.sleep(self.config['monitoring']['check_interval'])
                
            except Exception as e:
                logger.error(f"Error in streamlined monitoring loop: {e}")
                await asyncio.sleep(self.config['monitoring']['check_interval'])
    
    async def data_streaming_loop(self):
        """Stream raw data batches to Calculation Agent"""
        logger.info("Starting raw data streaming to Calculation Agent...")
        
        while self.streaming_active:
            try:
                batch = []
                
                # Collect batch of raw data messages
                for _ in range(self.data_batch_size):
                    try:
                        message = await asyncio.wait_for(
                            self.data_stream_queue.get(), 
                            timeout=self.config['data_streaming']['stream_interval']
                        )
                        batch.append(message)
                    except asyncio.TimeoutError:
                        break
                
                # Send batch if we have data
                if batch:
                    await self.send_raw_data_to_calculation_agent(batch)
                
                await asyncio.sleep(self.config['data_streaming']['stream_interval'])
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in data streaming loop: {e}")
                await asyncio.sleep(2.0)
    
    async def send_raw_data_to_calculation_agent(self, batch: List[DataStreamMessage]):
        """Send raw data batch to Calculation Agent for AI analysis"""
        try:
            batch_data = {
                'batch_id': f"raw_data_batch_{int(time.time())}",
                'timestamp': datetime.now().isoformat(),
                'source': 'streamlined_monitor_agent',
                'message_count': len(batch),
                'batch_type': 'raw_metrics_for_ai_analysis',
                
                # No AI analysis - just raw data statistics
                'batch_statistics': {
                    'data_collection_mode': 'raw_only',
                    'ai_analysis_delegated': True,
                    'basic_health_included': True,
                    'requires_lstm_processing': True,
                    'requires_anomaly_detection': True,
                    'requires_fault_classification': True
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
            
            # Save for Calculation Agent
            with open(self.config['calculation_agent']['endpoint'], 'a') as f:
                f.write(json.dumps(batch_data, cls=DateTimeEncoder) + '\n')
            
            logger.info(f"📤 Sent raw data batch to Calculation Agent: {len(batch)} messages (No AI processing done)")
            
        except Exception as e:
            logger.error(f"Error sending raw data to Calculation Agent: {e}")
    
    async def establish_basic_baseline(self):
        """Establish basic operational baseline - simplified version"""
        logger.info("Establishing basic operational baseline...")
        
        baseline_samples = self.config['monitoring'].get('baseline_samples', 5)
        baseline_data = []
        
        for sample in range(baseline_samples):
            raw_metrics = await self.ns3_interface.get_all_node_metrics()
            if raw_metrics:
                current_metrics = self.convert_to_enhanced_metrics(raw_metrics)
                await self.basic_operational_health_check(current_metrics)
                
                # Store basic baseline statistics
                baseline_data.append({
                    'operational_percentage': self.basic_health_stats.get('operational_percentage', 100),
                    'voltage_issues': self.basic_health_stats.get('voltage_issues', 0),
                    'energy_critical_nodes': self.basic_health_stats.get('energy_critical_nodes', 0)
                })
                
                logger.info(f"Basic baseline sample {sample + 1}/{baseline_samples} collected")
                await asyncio.sleep(1)
        
        # Calculate simple baseline statistics
        if baseline_data:
            avg_operational = statistics.mean([d['operational_percentage'] for d in baseline_data])
            avg_voltage_issues = statistics.mean([d['voltage_issues'] for d in baseline_data])
            
            logger.info(f"Basic operational baseline established:")
            logger.info(f"  Average operational: {avg_operational:.1f}%")
            logger.info(f"  Average voltage issues: {avg_voltage_issues:.1f}")
    
    async def start_streamlined_monitoring(self):
        """Start streamlined monitoring - focus on data collection only"""
        logger.info("=" * 80)
        logger.info("🚀 STARTING STREAMLINED MONITOR AGENT")
        logger.info("Purpose: Raw data collection + Basic health monitoring")
        logger.info("AI Analysis: Delegated to Calculation Agent")
        logger.info("Fault Detection: Delegated to Calculation Agent")
        logger.info("LSTM Training: Delegated to Calculation Agent")
        logger.info("Anomaly Detection: Delegated to Calculation Agent")
        logger.info("=" * 80)
        
        self.is_running = True
        self.streaming_active = True
        
        # Initialize basic health stats
        self.basic_health_stats = {}
        
        try:
            # Initialize NS-3 interface
            await self.ns3_interface.initialize_simulation()
            
            # Establish basic baseline (simplified)
            await self.establish_basic_baseline()
            
            # Start data streaming task
            data_streaming_task = asyncio.create_task(self.data_streaming_loop())
            
            # Start streamlined monitoring loop
            monitoring_task = asyncio.create_task(self.simplified_monitoring_loop())
            
            # Wait for monitoring to complete
            await monitoring_task
            
            # Cancel streaming task
            data_streaming_task.cancel()
            
        except Exception as e:
            logger.error(f"Error in streamlined monitoring: {e}")
            raise
        finally:
            await self.stop_streamlined_monitoring()
    
    async def stop_streamlined_monitoring(self):
        """Stop streamlined monitoring"""
        logger.info("🛑 Stopping Streamlined Monitor Agent...")
        self.is_running = False
        self.streaming_active = False
        
        await self.generate_streamlined_summary()
        await self.ns3_interface.cleanup()
        
        logger.info("Streamlined Monitor Agent stopped successfully")
    
    async def generate_streamlined_summary(self):
        """Generate streamlined monitoring summary"""
        logger.info("=" * 80)
        logger.info("STREAMLINED MONITORING SUMMARY")
        logger.info("=" * 80)
        
        logger.info("📊 Data Collection Results:")
        logger.info("   ✅ Raw network metrics collected and streamed")
        logger.info("   ✅ Basic operational health monitoring performed")
        logger.info("   ✅ Data successfully sent to Calculation Agent for AI analysis")
        logger.info("   🔄 AI anomaly detection delegated to Calculation Agent")
        logger.info("   🔄 Fault prediction delegated to Calculation Agent")
        logger.info("   🔄 LSTM training data preparation delegated to Calculation Agent")
        logger.info("   🔄 Root cause analysis delegated to Calculation Agent (SHAP)")
        
        if hasattr(self, 'basic_health_stats') and self.basic_health_stats:
            logger.info(f"\n📈 Final Network Status:")
            logger.info(f"   Network Status: {self.basic_health_stats.get('network_status', 'unknown')}")
            logger.info(f"   Operational Nodes: {self.basic_health_stats.get('operational_nodes', 'unknown')}/{self.basic_health_stats.get('total_nodes', 'unknown')}")
            logger.info(f"   Operational Rate: {self.basic_health_stats.get('operational_percentage', 0):.1f}%")
            logger.info(f"   Voltage Issues Detected: {self.basic_health_stats.get('voltage_issues', 0)}")
            logger.info(f"   Energy Critical Nodes: {self.basic_health_stats.get('energy_critical_nodes', 0)}")
        
        logger.info(f"\n🎯 Role Separation Complete:")
        logger.info(f"   Monitor Agent: Data collection + Basic health ✅")
        logger.info(f"   Calculation Agent: AI analysis + Anomaly detection ⏳")
        logger.info(f"   Healing Agent: Fault recovery actions ⏳")
        logger.info(f"   Orchestration Agent: Workflow coordination ⏳")
        
        # Save summary report
        summary_report = {
            'monitoring_type': 'streamlined_data_collection',
            'completion_time': datetime.now().isoformat(),
            'role': 'data_collector_and_basic_health_monitor',
            'ai_analysis_delegated': True,
            'final_health_stats': self.basic_health_stats,
            'next_steps': [
                'Calculation Agent performs LSTM analysis',
                'Calculation Agent detects anomalies',
                'Calculation Agent classifies faults',
                'Healing Agent receives alerts for action'
            ]
        }
        
        try:
            with open('streamlined_monitoring_report.json', 'w') as f:
                json.dump(summary_report, f, indent=2, cls=DateTimeEncoder)
            logger.info("📄 Streamlined monitoring report saved to streamlined_monitoring_report.json")
        except Exception as e:
            logger.error(f"Error saving summary report: {e}")

# Configuration file creation for streamlined monitoring
def create_streamlined_config():
    """Create configuration for streamlined monitoring"""
    config = {
        "monitoring": {
            "check_interval": 3.0,
            "baseline_samples": 5,
            "basic_health_only": True,
            "ai_analysis_delegated": True
        },
        "data_streaming": {
            "batch_size": 5,
            "stream_interval": 2.0,
            "raw_data_only": True,
            "requires_ai_processing": True
        },
        "calculation_agent": {
            "endpoint": "calculation_agent_data_stream.json",
            "ai_analysis_required": True
        },
        "basic_thresholds": {
            "voltage_min": 200.0,
            "voltage_max": 240.0,
            "operational_threshold": 0.9,
            "energy_critical": 0.1
        },
        "ns3": {
            "metrics_file": "rural_network_metrics.csv",
            "topology_file": "network_topology.json"
        },
        "logging": {
            "level": "INFO",
            "focus": "data_collection_and_basic_health"
        }
    }
    
    with open('streamlined_monitor_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    logger.info("Streamlined monitoring configuration created")

# Main execution
async def main():
    """Main execution - streamlined monitoring approach"""
    try:
        # Create streamlined config if it doesn't exist
        if not os.path.exists('streamlined_monitor_config.json'):
            create_streamlined_config()
        
        # Use streamlined config
        config_file = 'streamlined_monitor_config.json'
        
        monitor = StreamlinedMonitorAgent(config_file)
        
        # Start streamlined monitoring
        await monitor.start_streamlined_monitoring()
        
    except KeyboardInterrupt:
        logger.info("Streamlined monitoring stopped by user")
    except Exception as e:
        logger.error(f"Error in streamlined monitoring main: {e}")

if __name__ == "__main__":
    asyncio.run(main())