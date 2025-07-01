import sqlite3
import json
import os
from pathlib import Path

class DatabaseSetup:
    def __init__(self, db_path='network_knowledge.db'):
        self.db_path = db_path
        self.conn = None
        
    def create_database(self):
        """Create and populate the complete database from SQL files"""
        try:
            # Remove existing database
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
                
            self.conn = sqlite3.connect(self.db_path)
            cursor = self.conn.cursor()
            
            # Execute schema
            self._execute_sql_file('fault_demo_database_schema.sql', cursor)
            
            # Populate tables
            self._execute_sql_file('fault_demo_database_nodes.sql', cursor)
            self._execute_sql_file('fault_demo_database_links.sql', cursor)
            self._execute_sql_file('fault_demo_database_policies.sql', cursor)
            self._execute_sql_file('fault_demo_database_recovery_tactics.sql', cursor)
            self._execute_sql_file('fault_demo_database_traffic_flows.sql', cursor)
            
            # Add additional knowledge tables for RAG
            self._create_rag_knowledge_tables(cursor)
            
            self.conn.commit()
            print(f"✅ Database created successfully: {self.db_path}")
            
        except Exception as e:
            print(f"❌ Database setup failed: {e}")
            raise
            
    def _execute_sql_file(self, filename, cursor):
        """Execute SQL commands from file"""
        try:
            with open(filename, 'r') as f:
                sql_content = f.read()
                cursor.executescript(sql_content)
            print(f"✅ Executed {filename}")
        except FileNotFoundError:
            print(f"⚠️ SQL file not found: {filename}")
        except Exception as e:
            print(f"❌ Error executing {filename}: {e}")
            
    def _create_rag_knowledge_tables(self, cursor):
        """Create additional tables for RAG knowledge"""
        rag_tables_sql = """
        -- Additional tables for RAG knowledge
        CREATE TABLE IF NOT EXISTS FaultPatterns (
            pattern_id INTEGER PRIMARY KEY,
            pattern_name VARCHAR(100) NOT NULL,
            symptoms TEXT,
            causes TEXT,
            healing_actions TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_api VARCHAR(100)
        );
        
        CREATE TABLE IF NOT EXISTS HealingTemplates (
            template_id INTEGER PRIMARY KEY,
            template_name VARCHAR(100) NOT NULL,
            action_type VARCHAR(100),
            description TEXT,
            duration INTEGER,
            success_rate REAL,
            prerequisites TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_api VARCHAR(100)
        );
        
        -- Populate fault patterns
        INSERT INTO FaultPatterns (pattern_name, symptoms, causes, healing_actions, source_api) VALUES
        ('Link_Failure', 'High packet loss,No connectivity,Timeout errors', 'Fiber cut,Equipment failure,Power outage', 'Emergency_Reroute,Redundant_Path_Activation,Physical_Repair', 'database'),
        ('High_Latency', 'Slow response times,User complaints,QoS degradation', 'Network congestion,Routing loops,Equipment overload', 'Traffic_Load_Balance,QoS_Prioritization,Load_Shedding', 'database'),
        ('Power_Outage', 'Node offline,No heartbeat,Service interruption', 'Grid failure,Equipment malfunction,Environmental factors', 'Backup_Power_Switch,Generator_Deployment,Load_Shedding', 'database'),
        ('Congestion', 'High bandwidth utilization,Packet drops,Slow performance', 'Traffic spikes,Insufficient capacity,Poor routing', 'Traffic_Load_Balance,QoS_Prioritization,Emergency_Reroute', 'database');
        
        -- Populate healing templates
        INSERT INTO HealingTemplates (template_name, action_type, description, duration, success_rate, prerequisites, source_api) VALUES
        ('Emergency_Traffic_Reroute', 'emergency_reroute', 'Quickly redirect traffic through alternative paths', 30, 0.85, 'Alternative paths available', 'database'),
        ('Backup_Power_Activation', 'power_switch', 'Switch to backup power source', 120, 0.75, 'Backup power system operational', 'database'),
        ('Load_Redistribution', 'load_balancing', 'Redistribute traffic load across multiple links', 45, 0.7, 'Multiple links available', 'database'),
        ('QoS_Emergency_Mode', 'qos_prioritization', 'Activate emergency QoS policies', 30, 0.8, 'QoS policies configured', 'database'),
        ('Node_Restart_Procedure', 'node_restart', 'Controlled restart of network node', 300, 0.65, 'Node supports remote restart', 'database');
        """
        
        cursor.executescript(rag_tables_sql)
        print("✅ RAG knowledge tables created and populated")

if __name__ == "__main__":
    db_setup = DatabaseSetup()
    db_setup.create_database()
