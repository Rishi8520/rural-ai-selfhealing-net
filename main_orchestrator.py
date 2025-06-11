import asyncio
import logging
import json
import os
import zmq.asyncio
from datetime import datetime
import tensorflow as tf
from prometheus_client import start_http_server, Gauge, Counter
import subprocess
import requests
import webbrowser
import psutil

def configure_gpu_for_nokia():
    try:
        # Check for GPU availability
        gpus = tf.config.experimental.list_physical_devices('GPU')
        if gpus:
            print(f"🖥️  Found {len(gpus)} GPU(s): {[gpu.name for gpu in gpus]}")
            
            # 🔧 Configure GPU memory growth to prevent OOM errors
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
                print(f"✅ Memory growth enabled for {gpu.name}")
            
            # 🔧 FIXED: Use correct API for memory limit
            try:
                tf.config.experimental.set_virtual_device_configuration(
                    gpus[0],
                    [tf.config.experimental.VirtualDeviceConfiguration(memory_limit=6144)]
                )
                print(f"🔒 GPU memory limit set to 6GB for stable operation")
            except RuntimeError:
                # Memory limit must be set before GPUs have been initialized
                print("⚠️ GPU already initialized, memory limit not set")
            
            # 🔧 Enable mixed precision for RTX 3050 efficiency (faster training)
            policy = tf.keras.mixed_precision.Policy('mixed_float16')
            tf.keras.mixed_precision.set_global_policy(policy)
            print("🚀 Mixed precision enabled for 2x faster training")
            
            # 🔧 Limit CPU threads to prevent system freeze during GPU operations
            tf.config.threading.set_inter_op_parallelism_threads(4)
            tf.config.threading.set_intra_op_parallelism_threads(4)
            print("🔒 CPU threads limited to prevent system freeze")
            
            # 🔧 Enable XLA compilation for additional speed
            tf.config.optimizer.set_jit(True)
            print("⚡ XLA JIT compilation enabled")
            
            print("✅ RTX 3050 GPU configured successfully for Nokia Build-a-thon!")
            return True
            
        else:
            print("❌ No GPU detected. Check NVIDIA driver installation.")
            print("🔄 Falling back to CPU mode...")
            return False
            
    except Exception as e:
        print(f"❌ GPU configuration failed: {e}")
        print("🔄 Falling back to CPU mode...")
        return False

# 🚀 CONFIGURE GPU BEFORE ANY IMPORTS
gpu_available = configure_gpu_for_nokia()

# EXISTING IMPORTS (keep all your current imports)
from mcp_agent import MCPAgent
from calculation_agent import CalculationAgent
from healing_agent import HealingAgent
from monitor_agent import StreamlinedMonitorAgent

# NEW: Add orchestration agent import
from orchestration_agent import NetworkOrchestrationAgent

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Nokia Build-a-thon ZeroMQ Configuration (UPDATED)
SOCKET_ADDRESSES = {
    # EXISTING ADDRESSES (unchanged)
    'ANOMALY_PUBLISHER': 'tcp://127.0.0.1:5555',
    'METRICS_PUBLISHER': 'tcp://127.0.0.1:5556', 
    'MCP_CALC_PULL': 'tcp://127.0.0.1:5557',
    
    # NEW: Orchestration integration
    'HEALING_TO_ORCHESTRATION': 'tcp://127.0.0.1:5558',  # Healing → Orchestration
    'ORCHESTRATION_RECEIVER': 'tcp://127.0.0.1:5558',    # Orchestration listens here
    
    # Status updates
    'STATUS_PUBLISHER': 'tcp://127.0.0.1:5561'
}

class MainOrchestrator:
    def __init__(self):
        self.context = zmq.asyncio.Context()
        self.agents = {}
        self.is_running = False
        
        # ✅ FIXED: Call setup_central_metrics method
        self.setup_central_metrics()

        start_http_server(8000)  # Central metrics on port 8000
        logger.info("📊 Nokia Build-a-thon Central Prometheus metrics on port 8000")
        
        logger.info("🏆 Nokia Build-a-thon: Rural AI Self-Healing Network Orchestrator")
        logger.info("🔄 Enhanced with TOSCA Orchestration Integration")

    def setup_central_metrics(self):
        """✅ FIXED: Setup central Nokia Build-a-thon metrics with unique naming and error handling"""
        # 🔧 FIX: Use try-catch to avoid duplicate registration
        try:
            self.system_status_gauge = Gauge(
                'nokia_central_system_status',  # 🆕 Changed prefix to avoid conflicts
                'Overall system status (1=healthy, 0=degraded)',
                ['component']
            )
            logger.info("✅ System status gauge created")
        except ValueError as e:
            logger.warning(f"System status gauge already exists: {e}")
            # Metric already exists, get reference to it
            from prometheus_client import REGISTRY
            self.system_status_gauge = None
            for collector in REGISTRY._collector_to_names:
                if hasattr(collector, '_name') and 'nokia_central_system_status' in str(collector._name):
                    self.system_status_gauge = collector
                    break

        try:
            self.agent_status_gauge = Gauge(
                'nokia_central_agent_status',  # 🆕 Changed prefix
                'Agent status (1=running, 0=stopped)',
                ['agent_name', 'agent_type']
            )
            logger.info("✅ Agent status gauge created")
        except ValueError as e:
            logger.warning(f"Agent status gauge already exists: {e}")
            self.agent_status_gauge = None

        try:
            self.gpu_acceleration_gauge = Gauge(
                'nokia_central_gpu_acceleration_active',  # 🆕 Changed prefix
                'GPU acceleration status (1=active, 0=inactive)'
            )
            logger.info("✅ GPU acceleration gauge created")
        except ValueError as e:
            logger.warning(f"GPU acceleration gauge already exists: {e}")
            self.gpu_acceleration_gauge = None

        try:
            self.network_health_gauge = Gauge(
                'nokia_central_network_health_percentage',  # 🆕 Changed prefix
                'Network health percentage',
                ['network_type']
            )
            logger.info("✅ Network health gauge created")
        except ValueError as e:
            logger.warning(f"Network health gauge already exists: {e}")
            self.network_health_gauge = None

        # 🔧 FIX: Use unique names for TOSCA metrics to avoid conflicts with orchestration agent
        try:
            self.tosca_workflows_successful = Counter(
                'nokia_central_tosca_workflows_successful_total',  # 🆕 Changed prefix
                'Number of successful TOSCA workflows',
                ['workflow_type']
            )
            logger.info("✅ TOSCA workflows counter created")
        except ValueError as e:
            logger.warning(f"TOSCA workflows counter already exists: {e}")
            self.tosca_workflows_successful = None

        try:
            self.tosca_workflows_failed = Counter(
                'nokia_central_tosca_workflows_failed_total',  # 🆕 Changed prefix
                'Number of failed TOSCA workflows',
                ['workflow_type', 'error_type']
            )
            logger.info("✅ TOSCA workflows failed counter created")
        except ValueError as e:
            logger.warning(f"TOSCA workflows failed counter already exists: {e}")
            self.tosca_workflows_failed = None

        try:
            self.healing_effectiveness_gauge = Gauge(
                'nokia_central_healing_effectiveness_percentage',  # 🆕 Changed prefix
                'Healing effectiveness percentage',
                ['strategy']
            )
            logger.info("✅ Healing effectiveness gauge created")
        except ValueError as e:
            logger.warning(f"Healing effectiveness gauge already exists: {e}")
            self.healing_effectiveness_gauge = None

        try:
            self.node_status_gauge = Gauge(
                'nokia_central_node_status',  # 🆕 Changed prefix
                'Status of individual nodes',
                ['node_id', 'node_type']
            )
            logger.info("✅ Node status gauge created")
        except ValueError as e:
            logger.warning(f"Node status gauge already exists: {e}")
            self.node_status_gauge = None

        # Additional metrics for Grafana/Prometheus status
        try:
            self.prometheus_status_gauge = Gauge(
                'nokia_central_prometheus_status',
                'Prometheus server status (1=running, 0=stopped)'
            )
            logger.info("✅ Prometheus status gauge created")
        except ValueError as e:
            logger.warning(f"Prometheus status gauge already exists: {e}")
            self.prometheus_status_gauge = None

        try:
            self.grafana_status_gauge = Gauge(
                'nokia_central_grafana_status',
                'Grafana server status (1=running, 0=stopped)'
            )
            logger.info("✅ Grafana status gauge created")
        except ValueError as e:
            logger.warning(f"Grafana status gauge already exists: {e}")
            self.grafana_status_gauge = None

        logger.info("✅ Central metrics setup completed (with duplicate protection)")

    async def initialize_agents(self):
        """Initialize all agents with Nokia Build-a-thon configuration + TOSCA orchestration"""
        try:
            # 1. Monitor Agent - detects anomalies from NS3 data (UNCHANGED)
            monitor_config_file = "streamlined_monitor_config.json"
            self.agents['monitor'] = StreamlinedMonitorAgent(monitor_config_file)
            logger.info("✅ Monitor Agent initialized")
            
            # 2. Calculation Agent - analyzes anomalies and triggers healing (UNCHANGED)
            node_ids = [f"node_{i:02d}" for i in range(50)]
            self.agents['calculation'] = CalculationAgent(
                node_ids=node_ids,
                pub_socket_address_a2a=SOCKET_ADDRESSES['METRICS_PUBLISHER'],
                push_socket_address_mcp=SOCKET_ADDRESSES['MCP_CALC_PULL'],
            )
            logger.info("✅ Calculation Agent initialized")
            
            # 3. Healing Agent - generates AI healing plans (UPDATED - now sends to orchestration)
            config = {
                'rag_database_path': 'rural_network_knowledge_base.db',
                'ns3_database_path': 'data/ns3_simulation/database/'
            }
            self.agents['healing'] = HealingAgent(
                context=self.context,
                sub_socket_address_a2a=SOCKET_ADDRESSES['METRICS_PUBLISHER'],  # Listens to calculation
                push_socket_address_mcp=SOCKET_ADDRESSES['HEALING_TO_ORCHESTRATION'],  # NOW: Sends to orchestration
            )
            logger.info("✅ Healing Agent initialized with real NS3 data + Orchestration integration")
            
            # 4. MCP Agent - central message processing (UNCHANGED)
            self.agents['mcp'] = MCPAgent(
                context=self.context,
                calc_agent_pull_address=SOCKET_ADDRESSES['MCP_CALC_PULL'],
                healing_agent_pull_address="tcp://127.0.0.1:5999"  # Not used in new flow
            )
            logger.info("✅ MCP Agent initialized")
            
            # 5. 🆕 NEW: TOSCA Orchestration Agent - executes infrastructure workflows
            self.agents['orchestration'] = NetworkOrchestrationAgent()
            logger.info("✅ 🚀 TOSCA Orchestration Agent initialized with xOpera integration")
            
            logger.info("🎉 All 5 Nokia Build-a-thon agents initialized successfully!")
            logger.info("📊 Flow: Monitor → Calculation → Healing → 🆕 TOSCA Orchestration → Infrastructure")
            
        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}")
            raise

    async def start_complete_system(self):
        """Complete Nokia Build-a-thon system startup integrated in main orchestrator"""
        try:
            logger.info("🏆 Starting Complete Nokia Build-a-thon System")
            logger.info("=" * 60)
            
            # 1. Start Prometheus
            logger.info("📊 Starting Prometheus...")
            try:
                # Check if Prometheus is already running
                prometheus_running = any("prometheus" in p.name().lower() for p in psutil.process_iter())
                
                if not prometheus_running:
                    prometheus_process = subprocess.Popen([
                        "prometheus", 
                        "--config.file=prometheus.yml",
                        "--storage.tsdb.path=prometheus_data/"
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    await asyncio.sleep(3)
                    logger.info("✅ Prometheus started successfully")
                else:
                    logger.info("✅ Prometheus is already running")
                
                if self.prometheus_status_gauge:
                    self.prometheus_status_gauge.set(1.0)
                    
            except Exception as e:
                logger.warning(f"Could not start Prometheus automatically: {e}")
                logger.info("🔧 Please start manually: prometheus --config.file=prometheus.yml")
                if self.prometheus_status_gauge:
                    self.prometheus_status_gauge.set(0.0)
            
            # 2. Start Grafana
            logger.info("📈 Starting Grafana...")
            try:
                subprocess.run(["sudo", "systemctl", "start", "grafana-server"], 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                await asyncio.sleep(5)
                logger.info("✅ Grafana started successfully")
                if self.grafana_status_gauge:
                    self.grafana_status_gauge.set(1.0)
            except Exception as e:
                logger.warning(f"Could not start Grafana automatically: {e}")
                logger.info("🔧 Please start manually: sudo systemctl start grafana-server")
                if self.grafana_status_gauge:
                    self.grafana_status_gauge.set(0.0)
            
            # 3. Setup Grafana dashboard
            logger.info("🔧 Setting up Nokia Build-a-thon dashboard...")
            try:
                # Wait for Grafana to be ready
                if await self.wait_for_grafana():
                    await self.configure_grafana_datasources()
                    dashboard_url = await self.create_nokia_dashboard()
                    if dashboard_url:
                        logger.info(f"✅ Nokia dashboard created: {dashboard_url}")
                    else:
                        logger.warning("❌ Failed to create Nokia dashboard")
                else:
                    logger.warning("❌ Grafana not ready, skipping dashboard setup")
                        
            except Exception as e:
                logger.warning(f"Could not setup Grafana dashboard: {e}")
                logger.info("🔧 Manual setup: Go to http://localhost:3000")
            
            # 4. Start all your agents (your existing code)
            logger.info("🚀 Starting Nokia Build-a-thon agents...")
            await self.start_all_agents()
            
            # 5. Display access URLs
            logger.info("\n🌐 Nokia Build-a-thon System URLs:")
            logger.info("   📊 Grafana Dashboard: http://localhost:3000")
            logger.info("   🔍 Prometheus: http://localhost:9090") 
            logger.info("   📈 Nokia Metrics: http://localhost:8000/metrics")
            logger.info("   🤖 Agent Status: Check individual agent logs")
            
        except Exception as e:
            logger.error(f"❌ Error in complete system startup: {e}")
            raise

    async def wait_for_grafana(self, timeout=30):
        """Wait for Grafana to be ready"""
        logger.info("🕐 Waiting for Grafana to start...")
        for i in range(timeout):
            try:
                response = requests.get("http://localhost:3000/api/health", timeout=2)
                if response.status_code == 200:
                    logger.info("✅ Grafana is ready!")
                    return True
            except:
                await asyncio.sleep(1)
        
        logger.warning("⏰ Grafana startup timeout")
        return False

    async def configure_grafana_datasources(self):
        """Configure Prometheus datasource in Grafana"""
        try:
            auth = ('admin', 'admin')
            headers = {'Content-Type': 'application/json'}
            
            datasource_config = {
                "name": "Nokia-Prometheus",
                "type": "prometheus", 
                "url": "http://localhost:9090",
                "access": "proxy",
                "isDefault": True
            }
            
            response = requests.post(
                "http://localhost:3000/api/datasources",
                auth=auth,
                headers=headers,
                json=datasource_config
            )
            
            if response.status_code in [200, 409]:  # 409 = already exists
                logger.info("✅ Prometheus datasource configured")
                return True
            else:
                logger.warning(f"❌ Failed to setup datasource: {response.text}")
                return False
                
        except Exception as e:
            logger.warning(f"Failed to configure datasources: {e}")
            return False

    async def create_nokia_dashboard(self):
        """Create Nokia Build-a-thon dashboard"""
        try:
            auth = ('admin', 'admin')
            headers = {'Content-Type': 'application/json'}
            
            dashboard = {
                "dashboard": {
                    "id": None,
                    "title": "Nokia Build-a-thon: AI Self-Healing Network with TOSCA",
                    "tags": ["nokia", "build-a-thon", "ai", "tosca", "healing"],
                    "timezone": "browser",
                    "panels": [
                        # System Status Overview
                        {
                            "id": 1,
                            "title": "🏆 Nokia Build-a-thon System Status",
                            "type": "stat",
                            "gridPos": {"h": 4, "w": 24, "x": 0, "y": 0},
                            "targets": [{
                                "expr": "nokia_central_system_status",
                                "legendFormat": "{{component}}"
                            }],
                            "options": {
                                "colorMode": "background",
                                "graphMode": "area"
                            }
                        },
                        # Agent Status
                        {
                            "id": 2,
                            "title": "🤖 Multi-Agent System Status",
                            "type": "stat",
                            "gridPos": {"h": 6, "w": 8, "x": 0, "y": 4},
                            "targets": [{
                                "expr": "nokia_central_agent_status",
                                "legendFormat": "{{agent_name}}"
                            }]
                        },
                        # Network Health
                        {
                            "id": 3,
                            "title": "🌐 Network Health",
                            "type": "gauge",
                            "gridPos": {"h": 6, "w": 8, "x": 8, "y": 4},
                            "targets": [{
                                "expr": "nokia_central_network_health_percentage",
                                "legendFormat": "Health %"
                            }],
                            "fieldConfig": {
                                "defaults": {
                                    "min": 0,
                                    "max": 100,
                                    "thresholds": {
                                        "steps": [
                                            {"color": "red", "value": 0},
                                            {"color": "yellow", "value": 70},
                                            {"color": "green", "value": 90}
                                        ]
                                    }
                                }
                            }
                        },
                        # GPU Status
                        {
                            "id": 4,
                            "title": "🚀 GPU Acceleration",
                            "type": "stat",
                            "gridPos": {"h": 6, "w": 8, "x": 16, "y": 4},
                            "targets": [{
                                "expr": "nokia_central_gpu_acceleration_active",
                                "legendFormat": "RTX 3050 Active"
                            }]
                        }
                    ],
                    "time": {"from": "now-1h", "to": "now"},
                    "refresh": "10s"
                },
                "overwrite": True
            }
            
            response = requests.post(
                "http://localhost:3000/api/dashboards/db",
                auth=auth,
                headers=headers,
                json=dashboard
            )
            
            if response.status_code == 200:
                result = response.json()
                dashboard_url = f"http://localhost:3000/d/{result.get('uid', '')}"
                logger.info(f"✅ Nokia dashboard created: {dashboard_url}")
                return dashboard_url
            else:
                logger.warning(f"❌ Failed to create dashboard: {response.text}")
                return None
                
        except Exception as e:
            logger.warning(f"Failed to create dashboard: {e}")
            return None

    async def start_all_agents(self):
        """Start all agents including TOSCA orchestration"""
        try:
            self.is_running = True
            
            # Create configuration files if needed
            await self._create_config_files()
            
            logger.info("🚀 Starting Nokia Build-a-thon AI Self-Healing Network...")
            logger.info("🆕 WITH TOSCA ORCHESTRATION INTEGRATION")
            logger.info("=" * 60)
            
            # Start agents in background tasks
            tasks = []
            
            # Start MCP Agent (message processing) - UNCHANGED
            tasks.append(asyncio.create_task(
                self.agents['mcp'].start(), 
                name="mcp_agent"
            ))
            
            # 🆕 NEW: Start TOSCA Orchestration Agent
            tasks.append(asyncio.create_task(
                self.agents['orchestration'].start(), 
                name="tosca_orchestration_agent"
            ))
            
            # Start Healing Agent (AI healing plans) - UNCHANGED
            tasks.append(asyncio.create_task(
                self.agents['healing'].start(), 
                name="healing_agent"
            ))
            
            logger.info("🤖 Background agents started (including TOSCA orchestration)...")
            
            # Update metrics
            if self.gpu_acceleration_gauge:
                self.gpu_acceleration_gauge.set(1.0)  # GPU is active
            
            for agent_name in ['monitor', 'calculation', 'healing', 'mcp', 'orchestration']:
                if self.agent_status_gauge:
                    self.agent_status_gauge.labels(
                        agent_name=agent_name,
                        agent_type='nokia_builathon'
                    ).set(1.0)
            
            if self.system_status_gauge:
                self.system_status_gauge.labels(component='overall').set(1.0)
            
            # Train Calculation Agent (blocking) - UNCHANGED
            logger.info("🧠 Training Calculation Agent ML models...")
            await self.agents['calculation'].start()
            logger.info("✅ Calculation Agent training completed")
            
            # Start Monitor Agent (data streaming) - UNCHANGED
            tasks.append(asyncio.create_task(
                self.agents['monitor'].start_streamlined_monitoring(), 
                name="monitor_agent"
            ))
            
            logger.info("📊 Monitor Agent streaming NS3 data...")
            logger.info("=" * 60)
            logger.info("🎭 Nokia Build-a-thon System: FULLY OPERATIONAL WITH TOSCA!")
            logger.info("🔄 Complete Flow: Monitor → Calculation → Healing → 🆕 TOSCA → Infrastructure")
            logger.info("🏆 Enterprise-Grade AI Self-Healing with xOpera Orchestration")
            logger.info("=" * 60)
            
            # Keep system running
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except KeyboardInterrupt:
            logger.info("\n🛑 Nokia Build-a-thon system stopped by user")
        except Exception as e:
            logger.error(f"Error in Nokia Build-a-thon system: {e}")
        finally:
            await self.cleanup()

    async def _create_config_files(self):
        """Create necessary configuration files for Nokia Build-a-thon (UPDATED with GPU settings)"""
        # Create calculation config with GPU optimizations
        calc_config = {
            "lstm_sequence_length": 10,
            "lstm_epochs": 15,  # Reduced for faster GPU training
            "anomaly_threshold_percentile": 99,
            "alert_debounce_interval": 10,
            "model_training_batch_size": 128,  # Larger batch for GPU efficiency
            "train_on_startup": True,
            "training_data_limit": 8000,
            
            # 🆕 GPU-specific settings
            "use_gpu": True,
            "gpu_memory_limit": 6144,  # MB
            "mixed_precision": True,
            "cpu_thread_limit": 4,
            "enable_xla": True,
            
            "lstm_features": [
                'throughput', 'latency', 'packet_loss', 'jitter',
                'signal_strength', 'cpu_usage', 'memory_usage', 'buffer_occupancy',
                'active_links', 'neighbor_count', 'link_utilization', 'critical_load',
                'normal_load', 'energy_level', 'x_position', 'y_position', 'z_position',
                'degradation_level', 'fault_severity', 'power_stability', 'voltage_level'
            ],
            "prediction_horizon": 1,
            "training_data_file": "baseline_network_metrics.csv",
            "testing_data_file": "rural_network_metrics.csv",
            "monitor_ns3_metrics_file": "calculation_agent_data_stream.json"
        }
        
        if not os.path.exists("calculation_config.json"):
            with open("calculation_config.json", 'w') as f:
                json.dump(calc_config, f, indent=2)
            logger.info("📝 Created calculation_config.json with GPU configuration")

        # Create monitor config (UNCHANGED)
        monitor_config = {
            "node_ids": [f"node_{i:02d}" for i in range(50)],
            "data_interval_seconds": 1,
            "output_file": "calculation_agent_data_stream.json",
            "metrics_mapping": {
                "packet_received": "throughput",
                "latency_avg": "latency",
                "packet_loss_rate": "packet_loss",
                "device_cpu_usage": "cpu_usage",
                "device_memory_usage": "memory_usage",
                "device_energy_level": "energy_level",
                "node_operational": "operational",
                "degradation_severity": "degradation_level",
                "fault_severity_level": "fault_severity",
                "power_stability_index": "power_stability",
                "voltage_level": "voltage_level",
                "node_type": "node_type",
                "pos_x": "position_x",
                "pos_y": "position_y"
            },
            "health_parameters": {
                "throughput_min": 1000.0,
                "latency_max": 50.0,
                "packet_loss_max": 0.01,
                "cpu_usage_max": 80.0,
                "memory_usage_max": 90.0,
                "energy_critical": 0.1,
                "degradation_threshold": 0.7,
                "fault_threshold": 0.5,
                "power_stability_min": 0.9,
                "voltage_min": 200.0,
                "voltage_max": 240.0,
                "operational_threshold": 0.9
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
        
        if not os.path.exists("streamlined_monitor_config.json"):
            with open("streamlined_monitor_config.json", 'w') as f:
                json.dump(monitor_config, f, indent=2)
            logger.info("📝 Created streamlined_monitor_config.json")

        # 🆕 NEW: Create TOSCA orchestration config
        tosca_config = {
            "xopera_path": "opera",  # Path to opera executable
            "templates_directory": "tosca_templates/",
            "deployment_timeout_seconds": 300,
            "default_priority": "medium",
            "logging": {
                "level": "INFO",
                "tosca_execution_logs": "tosca_executions.log"
            },
            "healing_strategy_mappings": {
                "reroute_traffic": "traffic_rerouting.yaml",
                "restart_device": "device_restart.yaml",
                "escalate_human": "human_escalation.yaml",
                "apply_policy": "policy_application.yaml",
                "backup_power_switch": "backup_power.yaml"
            }
        }
        
        if not os.path.exists("tosca_orchestration_config.json"):
            with open("tosca_orchestration_config.json", 'w') as f:
                json.dump(tosca_config, f, indent=2)
            logger.info("📝 🆕 Created tosca_orchestration_config.json")

        # Create Prometheus config
        prometheus_config = {
            "global": {
                "scrape_interval": "15s"
            },
            "scrape_configs": [
                {
                    "job_name": "nokia-central",
                    "static_configs": [{"targets": ["localhost:8000"]}],
                    "scrape_interval": "10s"
                },
                {
                    "job_name": "nokia-monitor",
                    "static_configs": [{"targets": ["localhost:8001"]}],
                    "scrape_interval": "5s"
                },
                {
                    "job_name": "nokia-calculation",
                    "static_configs": [{"targets": ["localhost:8002"]}],
                    "scrape_interval": "10s"
                },
                {
                    "job_name": "nokia-orchestration",
                    "static_configs": [{"targets": ["localhost:8003"]}],
                    "scrape_interval": "10s"
                },
                {
                    "job_name": "prometheus",
                    "static_configs": [{"targets": ["localhost:9090"]}]
                }
            ]
        }
        
        if not os.path.exists("prometheus.yml"):
            import yaml
            try:
                with open("prometheus.yml", 'w') as f:
                    yaml.dump(prometheus_config, f, default_flow_style=False)
                logger.info("📝 Created prometheus.yml")
            except ImportError:
                # Fallback if yaml module not available
                logger.warning("PyYAML not available, creating basic prometheus.yml")
                with open("prometheus.yml", 'w') as f:
                    f.write("global:\n  scrape_interval: 15s\n")
                    f.write("scrape_configs:\n")
                    f.write("  - job_name: nokia-central\n")
                    f.write("    static_configs:\n")
                    f.write("      - targets: ['localhost:8000']\n")
    
    async def cleanup(self):
        """Clean up all agents and resources (ENHANCED)"""
        logger.info("🧹 Cleaning up Nokia Build-a-thon system...")
        
        self.is_running = False
        
        for agent_name, agent in self.agents.items():
            try:
                if hasattr(agent, 'close'):
                    await agent.close()
                elif hasattr(agent, 'db_manager') and hasattr(agent.db_manager, 'close'):
                    agent.db_manager.close()
                logger.info(f"✅ Cleaned up {agent_name}")
            except Exception as e:
                logger.error(f"Error cleaning up {agent_name}: {e}")
        
        self.context.term()
        logger.info("🎉 Nokia Build-a-thon system cleanup complete (with TOSCA)")

async def main():
    """Nokia Build-a-thon Main Entry Point - Enhanced with TOSCA and Grafana"""
    print("🏆" + "=" * 60 + "🏆")
    print("🚀 NOKIA BUILD-A-THON: RURAL AI SELF-HEALING NETWORK")
    print("🤖 AI-Powered Network Healing with Google Gemini")
    print("🎭 🆕 TOSCA Orchestration with xOpera Integration")
    print("📊 📈 GRAFANA DASHBOARD WITH REAL-TIME MONITORING")
    print("📊 Real NS3 Simulation Data Processing")
    print("🌐 Rural Broadband Infrastructure Focus")
    print("🔄 Complete Flow: AI → TOSCA → Infrastructure Automation")
    print("🏆" + "=" * 60 + "🏆")
    
    try:
        # Initialize orchestrator first
        orchestrator = MainOrchestrator()
        
        # Initialize agents
        await orchestrator.initialize_agents()
        
        # 🆕 Start complete system (includes Prometheus, Grafana, and all agents)
        await orchestrator.start_complete_system()
        
    except KeyboardInterrupt:
        logger.info("🛑 Nokia Build-a-thon system stopped by user")
    except Exception as e:
        logger.error(f"❌ Nokia Build-a-thon system failed: {e}")
        logger.error(f"❌ Error details: {type(e).__name__}: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())