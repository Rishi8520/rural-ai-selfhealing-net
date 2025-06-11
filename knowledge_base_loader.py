# knowledge_base_loader.py
import sqlite3
import pandas as pd
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class KnowledgeBaseLoader:
    def __init__(self, database_path="data/ns3_simulation/database/"):
        self.database_path = Path(database_path)
        self.db_file = "rural_network_knowledge_base.db"
        
    def load_ns3_database(self):
        """Load all NS3 generated SQL files into SQLite database"""
        logger.info("Loading NS3 database files into knowledge base...")
        
        # Create SQLite database
        conn = sqlite3.connect(self.db_file)
        
        # Execute schema first
        schema_file = self.database_path / "fault_demo_database_schema.sql"
        if schema_file.exists():
            with open(schema_file, 'r') as f:
                schema_sql = f.read()
                conn.executescript(schema_sql)
            logger.info("Database schema loaded")
        
        # Load all data files
        data_files = [
            "fault_demo_database_nodes.sql",
            "fault_demo_database_links.sql", 
            "fault_demo_database_anomalies.sql",
            "fault_demo_database_recovery_tactics.sql",
            "fault_demo_database_policies.sql",
            "fault_demo_database_traffic_flows.sql"
        ]
        
        for file_name in data_files:
            file_path = self.database_path / file_name
            if file_path.exists():
                with open(file_path, 'r') as f:
                    data_sql = f.read()
                    conn.executescript(data_sql)
                logger.info(f"Loaded {file_name}")
        
        conn.commit()
        conn.close()
        logger.info("Knowledge base database ready")
        
if __name__ == "__main__":
    loader = KnowledgeBaseLoader()
    loader.load_ns3_database()
import sqlite3
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

class KnowledgeBaseLoader:
    def __init__(self, database_path="data/ns3_simulation/database/"):
        self.database_path = Path(database_path)
        self.db_file = "rural_network_knowledge_base.db"
        
    def load_ns3_database(self):
        """Load all NS3 generated SQL files into SQLite database"""
        logger.info("🏆 Nokia Build-a-thon: Loading NS3 database files into knowledge base...")
        
        # Create SQLite database
        conn = sqlite3.connect(self.db_file)
        
        # Execute schema first
        schema_file = self.database_path / "fault_demo_database_schema.sql"
        if schema_file.exists():
            with open(schema_file, 'r') as f:
                schema_sql = f.read()
                conn.executescript(schema_sql)
            logger.info("✅ Database schema loaded")
        else:
            logger.info("⚠️ NS3 schema file not found, healing_agent.py will create basic schema")
        
        # Load all data files
        data_files = [
            "fault_demo_database_nodes.sql",
            "fault_demo_database_links.sql", 
            "fault_demo_database_anomalies.sql",
            "fault_demo_database_recovery_tactics.sql",
            "fault_demo_database_policies.sql",
            "fault_demo_database_traffic_flows.sql"
        ]
        
        files_loaded = 0
        for file_name in data_files:
            file_path = self.database_path / file_name
            if file_path.exists():
                with open(file_path, 'r') as f:
                    data_sql = f.read()
                    conn.executescript(data_sql)
                logger.info(f"✅ Loaded {file_name}")
                files_loaded += 1
            else:
                logger.info(f"⚠️ NS3 file not found: {file_name}")
        
        if files_loaded == 0:
            logger.info("📝 No NS3 files found - healing_agent.py will create sample data")
        
        conn.commit()
        conn.close()
        logger.info("🚀 Knowledge base database ready for Nokia Build-a-thon!")
        logger.info(f"📊 Database file: {self.db_file}")
        
if __name__ == "__main__":
    loader = KnowledgeBaseLoader()
    loader.load_ns3_database()
    print("🎉 Nokia Build-a-thon knowledge base initialization complete!")
