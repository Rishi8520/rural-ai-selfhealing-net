# ns3_network_interface.py (UPDATED FOR REAL NS-3 DATA)
import pandas as pd
import os
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class NS3NetworkInterface:
    """Interface to read real NS-3 simulation data from CSV files"""
    
    def __init__(self, config: Dict[str, Any]):
        # File paths
        self.metrics_file = config.get('metrics_file', 'rural_network_metrics.csv')
        self.topology_file = config.get('topology_file', 'network_topology.json')
        
        # Data tracking
        self.current_time_index = 0
        self.simulation_data = None
        self.topology_info = {}
        self.available_times = []
        
        logger.info("NS-3 Network Interface initialized for real data")

    async def initialize_simulation(self):
        """Load and prepare NS-3 simulation data"""
        logger.info("Loading NS-3 simulation data...")
        
        try:
            # Load CSV data
            if not os.path.exists(self.metrics_file):
                raise FileNotFoundError(f"Metrics file not found: {self.metrics_file}")
            
            self.simulation_data = pd.read_csv(self.metrics_file)
            self.available_times = sorted(self.simulation_data['Time'].unique())
            
            logger.info(f"Loaded {len(self.simulation_data)} data points")
            logger.info(f"Simulation time range: {self.available_times[0]:.0f}s to {self.available_times[-1]:.0f}s")
            logger.info(f"Total nodes: {self.simulation_data['NodeId'].nunique()}")
            
            # Load topology
            if os.path.exists(self.topology_file):
                with open(self.topology_file, 'r') as f:
                    self.topology_info = json.load(f)
                logger.info("Topology information loaded")
            
            logger.info("NS-3 simulation data ready for monitoring")
            
        except Exception as e:
            logger.error(f"Failed to load NS-3 data: {e}")
            raise

    async def get_all_node_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get current network metrics (simulates real-time reading)"""
        if self.simulation_data is None:
            logger.warning("No simulation data loaded")
            return {}
        
        # Get current time slice
        if self.current_time_index >= len(self.available_times):
            logger.info("End of simulation data reached")
            return {}
        
        current_time = self.available_times[self.current_time_index]
        current_data = self.simulation_data[self.simulation_data['Time'] == current_time]
        
        logger.info(f"Reading metrics at time {current_time:.0f}s ({self.current_time_index + 1}/{len(self.available_times)})")
        
        # Convert to metrics format
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
                'voltage_level': float(row['Voltage_Level']) if row['Voltage_Level'] > 0 else 220.0,
                'power_stability': float(row['Power_Stability']) if row['Power_Stability'] > 0 else 0.95,
                'node_type': str(row['NodeType']),
                'position_x': float(row['X_Position']),
                'position_y': float(row['Y_Position']),
                'current_time': current_time
            }
        
        # Move to next time slice for next call
        self.current_time_index += 1
        
        return metrics

    def get_simulation_progress(self) -> Dict[str, Any]:
        """Get simulation progress information"""
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

    def reset_simulation(self):
        """Reset to beginning of simulation"""
        self.current_time_index = 0
        logger.info("Simulation reset to beginning")

    def jump_to_time(self, target_time: float):
        """Jump to specific simulation time"""
        closest_index = min(range(len(self.available_times)), 
                           key=lambda i: abs(self.available_times[i] - target_time))
        self.current_time_index = closest_index
        logger.info(f"Jumped to time {self.available_times[closest_index]:.0f}s")

    def get_node_time_series(self, node_id: str) -> pd.DataFrame:
        """Get complete time series for a specific node"""
        if self.simulation_data is None:
            return pd.DataFrame()
        
        node_num = int(node_id.split('_')[1])
        node_data = self.simulation_data[self.simulation_data['NodeId'] == node_num]
        return node_data.sort_values('Time')

    def get_network_topology(self) -> Dict[str, Any]:
        """Get network topology information"""
        return self.topology_info

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("NS-3 interface cleanup completed")