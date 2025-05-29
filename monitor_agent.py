# monitor_agent.py (ROBUST MONITOR AGENT FOR REAL NS-3 DATA)
import asyncio
import logging
import json
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
from ns3_network_interface import NS3NetworkInterface

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class NetworkMetrics:
    """Network metrics structure"""
    node_id: str
    timestamp: datetime
    throughput: float
    latency: float
    packet_loss: float
    voltage_level: float
    operational: bool
    node_type: str
    current_time: float

@dataclass
class FaultAlert:
    """Fault alert structure"""
    alert_id: str
    node_id: str
    fault_type: str
    severity: str
    detection_time: datetime
    simulation_time: float
    metrics: Dict[str, Any]
    description: str

class RuralNetworkMonitorAgent:
    """Robust Monitor Agent for Rural Network Fault Detection"""
    
    def __init__(self, config_file: str = "monitor_config.json"):
        self.config = self.load_configuration(config_file)
        
        # Initialize NS-3 interface
        self.ns3_interface = NS3NetworkInterface(self.config.get('ns3', {}))
        
        # Monitoring state
        self.is_running = False
        self.detected_faults = []
        self.node_baseline = {}
        self.fault_history = {}
        
        # Detection thresholds
        self.thresholds = self.config['thresholds']
        
        logger.info("Rural Network Monitor Agent initialized")

    def load_configuration(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            logger.info(f"Configuration loaded from {config_file}")
            return config
        except FileNotFoundError:
            logger.warning(f"Config file {config_file} not found, using defaults")
            return self.get_default_config()

    def get_default_config(self) -> Dict[str, Any]:
        """Default configuration"""
        return {
            "ns3": {
                "metrics_file": "rural_network_metrics.csv",
                "topology_file": "network_topology.json"
            },
            "thresholds": {
                "throughput_min": 15.0,
                "latency_max": 150.0,
                "packet_loss_max": 0.05,
                "voltage_min": 200.0,
                "voltage_max": 240.0,
                "power_stability_min": 0.85
            },
            "monitoring": {
                "check_interval": 2.0,
                "baseline_samples": 5
            }
        }

    async def start_monitoring(self):
        """Start the monitoring process"""
        logger.info("=" * 60)
        logger.info("STARTING RURAL NETWORK MONITOR AGENT")
        logger.info("=" * 60)
        
        self.is_running = True
        
        try:
            # Initialize NS-3 data
            await self.ns3_interface.initialize_simulation()
            
            # Establish baseline
            await self.establish_baseline()
            
            # Start main monitoring loop
            await self.monitoring_loop()
            
        except Exception as e:
            logger.error(f"Error in monitoring: {e}")
            raise
        finally:
            await self.stop_monitoring()

    async def establish_baseline(self):
        """Establish baseline metrics for fault detection"""
        logger.info("Establishing baseline metrics...")
        
        baseline_samples = self.config['monitoring']['baseline_samples']
        
        for sample in range(baseline_samples):
            # Get current metrics
            raw_metrics = await self.ns3_interface.get_all_node_metrics()
            
            if not raw_metrics:
                logger.warning("No metrics available for baseline")
                break
            
            # Process metrics
            current_metrics = self.convert_metrics(raw_metrics)
            
            # Store baseline data
            for node_id, metrics in current_metrics.items():
                if node_id not in self.node_baseline:
                    self.node_baseline[node_id] = {
                        'throughput_samples': [],
                        'latency_samples': [],
                        'voltage_samples': []
                    }
                
                self.node_baseline[node_id]['throughput_samples'].append(metrics.throughput)
                self.node_baseline[node_id]['latency_samples'].append(metrics.latency)
                self.node_baseline[node_id]['voltage_samples'].append(metrics.voltage_level)
            
            logger.info(f"Baseline sample {sample + 1}/{baseline_samples} collected")
            await asyncio.sleep(1)
        
        # Calculate baseline statistics
        for node_id, samples in self.node_baseline.items():
            if samples['throughput_samples']:
                samples['throughput_avg'] = sum(samples['throughput_samples']) / len(samples['throughput_samples'])
                samples['voltage_avg'] = sum(samples['voltage_samples']) / len(samples['voltage_samples'])
                samples['latency_avg'] = sum(samples['latency_samples']) / len(samples['latency_samples'])
        
        logger.info(f"Baseline established for {len(self.node_baseline)} nodes")

    async def monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("Starting main monitoring loop...")
        
        while self.is_running:
            try:
                # Get current network state
                raw_metrics = await self.ns3_interface.get_all_node_metrics()
                
                if not raw_metrics:
                    logger.info("End of simulation data reached")
                    break
                
                # Convert to monitoring format
                current_metrics = self.convert_metrics(raw_metrics)
                
                # Show progress
                progress = self.ns3_interface.get_simulation_progress()
                logger.info(f"Monitoring progress: {progress['progress']:.1f}% "
                           f"(Time: {progress['current_time']:.0f}s/{progress['total_time']:.0f}s)")
                
                # Detect faults
                detected_faults = self.detect_faults(current_metrics)
                
                # Process any detected faults
                if detected_faults:
                    await self.process_detected_faults(detected_faults)
                
                # Check for fault recovery
                await self.check_fault_recovery(current_metrics)
                
                # Wait for next check
                await asyncio.sleep(self.config['monitoring']['check_interval'])
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.config['monitoring']['check_interval'])

    def convert_metrics(self, raw_metrics: Dict[str, Dict[str, float]]) -> Dict[str, NetworkMetrics]:
        """Convert raw metrics to monitoring format"""
        metrics = {}
        current_time = datetime.now()
        
        for node_id, data in raw_metrics.items():
            metrics[node_id] = NetworkMetrics(
                node_id=node_id,
                timestamp=current_time,
                throughput=data.get('throughput', 0.0),
                latency=data.get('latency', 0.0),
                packet_loss=data.get('packet_loss', 0.0),
                voltage_level=data.get('voltage_level', 220.0),
                operational=data.get('operational', True),
                node_type=data.get('node_type', 'unknown'),
                current_time=data.get('current_time', 0.0)
            )
        
        return metrics

    def detect_faults(self, metrics: Dict[str, NetworkMetrics]) -> List[FaultAlert]:
        """Detect faults using threshold-based detection"""
        detected_faults = []
        
        for node_id, node_metrics in metrics.items():
            # Skip if already in fault state
            if node_id in self.fault_history and self.fault_history[node_id]['active']:
                continue
            
            # 1. OPERATIONAL STATUS FAULT (Most Critical)
            if not node_metrics.operational:
                fault = self.create_fault_alert(
                    node_id, "node_failure", "CRITICAL", node_metrics,
                    f"Node {node_id} is non-operational (likely fiber cut or hardware failure)"
                )
                detected_faults.append(fault)
                continue
            
            # 2. VOLTAGE/POWER FAULTS
            if (node_metrics.voltage_level < self.thresholds['voltage_min'] or 
                node_metrics.voltage_level > self.thresholds['voltage_max']):
                fault = self.create_fault_alert(
                    node_id, "power_fluctuation", "HIGH", node_metrics,
                    f"Voltage out of range: {node_metrics.voltage_level:.1f}V "
                    f"(normal: {self.thresholds['voltage_min']}-{self.thresholds['voltage_max']}V)"
                )
                detected_faults.append(fault)
            
            # 3. PERFORMANCE DEGRADATION
            baseline = self.node_baseline.get(node_id, {})
            
            # Throughput degradation
            if baseline.get('throughput_avg', 0) > 0:
                throughput_drop = (baseline['throughput_avg'] - node_metrics.throughput) / baseline['throughput_avg']
                if throughput_drop > 0.5:  # 50% drop
                    fault = self.create_fault_alert(
                        node_id, "throughput_degradation", "HIGH", node_metrics,
                        f"Throughput dropped {throughput_drop*100:.1f}% from baseline "
                        f"({node_metrics.throughput:.1f} vs {baseline['throughput_avg']:.1f} Mbps)"
                    )
                    detected_faults.append(fault)
            
            # Latency spike
            if node_metrics.latency > self.thresholds['latency_max']:
                fault = self.create_fault_alert(
                    node_id, "high_latency", "MEDIUM", node_metrics,
                    f"High latency detected: {node_metrics.latency:.1f}ms "
                    f"(threshold: {self.thresholds['latency_max']}ms)"
                )
                detected_faults.append(fault)
            
            # Packet loss
            if node_metrics.packet_loss > self.thresholds['packet_loss_max']:
                fault = self.create_fault_alert(
                    node_id, "high_packet_loss", "HIGH", node_metrics,
                    f"High packet loss: {node_metrics.packet_loss*100:.1f}% "
                    f"(threshold: {self.thresholds['packet_loss_max']*100:.1f}%)"
                )
                detected_faults.append(fault)
        
        return detected_faults

    def create_fault_alert(self, node_id: str, fault_type: str, severity: str, 
                          metrics: NetworkMetrics, description: str) -> FaultAlert:
        """Create a fault alert"""
        alert_id = f"FAULT_{int(time.time())}_{node_id}_{fault_type}"
        
        fault_alert = FaultAlert(
            alert_id=alert_id,
            node_id=node_id,
            fault_type=fault_type,
            severity=severity,
            detection_time=datetime.now(),
            simulation_time=metrics.current_time,
            metrics={
                'throughput': metrics.throughput,
                'latency': metrics.latency,
                'packet_loss': metrics.packet_loss,
                'voltage_level': metrics.voltage_level,
                'operational': metrics.operational,
                'node_type': metrics.node_type
            },
            description=description
        )
        
        return fault_alert

    async def process_detected_faults(self, faults: List[FaultAlert]):
        """Process and log detected faults"""
        for fault in faults:
            # Log the fault
            logger.warning("=" * 80)
            logger.warning(f"🚨 FAULT DETECTED: {fault.fault_type.upper()}")
            logger.warning(f"Node: {fault.node_id}")
            logger.warning(f"Severity: {fault.severity}")
            logger.warning(f"Simulation Time: {fault.simulation_time:.0f}s")
            logger.warning(f"Description: {fault.description}")
            logger.warning(f"Metrics: {fault.metrics}")
            logger.warning("=" * 80)
            
            # Store in history
            self.fault_history[fault.node_id] = {
                'fault': fault,
                'active': True,
                'detection_time': fault.simulation_time
            }
            
            # Store for analysis
            self.detected_faults.append(fault)
            
            # In real implementation, this would trigger the Orchestration Agent
            logger.info(f"🔧 Alert would be sent to Orchestration Agent for {fault.node_id}")

    async def check_fault_recovery(self, metrics: Dict[str, NetworkMetrics]):
        """Check if previously failed nodes have recovered"""
        recovered_nodes = []
        
        for node_id, fault_info in self.fault_history.items():
            if not fault_info['active']:
                continue
            
            # Check if node is back to normal
            if node_id in metrics:
                node_metrics = metrics[node_id]
                
                # Recovery conditions
                is_operational = node_metrics.operational
                voltage_ok = (self.thresholds['voltage_min'] <= node_metrics.voltage_level <= self.thresholds['voltage_max'])
                latency_ok = node_metrics.latency <= self.thresholds['latency_max']
                
                if is_operational and voltage_ok and latency_ok:
                    logger.info("=" * 80)
                    logger.info(f"✅ FAULT RECOVERY DETECTED")
                    logger.info(f"Node: {node_id}")
                    logger.info(f"Original Fault: {fault_info['fault'].fault_type}")
                    logger.info(f"Recovery Time: {node_metrics.current_time:.0f}s")
                    logger.info(f"Fault Duration: {node_metrics.current_time - fault_info['detection_time']:.0f}s")
                    logger.info("=" * 80)
                    
                    fault_info['active'] = False
                    fault_info['recovery_time'] = node_metrics.current_time
                    recovered_nodes.append(node_id)

    async def stop_monitoring(self):
        """Stop monitoring and generate summary"""
        logger.info("Stopping Monitor Agent...")
        self.is_running = False
        
        # Generate fault detection summary
        await self.generate_fault_summary()
        
        # Cleanup
        await self.ns3_interface.cleanup()
        
        logger.info("Monitor Agent stopped successfully")

    async def generate_fault_summary(self):
        """Generate fault detection summary"""
        logger.info("=" * 80)
        logger.info("FAULT DETECTION SUMMARY")
        logger.info("=" * 80)
        
        if not self.detected_faults:
            logger.info("✅ No faults detected during monitoring")
            return
        
        # Group faults by type
        fault_types = {}
        for fault in self.detected_faults:
            if fault.fault_type not in fault_types:
                fault_types[fault.fault_type] = []
            fault_types[fault.fault_type].append(fault)
        
        logger.info(f"Total faults detected: {len(self.detected_faults)}")
        logger.info(f"Fault types: {list(fault_types.keys())}")
        
        for fault_type, faults in fault_types.items():
            logger.info(f"\n{fault_type.upper()}: {len(faults)} instances")
            for fault in faults:
                logger.info(f"  - {fault.node_id} at {fault.simulation_time:.0f}s ({fault.severity})")
        
        # Recovery statistics
        active_faults = sum(1 for info in self.fault_history.values() if info['active'])
        recovered_faults = len(self.fault_history) - active_faults
        
        logger.info(f"\nRecovery Statistics:")
        logger.info(f"  - Active faults: {active_faults}")
        logger.info(f"  - Recovered faults: {recovered_faults}")
        
        # Save detailed report
        self.save_fault_report()

    def save_fault_report(self):
        """Save detailed fault report to file"""
        report = {
            'monitoring_session': {
                'start_time': datetime.now().isoformat(),
                'total_faults': len(self.detected_faults),
                'fault_types': list(set(f.fault_type for f in self.detected_faults))
            },
            'detected_faults': [
                {
                    'alert_id': f.alert_id,
                    'node_id': f.node_id,
                    'fault_type': f.fault_type,
                    'severity': f.severity,
                    'simulation_time': f.simulation_time,
                    'description': f.description,
                    'metrics': f.metrics
                }
                for f in self.detected_faults
            ],
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
        
        with open('fault_detection_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info("Detailed fault report saved to 'fault_detection_report.json'")

# Main execution
async def main():
    """Main function to run the monitor agent"""
    monitor = RuralNetworkMonitorAgent()
    
    try:
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        await monitor.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(main())