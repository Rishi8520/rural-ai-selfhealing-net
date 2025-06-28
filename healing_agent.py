import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import asyncio
import logging
import json
import time
import zmq
import zmq.asyncio
import google.generativeai as genai
import numpy as np
import sqlite3
import platform
import torch
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from sentence_transformers import SentenceTransformer
import faiss
from prometheus_client import start_http_server, Gauge, Counter, Histogram
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import google.api_core.exceptions

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class AnomalyAlert:
    message_id: str
    node_id: str
    anomaly_id: str
    anomaly_score: float
    severity: str
    detection_timestamp: str
    network_context: Dict[str, Any]
    confidence: float  # NO DEFAULT - must be provided by calculation agent

@dataclass
class HealingAction:
    action_id: str
    action_type: str
    priority: int
    description: str
    parameters: Dict[str, Any]
    estimated_duration: int
    success_probability: float

@dataclass
class HealingPlan:
    plan_id: str
    anomaly_id: str
    node_id: str
    severity: str
    healing_actions: List[HealingAction]
    total_estimated_duration: int
    confidence: float
    requires_approval: bool
    generated_timestamp: str

class DynamicHealingConfidenceCalculator:
    def __init__(self):
        self.action_success_history = {}
        self.plan_effectiveness_history = {}
        self.rag_quality_metrics = {}
        
    def calculate_dynamic_success_probability(self, action_type, node_type, severity):
        """Calculate success probability from actual execution history"""
        key = f"{action_type}_{node_type}_{severity}"
        
        if key not in self.action_success_history:
            self.action_success_history[key] = {'successes': 0, 'attempts': 0}
        
        history = self.action_success_history[key]
        
        if history['attempts'] == 0:
            return self.estimate_from_similar_actions(action_type, node_type, severity)
        
        # Actual success rate from execution history
        actual_success_rate = history['successes'] / history['attempts']
        return actual_success_rate
    
    def estimate_from_similar_actions(self, action_type, node_type, severity):
        """Estimate based on similar action types"""
        similar_rates = []
        
        for key, history in self.action_success_history.items():
            if history['attempts'] > 0:
                key_parts = key.split('_')
                if len(key_parts) >= 3:
                    if key_parts[1] == node_type or key_parts[2] == severity:
                        rate = history['successes'] / history['attempts']
                        similar_rates.append(rate)
        
        if similar_rates:
            return sum(similar_rates) / len(similar_rates)
        
        # Fallback to action complexity estimation
        complexity_scores = {
            'emergency_reroute': 0.85,
            'power_switch': 0.75,
            'resource_reallocation': 0.65,
            'traffic_rerouting': 0.8,
            'load_balancing': 0.7
        }
        
        base_score = complexity_scores.get(action_type, 0.6)
        
        # Adjust based on severity
        severity_multipliers = {'low': 1.1, 'medium': 1.0, 'high': 0.9, 'critical': 0.8}
        multiplier = severity_multipliers.get(severity, 1.0)
        
        return min(1.0, base_score * multiplier)
    
    def calculate_plan_confidence_from_actual_data(self, healing_actions, anomaly_confidence, rag_quality):
        """Calculate plan confidence from actual action performance and input confidence"""
        if not healing_actions:
            return 0.0
        
        # Factor 1: Average action success probabilities
        action_confidences = [action.success_probability for action in healing_actions]
        avg_action_confidence = sum(action_confidences) / len(action_confidences)
        
        # Factor 2: Priority weighting (higher priority = higher confidence factor)
        priority_weights = []
        for action in healing_actions:
            weight = 1.0 / action.priority if action.priority > 0 else 1.0
            priority_weights.append(weight)
        
        weighted_action_confidence = sum(conf * weight for conf, weight in zip(action_confidences, priority_weights))
        total_weight = sum(priority_weights)
        
        if total_weight > 0:
            priority_weighted_confidence = weighted_action_confidence / total_weight
        else:
            priority_weighted_confidence = avg_action_confidence
        
        # Factor 3: Strategy diversity bonus
        strategy_types = set()
        for action in healing_actions:
            if action.action_id.startswith('DB_KB_'):
                strategy_types.add('database_knowledge')
            elif action.action_id.startswith('RAG_AI_'):
                strategy_types.add('rag_ai')
            elif action.action_id.startswith('TMPL_'):
                strategy_types.add('template')
        
        diversity_factor = len(strategy_types) / 3.0  # Max 3 strategies
        
        # Factor 4: RAG quality factor
        rag_factor = min(1.0, rag_quality)
        
        # Combine all factors with input anomaly confidence
        plan_base_confidence = (
            avg_action_confidence * 0.3 +
            priority_weighted_confidence * 0.4 +
            diversity_factor * 0.15 +
            rag_factor * 0.15
        )
        
        # Final confidence includes input confidence
        final_confidence = (plan_base_confidence * 0.7) + (anomaly_confidence * 0.3)
        
        return min(1.0, max(0.0, final_confidence))
    
    def update_action_result(self, action_type, node_type, severity, was_successful):
        """Update actual execution results"""
        key = f"{action_type}_{node_type}_{severity}"
        
        if key not in self.action_success_history:
            self.action_success_history[key] = {'successes': 0, 'attempts': 0}
        
        self.action_success_history[key]['attempts'] += 1
        if was_successful:
            self.action_success_history[key]['successes'] += 1
    
    def assess_rag_quality(self, retrieved_docs_count, query_similarity_scores):
        """Assess RAG retrieval quality"""
        if retrieved_docs_count == 0:
            return 0.1
        
        if not query_similarity_scores:
            return 0.5
        
        avg_similarity = sum(query_similarity_scores) / len(query_similarity_scores)
        quality_score = min(1.0, avg_similarity * retrieved_docs_count / 3.0)
        
        return quality_score

class APIKnowledgeLoader:
    def __init__(self):
        self.knowledge_apis = self.load_api_configuration()
        
    def load_api_configuration(self):
        api_config_path = os.getenv('KNOWLEDGE_API_CONFIG', 'knowledge_api_config.json')
        try:
            with open(api_config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"API config file not found: {api_config_path}")
            return self.get_default_api_config()
    
    def get_default_api_config(self):
        return {
            "node_types_api": {
                "url": os.getenv('NODE_TYPES_API_URL', 'http://localhost:8080/api/node-types'),
                "headers": {"Authorization": f"Bearer {os.getenv('API_TOKEN', '')}"}
            },
            "fault_patterns_api": {
                "url": os.getenv('FAULT_PATTERNS_API_URL', 'http://localhost:8080/api/fault-patterns'),
                "headers": {"Authorization": f"Bearer {os.getenv('API_TOKEN', '')}"}
            },
            "healing_templates_api": {
                "url": os.getenv('HEALING_TEMPLATES_API_URL', 'http://localhost:8080/api/healing-templates'),
                "headers": {"Authorization": f"Bearer {os.getenv('API_TOKEN', '')}"}
            },
            "recovery_tactics_api": {
                "url": os.getenv('RECOVERY_TACTICS_API_URL', 'http://localhost:8080/api/recovery-tactics'),
                "headers": {"Authorization": f"Bearer {os.getenv('API_TOKEN', '')}"}
            }
        }
    
    async def load_knowledge_from_apis(self):
        knowledge_data = {}
        
        for api_name, api_config in self.knowledge_apis.items():
            try:
                response = requests.get(api_config['url'], headers=api_config.get('headers', {}), timeout=30)
                if response.status_code == 200:
                    knowledge_data[api_name] = response.json()
                    logger.info(f"Loaded knowledge from {api_name}: {len(knowledge_data[api_name])} items")
                else:
                    logger.error(f"Failed to load from {api_name}: HTTP {response.status_code}")
                    knowledge_data[api_name] = []
            except Exception as e:
                logger.error(f"Error loading from {api_name}: {e}")
                knowledge_data[api_name] = []
        
        return knowledge_data

class DatabaseManager:
    def __init__(self, db_path='api_driven_network_knowledge.db'):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.api_loader = APIKnowledgeLoader()
        self._connect()
        self._ensure_tables()

    def _connect(self):
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            logger.info(f"Connected to database: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def _ensure_tables(self):
        try:
            self.cursor.executescript("""
                CREATE TABLE IF NOT EXISTS NodeTypes (
                    node_type_id INTEGER PRIMARY KEY,
                    node_type_name VARCHAR(100) NOT NULL,
                    description TEXT,
                    critical_metrics TEXT,
                    common_faults TEXT,
                    healing_strategies TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source_api VARCHAR(100)
                );

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

                CREATE TABLE IF NOT EXISTS RecoveryTactics (
                    tactic_id VARCHAR(50) PRIMARY KEY,
                    tactic_name VARCHAR(100),
                    description TEXT,
                    estimated_time_seconds INTEGER,
                    priority VARCHAR(20),
                    node_type_applicable TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source_api VARCHAR(100)
                );

                CREATE TABLE IF NOT EXISTS KnowledgeMetadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_records INTEGER,
                    api_source VARCHAR(100),
                    status VARCHAR(50)
                );
            """)
            self.conn.commit()
            logger.info("Database tables created successfully")
        except sqlite3.Error as e:
            logger.error(f"Error creating tables: {e}")
            raise

    async def load_knowledge_from_apis(self):
        try:
            knowledge_data = await self.api_loader.load_knowledge_from_apis()
            
            await self._store_node_types(knowledge_data.get('node_types_api', []))
            await self._store_fault_patterns(knowledge_data.get('fault_patterns_api', []))
            await self._store_healing_templates(knowledge_data.get('healing_templates_api', []))
            await self._store_recovery_tactics(knowledge_data.get('recovery_tactics_api', []))
            
            self._update_metadata(knowledge_data)
            
        except Exception as e:
            logger.error(f"Error loading knowledge from APIs: {e}")

    async def _store_node_types(self, node_types_data):
        try:
            self.cursor.execute("DELETE FROM NodeTypes WHERE source_api = 'api'")
            
            for item in node_types_data:
                self.cursor.execute("""
                    INSERT INTO NodeTypes (node_type_name, description, critical_metrics, common_faults, healing_strategies, source_api)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    item.get('name', 'unknown'),
                    item.get('description', ''),
                    ','.join(item.get('critical_metrics', [])),
                    ','.join(item.get('common_faults', [])),
                    ','.join(item.get('healing_strategies', [])),
                    'api'
                ))
            
            self.conn.commit()
            logger.info(f"Stored {len(node_types_data)} node types from API")
            
        except Exception as e:
            logger.error(f"Error storing node types: {e}")

    async def _store_fault_patterns(self, fault_patterns_data):
        try:
            self.cursor.execute("DELETE FROM FaultPatterns WHERE source_api = 'api'")
            
            for item in fault_patterns_data:
                self.cursor.execute("""
                    INSERT INTO FaultPatterns (pattern_name, symptoms, causes, healing_actions, source_api)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    item.get('name', 'unknown'),
                    ','.join(item.get('symptoms', [])),
                    ','.join(item.get('causes', [])),
                    ','.join(item.get('healing_actions', [])),
                    'api'
                ))
            
            self.conn.commit()
            logger.info(f"Stored {len(fault_patterns_data)} fault patterns from API")
            
        except Exception as e:
            logger.error(f"Error storing fault patterns: {e}")

    async def _store_healing_templates(self, healing_templates_data):
        try:
            self.cursor.execute("DELETE FROM HealingTemplates WHERE source_api = 'api'")
            
            for item in healing_templates_data:
                self.cursor.execute("""
                    INSERT INTO HealingTemplates (template_name, action_type, description, duration, success_rate, prerequisites, source_api)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.get('name', 'unknown'),
                    item.get('action_type', ''),
                    item.get('description', ''),
                    item.get('duration', 60),
                    item.get('success_rate', 0.5),
                    ','.join(item.get('prerequisites', [])),
                    'api'
                ))
            
            self.conn.commit()
            logger.info(f"Stored {len(healing_templates_data)} healing templates from API")
            
        except Exception as e:
            logger.error(f"Error storing healing templates: {e}")

    async def _store_recovery_tactics(self, recovery_tactics_data):
        try:
            self.cursor.execute("DELETE FROM RecoveryTactics WHERE source_api = 'api'")
            
            for item in recovery_tactics_data:
                self.cursor.execute("""
                    INSERT INTO RecoveryTactics (tactic_id, tactic_name, description, estimated_time_seconds, priority, node_type_applicable, source_api)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.get('id', f"tactic_{int(time.time())}"),
                    item.get('name', 'unknown'),
                    item.get('description', ''),
                    item.get('estimated_time', 60),
                    item.get('priority', 'medium'),
                    ','.join(item.get('applicable_node_types', [])),
                    'api'
                ))
            
            self.conn.commit()
            logger.info(f"Stored {len(recovery_tactics_data)} recovery tactics from API")
            
        except Exception as e:
            logger.error(f"Error storing recovery tactics: {e}")

    def _update_metadata(self, knowledge_data):
        try:
            total_records = sum(len(data) for data in knowledge_data.values())
            
            self.cursor.execute("""
                INSERT INTO KnowledgeMetadata (total_records, api_source, status)
                VALUES (?, ?, ?)
            """, (total_records, 'multiple_apis', 'success'))
            
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"Error updating metadata: {e}")

    def get_node_type_knowledge(self, node_type):
        try:
            self.cursor.execute("SELECT * FROM NodeTypes WHERE node_type_name = ?", (node_type,))
            result = self.cursor.fetchone()
            if result:
                return {
                    'node_type_id': result[0],
                    'node_type_name': result[1],
                    'description': result[2],
                    'critical_metrics': result[3].split(',') if result[3] else [],
                    'common_faults': result[4].split(',') if result[4] else [],
                    'healing_strategies': result[5].split(',') if result[5] else []
                }
            return {}
        except sqlite3.Error as e:
            logger.error(f"Error fetching node type knowledge: {e}")
            return {}

    def get_fault_pattern_knowledge(self, pattern_name):
        try:
            self.cursor.execute("SELECT * FROM FaultPatterns WHERE pattern_name = ?", (pattern_name,))
            result = self.cursor.fetchone()
            if result:
                return {
                    'pattern_id': result[0],
                    'pattern_name': result[1],
                    'symptoms': result[2].split(',') if result[2] else [],
                    'causes': result[3].split(',') if result[3] else [],
                    'healing_actions': result[4].split(',') if result[4] else []
                }
            return {}
        except sqlite3.Error as e:
            logger.error(f"Error fetching fault pattern knowledge: {e}")
            return {}

    def get_healing_templates(self, action_type=None):
        try:
            if action_type:
                self.cursor.execute("SELECT * FROM HealingTemplates WHERE action_type = ?", (action_type,))
            else:
                self.cursor.execute("SELECT * FROM HealingTemplates")
            
            results = self.cursor.fetchall()
            templates = []
            for result in results:
                templates.append({
                    'template_id': result[0],
                    'template_name': result[1],
                    'action_type': result[2],
                    'description': result[3],
                    'duration': result[4],
                    'success_rate': result[5],
                    'prerequisites': result[6].split(',') if result[6] else []
                })
            return templates
        except sqlite3.Error as e:
            logger.error(f"Error fetching healing templates: {e}")
            return []

    def get_recovery_tactics_for_node_type(self, node_type):
        try:
            self.cursor.execute("SELECT * FROM RecoveryTactics WHERE node_type_applicable LIKE ?", (f'%{node_type}%',))
            results = self.cursor.fetchall()
            tactics = []
            for result in results:
                tactics.append({
                    'tactic_id': result[0],
                    'tactic_name': result[1],
                    'description': result[2],
                    'estimated_time_seconds': result[3],
                    'priority': result[4],
                    'node_type_applicable': result[5].split(',') if result[5] else []
                })
            return tactics
        except sqlite3.Error as e:
            logger.error(f"Error fetching recovery tactics: {e}")
            return []

    def get_all_knowledge_documents(self):
        documents = []
        try:
            self.cursor.execute("SELECT * FROM NodeTypes")
            for row in self.cursor.fetchall():
                doc = f"Node Type: {row[1]}. Description: {row[2]}. Critical Metrics: {row[3]}. Common Faults: {row[4]}. Healing Strategies: {row[5]}"
                documents.append(doc)

            self.cursor.execute("SELECT * FROM FaultPatterns")
            for row in self.cursor.fetchall():
                doc = f"Fault Pattern: {row[1]}. Symptoms: {row[2]}. Causes: {row[3]}. Healing Actions: {row[4]}"
                documents.append(doc)

            self.cursor.execute("SELECT * FROM HealingTemplates")
            for row in self.cursor.fetchall():
                doc = f"Healing Template: {row[1]}. Action Type: {row[2]}. Description: {row[3]}. Duration: {row[4]}s. Success Rate: {row[5]}. Prerequisites: {row[6]}"
                documents.append(doc)

            self.cursor.execute("SELECT * FROM RecoveryTactics")
            for row in self.cursor.fetchall():
                doc = f"Recovery Tactic: {row[1]}. Description: {row[2]}. Time: {row[3]}s. Priority: {row[4]}. Applicable to: {row[5]}"
                documents.append(doc)

        except sqlite3.Error as e:
            logger.error(f"Error fetching knowledge documents: {e}")
        
        return documents

    def close(self):
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

class EnhancedHealingAgent:
    def __init__(self):
        self.context = zmq.asyncio.Context()
        self.a2a_subscriber = None
        self.mcp_publisher = None
        self.orchestrator_publisher = None
        
        self.gemini_api_key = os.getenv('GOOGLE_API_KEY')
        if not self.gemini_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        
        self.gemini_model = None
        self.initialize_gemini()
        
        self.embedding_model = self._initialize_embeddings()
        self.db_manager = DatabaseManager()
        self.rag_index = None
        self.rag_documents = []
        
        # Initialize dynamic confidence calculator
        self.dynamic_confidence_calc = DynamicHealingConfidenceCalculator()
        
        self.setup_prometheus_metrics()
        start_http_server(8004)
        
        self.healing_plans_dir = Path("healing_plans")
        self.healing_reports_dir = Path("healing_reports")
        self.healing_plans_dir.mkdir(exist_ok=True)
        self.healing_reports_dir.mkdir(exist_ok=True)
        
        self.processing_queue = asyncio.Queue()
        self.active_healing_plans = {}
        self.is_running = False
        
        self.comm_metrics = {
            'alerts_received': 0,
            'healing_plans_generated': 0,
            'responses_sent': 0,
            'failed_operations': 0
        }
        
        self.processing_times = []
        
        logger.info("Enhanced Healing Agent with API-driven knowledge initialized successfully")

    def initialize_gemini(self):
        try:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_model = genai.GenerativeModel('gemini-pro')
            logger.info("Gemini AI initialized successfully")
        except Exception as e:
            logger.error(f"Gemini AI initialization failed: {e}")
            raise

    def _initialize_embeddings(self):
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = SentenceTransformer('all-MiniLM-L6-v2', device=device)
            logger.info(f"SentenceTransformer loaded on: {device}")
            return model
        except Exception as e:
            logger.error(f"Error initializing embeddings: {e}")
            return SentenceTransformer('all-MiniLM-L6-v2', device="cpu")

    def setup_prometheus_metrics(self):
        self.healing_plan_generation_counter = Counter(
            'nokia_healing_plans_generated_total',
            'Total healing plans generated',
            ['node_id', 'severity', 'strategy']
        )
        
        self.healing_plan_effectiveness_gauge = Gauge(
            'nokia_healing_plan_effectiveness_percentage',
            'Healing plan effectiveness percentage',
            ['plan_id', 'strategy']
        )
        
        self.gemini_llm_response_time = Histogram(
            'nokia_gemini_llm_response_time_seconds',
            'Gemini LLM response time',
            ['query_type']
        )

    async def _load_rag_data(self):
        try:
            await self.db_manager.load_knowledge_from_apis()
            
            documents = self.db_manager.get_all_knowledge_documents()
            
            if not documents:
                logger.warning("No knowledge documents found for RAG")
                return

            self.rag_documents = documents
            
            logger.info(f"Generating embeddings for {len(documents)} documents")
            document_embeddings = self.embedding_model.encode(documents)
            
            self.rag_index = faiss.IndexFlatL2(document_embeddings.shape[1])
            self.rag_index.add(np.array(document_embeddings).astype('float32'))
            
            logger.info("RAG index built successfully from API-driven knowledge")
            
        except Exception as e:
            logger.error(f"Error loading RAG data: {e}")

    def _get_rag_context(self, node_id, anomaly_description):
        if not self.rag_index or not self.rag_documents:
            logger.warning("RAG index not available")
            return "No RAG context available", 0.1

        try:
            query_text = f"Node {node_id} anomaly: {anomaly_description}"
            query_embedding = self.embedding_model.encode([query_text]).astype('float32')
            
            D, I = self.rag_index.search(query_embedding, k=3)
            context_docs = [self.rag_documents[i] for i in I[0] if i != -1]
            
            if context_docs:
                logger.info(f"Retrieved {len(context_docs)} RAG context documents")
                # Calculate RAG quality
                similarities = [1.0 / (1.0 + d) for d in D[0] if d != -1]  # Convert distance to similarity
                rag_quality = self.dynamic_confidence_calc.assess_rag_quality(len(context_docs), similarities)
                return "\n\n".join(context_docs), rag_quality
            else:
                return "No relevant RAG context found", 0.1
                
        except Exception as e:
            logger.error(f"Error retrieving RAG context: {e}")
            return "RAG context retrieval failed", 0.1

    async def initialize_communication(self):
        try:
            self.a2a_subscriber = self.context.socket(zmq.SUB)
            self.a2a_subscriber.connect("tcp://127.0.0.1:5555")
            self.a2a_subscriber.setsockopt_string(zmq.SUBSCRIBE, "")
            
            self.mcp_publisher = self.context.socket(zmq.PUB)
            self.mcp_publisher.bind("tcp://127.0.0.1:5556")
            
            self.orchestrator_publisher = self.context.socket(zmq.PUB)
            self.orchestrator_publisher.bind("tcp://127.0.0.1:5558")
            
            logger.info("Enhanced Healing Agent communication initialized")
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"Communication initialization failed: {e}")
            raise

    async def start_with_enhanced_communication(self):
        logger.info("Starting Enhanced Healing Agent with API-driven knowledge...")
        
        await self.initialize_communication()
        await self._load_rag_data()
        
        self.is_running = True
        
        tasks = [
            asyncio.create_task(self.listen_for_anomaly_alerts()),
            asyncio.create_task(self.process_healing_queue()),
            asyncio.create_task(self.monitor_healing_performance()),
            asyncio.create_task(self.generate_periodic_reports()),
            asyncio.create_task(self.periodic_knowledge_refresh())
        ]
        
        logger.info("Enhanced Healing Agent started successfully")
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
        finally:
            await self.cleanup()

    async def listen_for_anomaly_alerts(self):
        logger.info("Starting anomaly alert listener...")
        
        while self.is_running:
            try:
                message = await asyncio.wait_for(
                    self.a2a_subscriber.recv_json(),
                    timeout=1.0
                )
                
                if message.get('message_type') == 'anomaly_alert':
                    await self.handle_incoming_anomaly_alert(message)
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error receiving anomaly alert: {e}")
                self.comm_metrics['failed_operations'] += 1
                await asyncio.sleep(1)

    async def handle_incoming_anomaly_alert(self, alert_message: Dict[str, Any]):
        try:
            anomaly_alert = self.parse_anomaly_alert(alert_message)
            if anomaly_alert is None:
                logger.error("Invalid anomaly alert received")
                return

            logger.info(f"Anomaly alert received: {anomaly_alert.anomaly_id}")
            
            self.comm_metrics['alerts_received'] += 1
            await self.processing_queue.put(anomaly_alert)
            
        except Exception as e:
            logger.error(f"Error handling anomaly alert: {e}")
            self.comm_metrics['failed_operations'] += 1

    def parse_anomaly_alert(self, alert_message: Dict[str, Any]) -> Optional[AnomalyAlert]:
        try:
            anomaly_details = alert_message.get('anomaly_details', {})
            network_context = alert_message.get('network_context', {})
            
            # Extract confidence - NO default value
            confidence = anomaly_details.get('confidence')
            if confidence is None:
                logger.error("No confidence provided in anomaly alert")
                return None
            
            return AnomalyAlert(
                message_id=alert_message.get('message_id', ''),
                node_id=anomaly_details.get('node_id', ''),
                anomaly_id=anomaly_details.get('anomaly_id', ''),
                anomaly_score=anomaly_details.get('anomaly_score', 0.0),
                severity=anomaly_details.get('severity', 'unknown'),
                detection_timestamp=anomaly_details.get('detection_timestamp', ''),
                network_context=network_context,
                confidence=confidence  # DYNAMIC confidence from calculation agent
            )
        except Exception as e:
            logger.error(f"Error parsing anomaly alert: {e}")
            return None

    async def process_healing_queue(self):
        logger.info("Starting healing queue processor...")
        
        while self.is_running:
            try:
                anomaly_alert = await asyncio.wait_for(
                    self.processing_queue.get(),
                    timeout=5.0
                )
                
                start_time = time.time()
                healing_plan = await self.generate_comprehensive_healing_plan(anomaly_alert)
                processing_time = time.time() - start_time
                
                if healing_plan:
                    await self.send_healing_responses(anomaly_alert, healing_plan)
                    
                    self.processing_times.append(processing_time)
                    self.comm_metrics['healing_plans_generated'] += 1
                    
                    self.healing_plan_generation_counter.labels(
                        node_id=anomaly_alert.node_id,
                        severity=anomaly_alert.severity,
                        strategy="multi_strategy"
                    ).inc()
                    
                    logger.info(f"Healing plan generated in {processing_time:.2f}s: {healing_plan.plan_id}")
                else:
                    logger.error(f"Failed to generate healing plan for {anomaly_alert.anomaly_id}")
                    self.comm_metrics['failed_operations'] += 1
                
                self.processing_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing healing queue: {e}")
                self.comm_metrics['failed_operations'] += 1

    async def generate_comprehensive_healing_plan(self, anomaly_alert: AnomalyAlert) -> Optional[HealingPlan]:
        try:
            logger.info(f"Generating comprehensive healing plan for {anomaly_alert.anomaly_id}")
            
            network_analysis = self.analyze_network_context(anomaly_alert)
            
            healing_actions = []
            
            kb_actions = self.generate_database_knowledge_actions(anomaly_alert, network_analysis)
            healing_actions.extend(kb_actions)
            
            rag_ai_actions, rag_quality = await self.generate_rag_ai_healing_actions(anomaly_alert, network_analysis)
            healing_actions.extend(rag_ai_actions)
            
            template_actions = self.generate_database_template_actions(anomaly_alert, network_analysis)
            healing_actions.extend(template_actions)
            
            healing_actions = self.prioritize_and_deduplicate_actions(healing_actions)
            
            if not healing_actions:
                logger.error(f"No healing actions generated for {anomaly_alert.anomaly_id}")
                return None
            
            # Calculate dynamic confidence using all available data
            plan_confidence = self.dynamic_confidence_calc.calculate_plan_confidence_from_actual_data(
                healing_actions, anomaly_alert.confidence, rag_quality
            )
            
            healing_plan = HealingPlan(
                plan_id=f"HEAL_{anomaly_alert.node_id}_{int(time.time())}",
                anomaly_id=anomaly_alert.anomaly_id,
                node_id=anomaly_alert.node_id,
                severity=anomaly_alert.severity,
                healing_actions=healing_actions,
                total_estimated_duration=sum(action.estimated_duration for action in healing_actions),
                confidence=plan_confidence,  # DYNAMIC confidence
                requires_approval=anomaly_alert.severity in ['critical', 'high'],
                generated_timestamp=datetime.now().isoformat()
            )
            
            await self.save_healing_plan(healing_plan)
            self.active_healing_plans[healing_plan.plan_id] = healing_plan
            
            logger.info(f"Comprehensive healing plan generated: {healing_plan.plan_id}")
            
            return healing_plan
            
        except Exception as e:
            logger.error(f"Error generating healing plan: {e}")
            return None

    def analyze_network_context(self, anomaly_alert: AnomalyAlert) -> Dict[str, Any]:
        try:
            network_context = anomaly_alert.network_context
            node_type = network_context.get('node_type', 'GENERIC')
            fault_pattern = network_context.get('fault_pattern', 'unknown')
            
            node_knowledge = self.db_manager.get_node_type_knowledge(node_type)
            fault_knowledge = self.db_manager.get_fault_pattern_knowledge(fault_pattern)
            
            analysis = {
                'node_type': node_type,
                'fault_pattern': fault_pattern,
                'critical_metrics': node_knowledge.get('critical_metrics', []),
                'common_faults': node_knowledge.get('common_faults', []),
                'healing_strategies': node_knowledge.get('healing_strategies', []),
                'fault_symptoms': fault_knowledge.get('symptoms', []),
                'fault_causes': fault_knowledge.get('causes', []),
                'recommended_actions': fault_knowledge.get('healing_actions', []),
                'severity_level': anomaly_alert.severity,
                'anomaly_score': anomaly_alert.anomaly_score,
                'spatial_context': network_context.get('spatial_context', {})
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing network context: {e}")
            return {}

    def generate_database_knowledge_actions(self, anomaly_alert: AnomalyAlert, analysis: Dict[str, Any]) -> List[HealingAction]:
        actions = []
        
        try:
            node_type = analysis.get('node_type', 'GENERIC')
            recovery_tactics = self.db_manager.get_recovery_tactics_for_node_type(node_type)
            
            for tactic in recovery_tactics[:3]:
                # DYNAMIC success probability based on actual execution history
                dynamic_success_prob = self.dynamic_confidence_calc.calculate_dynamic_success_probability(
                    tactic['tactic_name'], node_type, anomaly_alert.severity
                )
                
                action = HealingAction(
                    action_id=f"DB_KB_{tactic['tactic_id']}_{int(time.time())}",
                    action_type=tactic['tactic_name'].lower().replace(' ', '_'),
                    priority=1 if tactic['priority'] == 'high' else 2 if tactic['priority'] == 'medium' else 3,
                    description=tactic['description'],
                    parameters={
                        'tactic_id': tactic['tactic_id'],
                        'estimated_time': tactic['estimated_time_seconds'],
                        'priority_level': tactic['priority']
                    },
                    estimated_duration=tactic['estimated_time_seconds'],
                    success_probability=dynamic_success_prob  # DYNAMIC
                )
                actions.append(action)
            
            logger.info(f"Generated {len(actions)} database knowledge-based actions")
            
        except Exception as e:
            logger.error(f"Error generating database knowledge actions: {e}")
        
        return actions

    async def generate_rag_ai_healing_actions(self, anomaly_alert: AnomalyAlert, analysis: Dict[str, Any]) -> tuple[List[HealingAction], float]:
        actions = []
        rag_quality = 0.1
        
        try:
            rag_context, rag_quality = self._get_rag_context(anomaly_alert.node_id, f"Anomaly {anomaly_alert.anomaly_id}")
            
            prompt = self.build_rag_enhanced_prompt(anomaly_alert, analysis, rag_context)
            
            start_time = time.time()
            response = await self.send_llm_request(prompt)
            response_time = time.time() - start_time
            
            self.gemini_llm_response_time.labels(query_type="rag_healing_generation").observe(response_time)
            
            if response:
                ai_actions = self.parse_gemini_response(response)
                actions.extend(ai_actions)
                logger.info(f"Generated {len(ai_actions)} RAG-enhanced AI actions")
            
        except Exception as e:
            logger.error(f"Error generating RAG AI actions: {e}")
        
        return actions, rag_quality

    def build_rag_enhanced_prompt(self, anomaly_alert: AnomalyAlert, analysis: Dict[str, Any], rag_context: str) -> str:
        prompt = f"""
You are an expert Nokia rural network healing specialist with access to comprehensive knowledge base.

ANOMALY DETAILS:
- Node ID: {anomaly_alert.node_id}
- Anomaly Score: {anomaly_alert.anomaly_score:.3f}
- Severity: {anomaly_alert.severity}
- Node Type: {analysis.get('node_type', 'unknown')}
- Fault Pattern: {analysis.get('fault_pattern', 'unknown')}

NETWORK CONTEXT:
- Critical Metrics: {', '.join(analysis.get('critical_metrics', []))}
- Detected Symptoms: {', '.join(analysis.get('fault_symptoms', []))}
- Possible Causes: {', '.join(analysis.get('fault_causes', []))}

KNOWLEDGE BASE CONTEXT:
{rag_context}

Generate 2-3 specific healing actions in JSON format:

{{
    "actions": [
        {{
            "action_type": "specific_action_name",
            "description": "detailed description",
            "priority": 1-3,
            "parameters": {{"key": "value"}},
            "estimated_duration": seconds,
            "success_probability": 0.0-1.0
        }}
    ]
}}

Focus on Nokia rural network best practices. Ensure actions are technically feasible, prioritized by impact, and include specific implementation parameters.
"""
        return prompt

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3),
           retry=retry_if_exception_type(google.api_core.exceptions.ResourceExhausted))
    async def send_llm_request(self, prompt, temperature=0.7, max_output_tokens=1024):
        try:
            response = self.gemini_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                ),
            )
            
            if hasattr(response, 'text'):
                return response.text
            elif hasattr(response, 'candidates') and response.candidates:
                return response.candidates[0].content.parts[0].text
            else:
                logger.error(f"Unexpected LLM response format")
                return None
                
        except google.api_core.exceptions.ResourceExhausted as e:
            logger.warning(f"ResourceExhausted error from LLM, retrying: {e}")
            raise
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return None

    def parse_gemini_response(self, response_text: str) -> List[HealingAction]:
        actions = []
        
        try:
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if json_match:
                response_data = json.loads(json_match.group())
                action_data_list = response_data.get('actions', [])
                
                for i, action_data in enumerate(action_data_list):
                    # Calculate dynamic success probability
                    dynamic_success_prob = self.dynamic_confidence_calc.calculate_dynamic_success_probability(
                        action_data.get('action_type', 'ai_action'), 
                        'generic', 
                        'medium'
                    )
                    
                    action = HealingAction(
                        action_id=f"RAG_AI_{int(time.time())}_{i}",
                        action_type=action_data.get('action_type', 'ai_action'),
                        priority=action_data.get('priority', 3),
                        description=action_data.get('description', 'AI-generated action'),
                        parameters=action_data.get('parameters', {}),
                        estimated_duration=action_data.get('estimated_duration', 60),
                        success_probability=dynamic_success_prob  # DYNAMIC
                    )
                    actions.append(action)
                    
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {e}")
        
        return actions

    def generate_database_template_actions(self, anomaly_alert: AnomalyAlert, analysis: Dict[str, Any]) -> List[HealingAction]:
        actions = []
        
        try:
            templates = self.db_manager.get_healing_templates()
            
            relevant_templates = []
            
            if anomaly_alert.severity in ['critical', 'high']:
                relevant_templates.extend([t for t in templates if 'emergency' in t['template_name'] or t['duration'] <= 60])
            
            relevant_templates.extend([t for t in templates if t not in relevant_templates][:2])
            
            for template in relevant_templates[:3]:
                # Calculate dynamic success probability
                dynamic_success_prob = self.dynamic_confidence_calc.calculate_dynamic_success_probability(
                    template['action_type'], 
                    analysis.get('node_type', 'GENERIC'), 
                    anomaly_alert.severity
                )
                
                action = HealingAction(
                    action_id=f"TMPL_{template['template_id']}_{int(time.time())}",
                    action_type=template['action_type'],
                    priority=1 if template['duration'] <= 60 else 2,
                    description=template['description'],
                    parameters={
                        'template_id': template['template_id'],
                        'prerequisites': template['prerequisites']
                    },
                    estimated_duration=template['duration'],
                    success_probability=dynamic_success_prob  # DYNAMIC
                )
                actions.append(action)
            
            logger.info(f"Generated {len(actions)} database template actions")
            
        except Exception as e:
            logger.error(f"Error generating database template actions: {e}")
        
        return actions

    def prioritize_and_deduplicate_actions(self, actions: List[HealingAction]) -> List[HealingAction]:
        try:
            unique_actions = {}
            for action in actions:
                key = action.action_type
                if key not in unique_actions or action.priority < unique_actions[key].priority:
                    unique_actions[key] = action
            
            sorted_actions = sorted(
                unique_actions.values(), 
                key=lambda x: (x.priority, -x.success_probability)
            )
            
            final_actions = sorted_actions[:5]
            
            logger.info(f"Prioritized and deduplicated: {len(final_actions)} final actions")
            return final_actions
            
        except Exception as e:
            logger.error(f"Error prioritizing actions: {e}")
            return actions

    async def save_healing_plan(self, healing_plan: HealingPlan):
        try:
            plan_file = self.healing_plans_dir / f"{healing_plan.plan_id}.json"
            
            plan_data = {
                'plan_id': healing_plan.plan_id,
                'anomaly_id': healing_plan.anomaly_id,
                'node_id': healing_plan.node_id,
                'severity': healing_plan.severity,
                'generated_timestamp': healing_plan.generated_timestamp,
                'total_estimated_duration': healing_plan.total_estimated_duration,
                'confidence': healing_plan.confidence,
                'requires_approval': healing_plan.requires_approval,
                'healing_actions': [asdict(action) for action in healing_plan.healing_actions]
            }
            
            with open(plan_file, 'w') as f:
                json.dump(plan_data, f, indent=2, default=str)
            
            logger.info(f"Healing plan saved: {plan_file}")
            
        except Exception as e:
            logger.error(f"Error saving healing plan: {e}")

    async def send_healing_responses(self, anomaly_alert: AnomalyAlert, healing_plan: HealingPlan):
        try:
            await self.send_healing_response_to_calculation_agent(anomaly_alert, healing_plan)
            await self.send_healing_plan_to_orchestrator(healing_plan)
            
            self.comm_metrics['responses_sent'] += 1
            
        except Exception as e:
            logger.error(f"Error sending healing responses: {e}")
            self.comm_metrics['failed_operations'] += 1

    async def send_healing_response_to_calculation_agent(self, anomaly_alert: AnomalyAlert, healing_plan: HealingPlan):
        try:
            response = {
                'message_type': 'healing_response',
                'timestamp': datetime.now().isoformat(),
                'source_agent': 'healing_agent',
                'target_agent': 'calculation_agent',
                'original_message_id': anomaly_alert.message_id,
                'anomaly_id': healing_plan.anomaly_id,
                'healing_plan': {
                    'plan_id': healing_plan.plan_id,
                    'node_id': healing_plan.node_id,
                    'severity': healing_plan.severity,
                    'confidence': healing_plan.confidence,
                    'total_estimated_duration': healing_plan.total_estimated_duration,
                    'healing_actions': [
                        {
                            'action_type': action.action_type,
                            'description': action.description,
                            'priority': action.priority,
                            'estimated_duration': action.estimated_duration
                        }
                        for action in healing_plan.healing_actions
                    ]
                },
                'response_metadata': {
                    'confidence': healing_plan.confidence,
                    'requires_approval': healing_plan.requires_approval
                }
            }
            
            await self.mcp_publisher.send_json(response)
            logger.info(f"Healing response sent to Calculation Agent: {healing_plan.plan_id}")
            
        except Exception as e:
            logger.error(f"Failed to send healing response to Calculation Agent: {e}")

    async def send_healing_plan_to_orchestrator(self, healing_plan: HealingPlan):
        try:
            orchestrator_message = {
                'message_type': 'healing_plan',
                'timestamp': datetime.now().isoformat(),
                'source_agent': 'healing_agent',
                'target_agent': 'orchestration_agent',
                'healing_plan_data': {
                    'plan_id': healing_plan.plan_id,
                    'anomaly_id': healing_plan.anomaly_id,
                    'node_id': healing_plan.node_id,
                    'severity': healing_plan.severity,
                    'generated_timestamp': healing_plan.generated_timestamp,
                    'confidence': healing_plan.confidence,
                    'requires_approval': healing_plan.requires_approval,
                    'total_estimated_duration': healing_plan.total_estimated_duration,
                    'healing_actions': [asdict(action) for action in healing_plan.healing_actions]
                },
                'execution_metadata': {
                    'auto_execute': not healing_plan.requires_approval,
                    'priority_level': healing_plan.severity,
                    'estimated_completion_time': datetime.now().timestamp() + healing_plan.total_estimated_duration
                }
            }
            
            await self.orchestrator_publisher.send_json(orchestrator_message)
            logger.info(f"Healing plan sent to Orchestrator: {healing_plan.plan_id}")
            
        except Exception as e:
            logger.error(f"Failed to send healing plan to Orchestrator: {e}")

    async def monitor_healing_performance(self):
        logger.info("Starting performance monitoring...")
        
        while self.is_running:
            try:
                await asyncio.sleep(60)
                
                avg_processing_time = np.mean(self.processing_times) if self.processing_times else 0
                success_rate = len([t for t in self.processing_times if t < 300]) / len(self.processing_times) if self.processing_times else 0
                
                logger.info(f"Performance Summary:")
                logger.info(f"  Alerts Received: {self.comm_metrics['alerts_received']}")
                logger.info(f"  Healing Plans Generated: {self.comm_metrics['healing_plans_generated']}")
                logger.info(f"  Responses Sent: {self.comm_metrics['responses_sent']}")
                logger.info(f"  Failed Operations: {self.comm_metrics['failed_operations']}")
                logger.info(f"  Avg Processing Time: {avg_processing_time:.2f}s")
                logger.info(f"  Success Rate: {success_rate:.2%}")
                
                if len(self.processing_times) > 100:
                    self.processing_times = self.processing_times[-100:]
                    
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")

    async def generate_periodic_reports(self):
        logger.info("Starting periodic report generation...")
        
        while self.is_running:
            try:
                await asyncio.sleep(3600)
                
                report = {
                    'report_timestamp': datetime.now().isoformat(),
                    'reporting_period': '1 hour',
                    'communication_metrics': self.comm_metrics.copy(),
                    'performance_metrics': {
                        'avg_processing_time': np.mean(self.processing_times) if self.processing_times else 0,
                        'total_processing_attempts': len(self.processing_times),
                        'active_healing_plans': len(self.active_healing_plans),
                        'success_rate': (
                            (self.comm_metrics['healing_plans_generated'] /
                             max(self.comm_metrics['alerts_received'], 1)) * 100
                        )
                    },
                    'active_healing_plans': [
                        {
                            'plan_id': plan.plan_id,
                            'node_id': plan.node_id,
                            'severity': plan.severity,
                            'generated_timestamp': plan.generated_timestamp
                        }
                        for plan in self.active_healing_plans.values()
                    ]
                }
                
                report_file = self.healing_reports_dir / f"healing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(report_file, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
                
                logger.info(f"Periodic report generated: {report_file}")
                
            except Exception as e:
                logger.error(f"Error generating periodic report: {e}")

    async def periodic_knowledge_refresh(self):
        logger.info("Starting periodic knowledge refresh...")
        
        while self.is_running:
            try:
                await asyncio.sleep(7200)  # Refresh every 2 hours
                
                logger.info("Refreshing knowledge from APIs...")
                await self._load_rag_data()
                logger.info("Knowledge refresh completed")
                
            except Exception as e:
                logger.error(f"Error in periodic knowledge refresh: {e}")

    async def cleanup(self):
        try:
            self.is_running = False
            
            if self.a2a_subscriber:
                self.a2a_subscriber.close()
            if self.mcp_publisher:
                self.mcp_publisher.close()
            if self.orchestrator_publisher:
                self.orchestrator_publisher.close()
            if self.context:
                self.context.term()
            if self.db_manager:
                self.db_manager.close()
            
            final_report = {
                'shutdown_timestamp': datetime.now().isoformat(),
                'final_metrics': self.comm_metrics.copy(),
                'total_active_plans': len(self.active_healing_plans),
                'avg_processing_time': np.mean(self.processing_times) if self.processing_times else 0
            }
            
            final_report_file = self.healing_reports_dir / f"final_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(final_report_file, 'w') as f:
                json.dump(final_report, f, indent=2, default=str)
            
            logger.info("Enhanced Healing Agent cleanup completed")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    agent = EnhancedHealingAgent()
    
    try:
        print('Enhanced Healing Agent with API-driven knowledge starting...')
        print('Listening for anomaly alerts from Calculation Agent')
        print('RAG-enhanced healing with API-loaded database knowledge')
        print('Multi-strategy healing plan generation')
        print('Prometheus metrics enabled on port 8004')
        print(f'Healing plans: {agent.healing_plans_dir}')
        print(f'Reports: {agent.healing_reports_dir}')
        print('API Configuration via environment variables or knowledge_api_config.json')
        
        await agent.start_with_enhanced_communication()
        
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        await agent.cleanup()

if __name__ == '__main__':
    asyncio.run(main())