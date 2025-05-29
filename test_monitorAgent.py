# test_monitor_agent.py
import asyncio
import logging
from monitor_agent import RuralNetworkMonitorAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_monitor_agent():
    """Test the monitor agent with real NS-3 data"""
    
    logger.info("🔍 TESTING MONITOR AGENT WITH REAL NS-3 DATA")
    logger.info("=" * 60)
    
    # Create monitor agent
    monitor = RuralNetworkMonitorAgent("monitor_config.json")
    
    try:
        # Start monitoring
        await monitor.start_monitoring()
        
        print("\n" + "=" * 60)
        print("MONITOR AGENT TEST COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("Check the following files:")
        print("- fault_detection_report.json (detailed report)")
        print("- Console output above (real-time monitoring)")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_monitor_agent())