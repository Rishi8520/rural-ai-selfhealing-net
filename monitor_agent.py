import os
import json
import csv
import logging
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

class MonitorAgent:
    """
    Monitor Agent for NS-3 Rural Network Simulation
    Focuses on essential files needed for Calculation Agent (LSTM + SHAP)
    """
    
    def __init__(self):
        # Directory structure
        self.ns3_simulation_dir = Path("ns3_simulation")
        self.faults_dir = self.ns3_simulation_dir / "Faults"
        self.output_dir = Path("monitor_output")
        self.output_dir.mkdir(exist_ok=True)
        
        # ONLY essential files for Calculation Agent
        self.essential_files = {
            'metrics': self.faults_dir / 'fault_demo_network_metrics.csv',      # LSTM training data
            'fault_events': self.faults_dir / 'fault_demo_fault_events.log',    # Fault timeline  
            'config': self.faults_dir / 'fault_demo_config.json'                # Simulation params
        }
        
        # Optional files (won't show warnings if missing)
        self.optional_files = {
            'topology': self.faults_dir / 'fault_demo_topology.json'             # Network structure
        }
        
        # Tracking
        self.last_processed = {}
        
        logger.info("✅ Monitor Agent initialized (Essential Files Only)")
        logger.info(f"📁 Monitoring directory: {self.faults_dir}")
        logger.info(f"📁 Output directory: {self.output_dir}")

    async def start_monitoring(self):
        """Start monitoring essential NS-3 simulation outputs"""
        logger.info("🚀 Starting Monitor Agent...")
        logger.info("📊 Monitoring 3 essential files for Calculation Agent:")
        logger.info("   • Network Metrics CSV (LSTM training)")
        logger.info("   • Fault Events Log (anomaly timeline)")  
        logger.info("   • Config JSON (simulation parameters)")
        
        # Initial scan
        await self.scan_essential_files()
        
        while True:
            try:
                if await self.check_for_new_data():
                    logger.info("🔄 Processing new simulation data...")
                    
                    processed_data = await self.process_simulation_data()
                    
                    if processed_data and self.validate_data(processed_data):
                        output_file = await self.create_calculation_input(processed_data)
                        
                        if output_file:
                            await self.notify_calculation_agent(processed_data, output_file)
                    else:
                        logger.warning("⚠️ Data validation failed")
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"❌ Monitor Agent error: {e}")
                await asyncio.sleep(5)

    async def scan_essential_files(self):
        """Scan only essential files - no warnings for missing optional files"""
        logger.info("📋 Essential Files Status:")
        
        essential_count = 0
        for file_type, file_path in self.essential_files.items():
            if file_path.exists():
                essential_count += 1
                file_size = file_path.stat().st_size
                logger.info(f"  ✅ {file_type}: {file_path.name} ({self.format_file_size(file_size)})")
            else:
                logger.error(f"  ❌ {file_type}: {file_path.name} (REQUIRED - MISSING)")
        
        # Check optional files (no error if missing)
        logger.info("📋 Optional Files:")
        for file_type, file_path in self.optional_files.items():
            if file_path.exists():
                file_size = file_path.stat().st_size  
                logger.info(f"  ✅ {file_type}: {file_path.name} ({self.format_file_size(file_size)})")
            else:
                logger.info(f"  ⚪ {file_type}: {file_path.name} (optional - not present)")
        
        logger.info(f"📈 Essential Files: {essential_count}/3 available")
        
        if essential_count == 3:
            logger.info("🎯 All essential files ready for Calculation Agent")
        else:
            logger.warning("⚠️ Missing essential files - Calculation Agent may not work properly")

    async def check_for_new_data(self) -> bool:
        """Check only essential files for updates"""
        try:
            # Check essential files
            for file_type, file_path in self.essential_files.items():
                if file_path.exists():
                    mod_time = file_path.stat().st_mtime
                    last_mod = self.last_processed.get(file_path.name, 0)
                    
                    if mod_time > last_mod:
                        logger.info(f"📊 New data: {file_path.name}")
                        return True
            
            # Check optional files (no warnings)
            for file_type, file_path in self.optional_files.items():
                if file_path.exists():
                    mod_time = file_path.stat().st_mtime
                    last_mod = self.last_processed.get(file_path.name, 0)
                    
                    if mod_time > last_mod:
                        logger.info(f"📊 New optional data: {file_path.name}")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error checking for new data: {e}")
            return False

    async def process_simulation_data(self) -> Optional[Dict[str, Any]]:
        """Process essential simulation data for Calculation Agent"""
        try:
            processed_data = {
                'timestamp': datetime.now().isoformat(),
                'source': 'ns3_rural_network_simulation',
                'agent_type': 'monitor_agent',
                'target': 'calculation_agent',
                'network_metrics': {},
                'fault_events': [],
                'simulation_config': {},
                'topology_info': {},  # Optional
                'processing_stats': {
                    'files_processed': 0,
                    'essential_files_count': 0
                }
            }
            
            # 1. Process network metrics (ESSENTIAL for LSTM)
            metrics_file = self.essential_files['metrics']
            if metrics_file.exists():
                logger.info("📊 Processing network metrics for LSTM training...")
                processed_data['network_metrics'] = await self.process_network_metrics(metrics_file)
                self.last_processed[metrics_file.name] = metrics_file.stat().st_mtime
                processed_data['processing_stats']['files_processed'] += 1
                processed_data['processing_stats']['essential_files_count'] += 1
            
            # 2. Process fault events (ESSENTIAL for anomaly detection)
            fault_events_file = self.essential_files['fault_events']
            if fault_events_file.exists():
                logger.info("🚨 Processing fault events for anomaly timeline...")
                processed_data['fault_events'] = await self.process_fault_events(fault_events_file)
                self.last_processed[fault_events_file.name] = fault_events_file.stat().st_mtime
                processed_data['processing_stats']['files_processed'] += 1
                processed_data['processing_stats']['essential_files_count'] += 1
            
            # 3. Process simulation config (ESSENTIAL for parameters)
            config_file = self.essential_files['config']
            if config_file.exists():
                logger.info("⚙️ Processing simulation configuration...")
                processed_data['simulation_config'] = await self.process_simulation_config(config_file)
                self.last_processed[config_file.name] = config_file.stat().st_mtime
                processed_data['processing_stats']['files_processed'] += 1
                processed_data['processing_stats']['essential_files_count'] += 1
            
            # 4. Process topology (OPTIONAL)
            topology_file = self.optional_files['topology']
            if topology_file.exists():
                logger.info("🏗️ Processing network topology (optional)...")
                processed_data['topology_info'] = await self.process_topology_info(topology_file)
                self.last_processed[topology_file.name] = topology_file.stat().st_mtime
                processed_data['processing_stats']['files_processed'] += 1
            
            logger.info(f"✅ Processed {processed_data['processing_stats']['essential_files_count']}/3 essential files")
            return processed_data
            
        except Exception as e:
            logger.error(f"❌ Error processing simulation data: {e}")
            return None

    async def process_network_metrics(self, metrics_file: Path) -> Dict[str, Any]:
        """Process network metrics CSV - optimized for LSTM training"""
        try:
            df = pd.read_csv(metrics_file)
            logger.info(f"📊 Loaded {len(df)} rows from metrics CSV")
            
            # Process metrics for LSTM training format
            node_metrics = {}
            
            for _, row in df.iterrows():
                node_id = str(row.get('NodeId', f"node_{len(node_metrics):02d}"))
                if not node_id.startswith('node_'):
                    node_id = f"node_{node_id:0>2}"
                
                # Essential metrics for LSTM anomaly detection
                node_metrics[node_id] = {
                    'timestamp': float(row.get('Time', time.time())),
                    'throughput': float(row.get('Throughput_Mbps', 0)),
                    'latency': float(row.get('Latency_ms', 0)),
                    'packet_loss': float(row.get('PacketLoss_Rate', 0)),
                    'cpu_usage': float(row.get('CPU_Usage', 0)),
                    'memory_usage': float(row.get('Memory_Usage', 0)),
                    'fault_severity': float(row.get('Fault_Severity', 0)),
                    'jitter': float(row.get('Jitter_ms', 0)),
                    'signal_strength': float(row.get('Signal_Strength_dBm', 0)),
                    'error_rate': float(row.get('Error_Rate', 0)),
                    'voltage_level': float(row.get('Voltage_Level_V', 0)),
                    'operational':float(row.get('Operational_Status', 1)),
                    'buffer_occupancy':float(row.get('Buffer_Occupancy', 0)),
                    'degradation_level': float(row.get('Degradation_Level', 0)),
                    'fault_severity': float(row.get('Fault_Severity', 0)),
                    'power_stability': float(row.get('Power_Stability', 1)),    
                }
            
            logger.info(f"📊 Processed {len(node_metrics)} nodes for LSTM training")
            return {
                'node_data': node_metrics,
                'summary': {
                    'total_nodes': len(node_metrics),
                    'data_points': len(df),
                    'lstm_ready': True
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing network metrics: {e}")
            return {}

    async def process_fault_events(self, fault_events_file: Path) -> List[Dict[str, Any]]:
        """Process fault events log"""
        try:
            fault_events = []
            
            with open(fault_events_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith(('#', '=', '---')):
                        # Parse fault events for anomaly correlation
                        if '|' in line:
                            parts = line.split('|')
                            if len(parts) >= 5:
                                fault_events.append({
                                    'timestamp': parts[0].strip(),
                                    'node_id': parts[1].strip(),
                                    'event_type': parts[2].strip(),
                                    'severity': parts[3].strip(),
                                    'description': parts[4].strip()
                                })
            
            logger.info(f"🚨 Processed {len(fault_events)} fault events")
            return fault_events
            
        except Exception as e:
            logger.error(f"❌ Error processing fault events: {e}")
            return []

    async def process_simulation_config(self, config_file: Path) -> Dict[str, Any]:
        """Process simulation configuration"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            logger.info("⚙️ Simulation configuration loaded")
            return config_data
            
        except Exception as e:
            logger.error(f"❌ Error processing simulation config: {e}")
            return {}

    async def process_topology_info(self, topology_file: Path) -> Dict[str, Any]:
        """Process topology JSON (optional)"""
        try:
            with open(topology_file, 'r', encoding='utf-8') as f:
                topology_data = json.load(f)
            
            logger.info("🏗️ Network topology loaded")
            return topology_data
            
        except Exception as e:
            logger.error(f"❌ Error processing topology: {e}")
            return {}

    def validate_data(self, processed_data: Dict[str, Any]) -> bool:
        """Validate essential data for Calculation Agent"""
        try:
            essential_count = processed_data['processing_stats']['essential_files_count']
            
            if essential_count < 3:
                logger.error(f"❌ Only {essential_count}/3 essential files processed")
                return False
            
            # Check LSTM data availability
            if not processed_data['network_metrics'].get('node_data'):
                logger.error("❌ No network metrics data for LSTM training")
                return False
            
            logger.info(f"✅ Data validation passed: {essential_count}/3 essential files")
            return True
            
        except Exception as e:
            logger.error(f"❌ Data validation error: {e}")
            return False

    async def create_calculation_input(self, processed_data: Dict[str, Any]) -> Optional[Path]:
        """Create JSON input for Calculation Agent (LSTM + SHAP)"""
        try:
            calculation_input = {
                'monitor_metadata': {
                    'generated_timestamp': datetime.now().isoformat(),
                    'source_agent': 'monitor_agent',
                    'target_agent': 'calculation_agent',
                    'data_version': '1.0',
                    'essential_files_processed': processed_data['processing_stats']['essential_files_count']
                },
                'lstm_training_data': {
                    'network_metrics': processed_data['network_metrics'],
                    'fault_events': processed_data['fault_events'],
                    'ready_for_training': True
                },
                'simulation_context': {
                    'config': processed_data['simulation_config'],
                    'topology': processed_data['topology_info']
                },
                'anomaly_detection_ready': {
                    'has_metrics': bool(processed_data['network_metrics']),
                    'has_fault_events': bool(processed_data['fault_events']),
                    'node_count': len(processed_data['network_metrics'].get('node_data', {})),
                    'ready': True
                }
            }
            
            # Save calculation input
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = self.output_dir / f"calculation_input_{timestamp}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(calculation_input, f, indent=2, default=str)
            
            file_size = output_file.stat().st_size
            logger.info(f"✅ Calculation input created: {output_file.name}")
            logger.info(f"📁 Size: {self.format_file_size(file_size)}")
            
            return output_file
            
        except Exception as e:
            logger.error(f"❌ Error creating calculation input: {e}")
            return None

    async def notify_calculation_agent(self, processed_data: Dict[str, Any], output_file: Path):
        """Notify calculation agent of new data"""
        try:
            logger.info("📤 Calculation Agent ready to process LSTM + SHAP analysis")
            
        except Exception as e:
            logger.error(f"❌ Error notifying calculation agent: {e}")

    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

# Main execution
async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    monitor = MonitorAgent()
    
    try:
        print('📡 Nokia Build-a-thon: Monitor Agent')
        print('🎯 Essential Files Monitor for Calculation Agent')
        print('📊 Monitoring: Network Metrics + Fault Events + Config')
        print(f'📁 Input Directory: {monitor.faults_dir}')
        print(f'📁 Output Directory: {monitor.output_dir}')
        print('🚀 Starting monitoring...')
        
        await monitor.start_monitoring()
        
    except KeyboardInterrupt:
        logger.info("🛑 Monitor Agent shutdown requested")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")

if __name__ == '__main__':
    asyncio.run(main())