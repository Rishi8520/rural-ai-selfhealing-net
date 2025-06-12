import asyncio
import logging
import json
import time
import psutil
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedMainOrchestrator:
    """System-wide orchestrator for independent agent management"""
    
    def __init__(self):
        self.agent_processes = {}
        self.agent_health = {}
        self.system_metrics = {}
        self.dashboard_port = 8000
        
        # Agent configurations
        self.agents_config = {
            'calculation_agent': {
                'script': 'enhanced_calculation_agent.py',
                'health_endpoint': 'http://localhost:8002/health',
                'metrics_endpoint': 'http://localhost:8002/metrics',
                'expected_files': ['shap_plots_enhanced/'],
                'critical': True
            },
            'healing_agent': {
                'script': 'enhanced_healing_agent.py', 
                'health_endpoint': 'http://localhost:8004/health',
                'metrics_endpoint': 'http://localhost:8004/metrics',
                'expected_files': ['healing_plans/', 'healing_reports/'],
                'critical': True
            },
            'orchestration_agent': {
                'script': 'enhanced_orchestration_agent.py',
                'health_endpoint': 'http://localhost:8001/health', 
                'metrics_endpoint': 'http://localhost:8001/metrics',
                'expected_files': ['tosca_templates/', 'healing_plans_for_ns3/'],
                'critical': True
            }
        }
    
    async def coordinate_independent_agents(self):
        """Main coordination loop for independent agents"""
        logger.info("🎯 Nokia Main Orchestrator: System-wide monitoring started")
        
        # Start system dashboard
        asyncio.create_task(self.start_system_dashboard())
        
        while True:
            try:
                # Monitor agent health
                await self.monitor_agent_health()
                
                # Aggregate system metrics
                await self.aggregate_system_metrics()
                
                # Check for agent failures and restart if needed
                await self.handle_agent_failures()
                
                # Generate system report
                await self.generate_system_report()
                
                # Wait before next check
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"❌ Main orchestrator error: {e}")
                await asyncio.sleep(5)
    
    async def monitor_agent_health(self):
        """Monitor health of all independent agents"""
        for agent_name, config in self.agents_config.items():
            try:
                # Check if agent process exists and is responsive
                health_status = await self.check_agent_health(agent_name, config)
                self.agent_health[agent_name] = health_status
                
                if not health_status['healthy'] and config['critical']:
                    logger.warning(f"⚠️ Critical agent {agent_name} is unhealthy")
                    await self.restart_failed_agent(agent_name, config)
                    
            except Exception as e:
                logger.error(f"❌ Health check failed for {agent_name}: {e}")
                self.agent_health[agent_name] = {'healthy': False, 'error': str(e)}
    
    async def check_agent_health(self, agent_name: str, config: Dict) -> Dict[str, Any]:
        """Check individual agent health"""
        try:
            # Try to reach health endpoint (if implemented)
            try:
                response = requests.get(config['health_endpoint'], timeout=5)
                if response.status_code == 200:
                    return {'healthy': True, 'response_time': response.elapsed.total_seconds()}
            except requests.RequestException:
                pass
            
            # Check if expected files/directories exist
            all_files_exist = True
            for expected_file in config['expected_files']:
                if not Path(expected_file).exists():
                    all_files_exist = False
                    break
            
            # Check system processes (basic check)
            agent_running = False
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if config['script'] in cmdline:
                        agent_running = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                'healthy': all_files_exist and agent_running,
                'files_exist': all_files_exist,
                'process_running': agent_running,
                'last_check': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
    
    async def aggregate_system_metrics(self):
        """Aggregate metrics from all agents"""
        system_summary = {
            'timestamp': datetime.now().isoformat(),
            'total_anomalies_detected': 0,
            'total_healing_plans_generated': 0,
            'total_tosca_templates_created': 0,
            'system_health_percentage': 0.0,
            'active_agents': 0,
            'agent_details': {}
        }
        
        healthy_agents = 0
        total_agents = len(self.agents_config)
        
        for agent_name, config in self.agents_config.items():
            agent_health = self.agent_health.get(agent_name, {'healthy': False})
            
            if agent_health['healthy']:
                healthy_agents += 1
                
                # Try to fetch metrics from agent
                try:
                    metrics = await self.fetch_agent_metrics(config['metrics_endpoint'])
                    system_summary['agent_details'][agent_name] = metrics
                    
                    # Aggregate specific metrics
                    if agent_name == 'calculation_agent':
                        system_summary['total_anomalies_detected'] += metrics.get('anomalies_sent', 0)
                    elif agent_name == 'healing_agent':
                        system_summary['total_healing_plans_generated'] += metrics.get('healing_plans_generated', 0)
                    elif agent_name == 'orchestration_agent':
                        system_summary['total_tosca_templates_created'] += metrics.get('tosca_templates_generated', 0)
                        
                except Exception as e:
                    logger.warning(f"⚠️ Could not fetch metrics from {agent_name}: {e}")
                    system_summary['agent_details'][agent_name] = {'error': str(e)}
            else:
                system_summary['agent_details'][agent_name] = {'status': 'unhealthy'}
        
        system_summary['system_health_percentage'] = (healthy_agents / total_agents) * 100
        system_summary['active_agents'] = healthy_agents
        
        self.system_metrics = system_summary
    
    async def fetch_agent_metrics(self, metrics_endpoint: str) -> Dict[str, Any]:
        """Fetch metrics from agent endpoint"""
        try:
            response = requests.get(metrics_endpoint, timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return {'error': f'HTTP {response.status_code}'}
        except requests.RequestException as e:
            return {'error': str(e)}
    
    async def generate_system_report(self):
        """Generate comprehensive system report"""
        try:
            report_dir = Path("system_reports")
            report_dir.mkdir(exist_ok=True)
            
            report = {
                'report_timestamp': datetime.now().isoformat(),
                'system_metrics': self.system_metrics,
                'agent_health': self.agent_health,
                'file_system_status': await self.check_file_system_status()
            }
            
            # Save report
            report_file = report_dir / f"system_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            # Log summary
            logger.info(f"📊 System Health: {self.system_metrics.get('system_health_percentage', 0):.1f}%")
            logger.info(f"🔄 Active Agents: {self.system_metrics.get('active_agents', 0)}/{len(self.agents_config)}")
            logger.info(f"📋 Report saved: {report_file}")
            
        except Exception as e:
            logger.error(f"❌ Error generating system report: {e}")
    
    async def check_file_system_status(self) -> Dict[str, Any]:
        """Check status of expected files and directories"""
        file_status = {}
        
        expected_directories = [
            'shap_plots_enhanced',
            'healing_plans', 
            'healing_reports',
            'tosca_templates',
            'healing_plans_for_ns3',
            'system_reports'
        ]
        
        for directory in expected_directories:
            dir_path = Path(directory)
            if dir_path.exists():
                file_count = len(list(dir_path.glob('*')))
                file_status[directory] = {
                    'exists': True,
                    'file_count': file_count,
                    'last_modified': dir_path.stat().st_mtime
                }
            else:
                file_status[directory] = {'exists': False}
        
        return file_status
    
    async def start_system_dashboard(self):
        """Start simple HTTP dashboard for system monitoring"""
        try:
            from aiohttp import web, web_runner
            
            async def dashboard_handler(request):
                html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Nokia Rural Network - System Dashboard</title>
                    <meta http-equiv="refresh" content="30">
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; }}
                        .healthy {{ color: green; }}
                        .unhealthy {{ color: red; }}
                        .metric {{ margin: 10px 0; }}
                        .agent-status {{ border: 1px solid #ccc; padding: 10px; margin: 10px 0; }}
                    </style>
                </head>
                <body>
                    <h1>Nokia Rural Network - System Dashboard</h1>
                    <p>Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    
                    <h2>System Health: {self.system_metrics.get('system_health_percentage', 0):.1f}%</h2>
                    
                    <h3>Agent Status:</h3>
                    {''.join([
                        f'''<div class="agent-status">
                            <h4>{agent_name}</h4>
                            <p class="{'healthy' if health.get('healthy', False) else 'unhealthy'}">
                                Status: {'Healthy' if health.get('healthy', False) else 'Unhealthy'}
                            </p>
                        </div>'''
                        for agent_name, health in self.agent_health.items()
                    ])}
                    
                    <h3>System Metrics:</h3>
                    <div class="metric">Total Anomalies Detected: {self.system_metrics.get('total_anomalies_detected', 0)}</div>
                    <div class="metric">Total Healing Plans Generated: {self.system_metrics.get('total_healing_plans_generated', 0)}</div>
                    <div class="metric">Total TOSCA Templates Created: {self.system_metrics.get('total_tosca_templates_created', 0)}</div>
                    <div class="metric">Active Agents: {self.system_metrics.get('active_agents', 0)}/{len(self.agents_config)}</div>
                </body>
                </html>
                """
                return web.Response(text=html, content_type='text/html')
            
            app = web.Application()
            app.router.add_get('/', dashboard_handler)
            app.router.add_get('/dashboard', dashboard_handler)
            
            runner = web_runner.AppRunner(app)
            await runner.setup()
            site = web_runner.TCPSite(runner, 'localhost', self.dashboard_port)
            await site.start()
            
            logger.info(f"📊 System dashboard started: http://localhost:{self.dashboard_port}/dashboard")
            
        except Exception as e:
            logger.error(f"❌ Failed to start dashboard: {e}")

# Main execution
async def main():
    """Main execution function for Enhanced Main Orchestrator"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    orchestrator = EnhancedMainOrchestrator()
    
    try:
        print('🎯 Nokia Enhanced Main Orchestrator starting...')
        print('📊 System-wide monitoring and coordination')
        print(f'🌐 Dashboard: http://localhost:{orchestrator.dashboard_port}/dashboard')
        print('🔄 Monitoring independent agents...')
        
        await orchestrator.coordinate_independent_agents()
        
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown requested")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")

if __name__ == '__main__':
    asyncio.run(main())