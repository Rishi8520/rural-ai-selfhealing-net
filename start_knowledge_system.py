#!/usr/bin/env python3
import subprocess
import time
import sys
import os
from pathlib import Path

def setup_and_start():
    """Setup database and start the knowledge API system"""
    
    print("🔧 Setting up Nokia Rural Network Knowledge System...")
    
    # Step 1: Setup database
    print("\n📊 Step 1: Creating database...")
    try:
        from setup_database import DatabaseSetup
        db_setup = DatabaseSetup()
        db_setup.create_database()
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False
    
    # Step 2: Create fallback knowledge base
    print("\n🔄 Step 2: Creating fallback knowledge base...")
    try:
        from fallback_knowledge_base import FallbackKnowledgeBase
        fallback_kb = FallbackKnowledgeBase()
    except Exception as e:
        print(f"❌ Fallback KB creation failed: {e}")
        return False
    
    # Step 3: Start API server
    print("\n🚀 Step 3: Starting API server...")
    try:
        subprocess.Popen([sys.executable, 'knowledge_api_server.py'])
        time.sleep(3)  # Give server time to start
        print("✅ API server started on http://localhost:8080")
    except Exception as e:
        print(f"❌ API server start failed: {e}")
        return False
    
    # Step 4: Test endpoints
    print("\n🧪 Step 4: Testing API endpoints...")
    import requests
    endpoints = [
        'http://localhost:8080/api/health',
        'http://localhost:8080/api/node-types',
        'http://localhost:8080/api/fault-patterns',
        'http://localhost:8080/api/healing-templates',
        'http://localhost:8080/api/recovery-tactics'
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, timeout=5)
            if response.status_code == 200:
                print(f"✅ {endpoint} - OK")
            else:
                print(f"⚠️ {endpoint} - HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint} - Failed: {e}")
    
    print(f"\n🎉 Knowledge system setup complete!")
    print(f"📊 Database: network_knowledge.db")
    print(f"🔄 Fallback: fallback_knowledge.db") 
    print(f"🔗 API Server: http://localhost:8080")
    print(f"📋 Now you can start the healing agent!")
    
    return True

if __name__ == "__main__":
    success = setup_and_start()
    if success:
        input("\nPress Enter to stop the API server...")
    else:
        print("❌ Setup failed!")
        sys.exit(1)

