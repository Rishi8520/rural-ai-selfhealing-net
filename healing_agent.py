# --- File: healing_agent.py ---
import asyncio
import json
import numpy as np
import zmq.asyncio
import sys
import time
import logging
# New imports for enhancements
import os
from dotenv import load_dotenv # For loading environment variables from .env
import google.generativeai as genai # For Gemini API
import google.api_core.exceptions # For Gemini API specific exceptions
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type # For robust error handling
from sentence_transformers import SentenceTransformer # For advanced RAG
import faiss # For efficient similarity search with dense vectors
import sqlite3 # Added for database operations
import platform # For Windows-specific event loop policy

# Set Windows-specific event loop policy for ZeroMQ compatibility
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- ADDED CODE FOR DEBUGGING GOOGLE_API_KEY ---
api_key_status = os.getenv("GOOGLE_API_KEY")
if api_key_status:
    logger.info(f"GOOGLE_API_KEY is loaded: {api_key_status[:5]}...{api_key_status[-5:]}")
else:
    logger.error("GOOGLE_API_KEY is NOT loaded. Please ensure it's set or in your .env file.")

# --- Database Manager Class ---
class DatabaseManager:
    def __init__(self, db_path='rag_knowledge_base.db'):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self._connect()
        self._ensure_tables() # Ensure tables exist when connected

    def _connect(self):
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            logger.info(f"Connected to database: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def _ensure_tables(self):
        """Ensures that necessary tables exist in the database, including the new UserFeedback table."""
        try:
            # SQL statements to create tables if they don't exist
            self.cursor.executescript("""
                CREATE TABLE IF NOT EXISTS NetworkLayers (
                    layer_id INTEGER PRIMARY KEY,
                    layer_name VARCHAR(100) NOT NULL,
                    description TEXT
                );

                CREATE TABLE IF NOT EXISTS NodeTypes (
                    node_type_id INTEGER PRIMARY KEY,
                    node_type_name VARCHAR(100) NOT NULL,
                    description TEXT
                );

                CREATE TABLE IF NOT EXISTS Nodes (
                    node_id VARCHAR(50) PRIMARY KEY,
                    node_name VARCHAR(100),
                    layer_id INTEGER,
                    node_type_id INTEGER,
                    ip_address VARCHAR(50),
                    location VARCHAR(200),
                    status VARCHAR(20),
                    FOREIGN KEY (layer_id) REFERENCES NetworkLayers(layer_id),
                    FOREIGN KEY (node_type_id) REFERENCES NodeTypes(node_type_id)
                );

                CREATE TABLE IF NOT EXISTS Links (
                    link_id VARCHAR(50) PRIMARY KEY,
                    source_node_id VARCHAR(50) NOT NULL,
                    target_node_id VARCHAR(50) NOT NULL,
                    link_type VARCHAR(50),
                    bandwidth_gbps REAL,
                    latency_ms REAL,
                    status VARCHAR(20),
                    FOREIGN KEY (source_node_id) REFERENCES Nodes(node_id),
                    FOREIGN KEY (target_node_id) REFERENCES Nodes(node_id)
                );

                CREATE TABLE IF NOT EXISTS Anomalies (
                    anomaly_id VARCHAR(50) PRIMARY KEY,
                    timestamp INTEGER NOT NULL,
                    node_id VARCHAR(50) NOT NULL,
                    severity VARCHAR(50),
                    description TEXT,
                    FOREIGN KEY (node_id) REFERENCES Nodes(node_id)
                );

                CREATE TABLE IF NOT EXISTS TrafficFlows (
                    flow_id VARCHAR(50) PRIMARY KEY,
                    source_node_id VARCHAR(50) NOT NULL,
                    destination_node_id VARCHAR(50) NOT NULL,
                    bandwidth_usage_gbps REAL,
                    flow_type VARCHAR(50),
                    FOREIGN KEY (source_node_id) REFERENCES Nodes(node_id),
                    FOREIGN KEY (destination_node_id) REFERENCES Nodes(node_id)
                );

                CREATE TABLE IF NOT EXISTS Policies (
                    policy_id INTEGER PRIMARY KEY,
                    policy_name VARCHAR(100) NOT NULL,
                    policy_type VARCHAR(50),
                    description TEXT
                );

                CREATE TABLE IF NOT EXISTS RecoveryTactics (
                    tactic_id INTEGER PRIMARY KEY,
                    tactic_name VARCHAR(100) NOT NULL,
                    description TEXT,
                    estimated_time_seconds INTEGER,
                    priority VARCHAR(50)
                );

                -- NEW TABLE FOR USER FEEDBACK
                CREATE TABLE IF NOT EXISTS UserFeedback (
                    feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    anomaly_id VARCHAR(50) NOT NULL,
                    timestamp INTEGER NOT NULL,
                    proposed_plan TEXT, -- Store JSON as text
                    user_decision VARCHAR(20) NOT NULL, -- 'approved', 'disapproved', 'other'
                    user_input TEXT, -- Raw text input from user
                    classified_intent TEXT, -- LLM-classified intent of user_input
                    extracted_entities TEXT, -- LLM-extracted entities from user_input (JSON as text)
                    FOREIGN KEY (anomaly_id) REFERENCES Anomalies(anomaly_id)
                );
            """)
            self.conn.commit()
            logger.info("Database tables ensured (created if not exist).")
        except sqlite3.Error as e:
            logger.error(f"Error ensuring database tables: {e}")
            self.conn.rollback()
            raise

    def _execute_query(self, query, params=()):
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
            return self.cursor
        except sqlite3.Error as e:
            logger.error(f"Database query failed: {e}")
            self.conn.rollback()
            raise

    def load_initial_data(self, data_files):
        """
        Loads initial data from SQL data files into the database.
        It handles reference data and larger datasets.
        """
        try:
            # Insert reference data directly, ensuring it's only added once
            # This is crucial for tables like NetworkLayers and NodeTypes that might be small
            # and required before other tables.
            self.cursor.execute("SELECT COUNT(*) FROM NetworkLayers")
            if self.cursor.fetchone()[0] == 0:
                self.cursor.executescript("""
                    INSERT INTO NetworkLayers VALUES (1, 'Core', 'High-capacity backbone routing and switching');
                    INSERT INTO NetworkLayers VALUES (2, 'Distribution', 'Regional traffic aggregation and distribution');
                    INSERT INTO NetworkLayers VALUES (3, 'Access', 'End-user connection points and edge access');
                """)
                logger.info("NetworkLayers reference data inserted.")

            self.cursor.execute("SELECT COUNT(*) FROM NodeTypes")
            if self.cursor.fetchone()[0] == 0:
                self.cursor.executescript("""
                    INSERT INTO NodeTypes VALUES (1, 'Core_Router', 'High-performance core network router');
                    INSERT INTO NodeTypes VALUES (2, 'Distribution_Switch', 'Regional distribution switch');
                    INSERT INTO NodeTypes VALUES (3, 'Access_Point', 'End-user access point');
                """)
                logger.info("NodeTypes reference data inserted.")

            self.cursor.execute("SELECT COUNT(*) FROM Policies")
            if self.cursor.fetchone()[0] == 0:
                self.cursor.executescript("""
                    INSERT INTO Policies VALUES (1, 'FCC_Rural_Broadband_Policy', 'Compliance', 'FCC regulations for rural broadband infrastructure');
                """)
                logger.info("Policies reference data inserted.")

            self.cursor.execute("SELECT COUNT(*) FROM RecoveryTactics")
            if self.cursor.fetchone()[0] == 0:
                self.cursor.executescript("""
                    INSERT INTO RecoveryTactics VALUES (1, 'Emergency_Reroute', 'Immediately reroute traffic through alternative paths', 30, 'medium');
                    INSERT INTO RecoveryTactics VALUES (2, 'Physical_Repair', 'Dispatch repair team for physical fiber restoration', 7200, 'low');
                    INSERT INTO RecoveryTactics VALUES (3, 'Backup_Power_Switch', 'Switch to backup power source', 120, 'medium');
                """)
                self.conn.commit() # Commit after all reference data inserts
                logger.info("RecoveryTactics reference data inserted.")
            self.conn.commit() # Commit any pending reference data inserts

            # Load data from individual files (Nodes, Links, Anomalies, TrafficFlows)
            # Only load if the respective table is empty to avoid duplicate data inserts
            for data_file in data_files:
                table_name_map = {
                    'rag_training_database_nodes.sql': 'Nodes',
                    'rag_training_database_links.sql': 'Links',
                    'rag_training_database_anomalies.sql': 'Anomalies',
                    'rag_training_database_traffic_flows.sql': 'TrafficFlows',
                    'rag_training_database_policies.sql': 'Policies', # Include these for completeness, though they are also in direct inserts
                    'rag_training_database_recovery_tactics.sql': 'RecoveryTactics' # Same as above
                }

                # Determine the actual table name from the file path
                table_name = None
                for file_path_key, mapped_table_name in table_name_map.items():
                    if data_file.endswith(file_path_key):
                        table_name = mapped_table_name
                        break

                if not table_name:
                    logger.warning(f"Skipping unknown data file: {data_file}")
                    continue

                try:
                    self.cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    if self.cursor.fetchone()[0] == 0:
                        with open(data_file, 'r') as f:
                            data_sql = f.read()
                            self.cursor.executescript(data_sql)
                            self.conn.commit()
                            logger.info(f"Data loaded from {data_file} into {table_name}.")
                    else:
                        logger.info(f"Table '{table_name}' already contains data. Skipping loading from {data_file}.")
                except sqlite3.Error as e:
                    logger.error(f"Error loading data from {data_file} into {table_name}: {e}")
                    self.conn.rollback()


            logger.info("Initial database data loading process completed.")

        except FileNotFoundError as e:
            logger.error(f"Error loading initial data: File not found - {e}")
        except sqlite3.Error as e:
            logger.error(f"Error executing SQL during data load: {e}")
            self.conn.rollback()
        except Exception as e:
            logger.error(f"An unexpected error occurred during data loading: {e}")

    def fetch_all_nodes(self):
        """Fetches all nodes from the Nodes table."""
        try:
            self.cursor.execute("""
                SELECT n.node_id, n.node_name, nl.layer_name, nt.node_type_name, n.ip_address, n.location, n.status
                FROM Nodes n
                JOIN NetworkLayers nl ON n.layer_id = nl.layer_id
                JOIN NodeTypes nt ON n.node_type_id = nt.node_type_id
            """)
            columns = [description[0] for description in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error fetching all nodes: {e}")
            return []

    def fetch_node_by_id(self, node_id):
        """Fetches a single node by its ID."""
        try:
            self.cursor.execute("""
                SELECT n.node_id, n.node_name, nl.layer_name, nt.node_type_name, n.ip_address, n.location, n.status
                FROM Nodes n
                JOIN NetworkLayers nl ON n.layer_id = nl.layer_id
                JOIN NodeTypes nt ON n.node_type_id = nt.node_type_id
                WHERE n.node_id = ?
            """, (node_id,))
            columns = [description[0] for description in self.cursor.description]
            row = self.cursor.fetchone()
            return dict(zip(columns, row)) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error fetching node by ID {node_id}: {e}")
            return None

    def fetch_links_for_node(self, node_id):
        """Fetches links connected to a given node."""
        try:
            self.cursor.execute("""
                SELECT link_id, source_node_id, target_node_id, link_type, bandwidth_gbps, latency_ms, status
                FROM Links
                WHERE source_node_id = ? OR target_node_id = ?
            """, (node_id, node_id))
            columns = [description[0] for description in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error fetching links for node {node_id}: {e}")
            return []

    def fetch_anomalies_for_node(self, node_id):
        """Fetches anomalies associated with a given node."""
        try:
            self.cursor.execute("""
                SELECT anomaly_id, timestamp, node_id, severity, description
                FROM Anomalies
                WHERE node_id = ?
                ORDER BY timestamp DESC
                LIMIT 5
            """, (node_id,)) # Limit to last 5 anomalies for brevity in RAG
            columns = [description[0] for description in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error fetching anomalies for node {node_id}: {e}")
            return []

    def fetch_traffic_flows_for_node(self, node_id):
        """Fetches traffic flows involving a given node as source or destination."""
        try:
            self.cursor.execute("""
                SELECT flow_id, source_node_id, destination_node_id, bandwidth_usage_gbps, flow_type
                FROM TrafficFlows
                WHERE source_node_id = ? OR destination_node_id = ?
                LIMIT 5
            """, (node_id, node_id)) # Limit to last 5 flows for brevity
            columns = [description[0] for description in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error fetching traffic flows for node {node_id}: {e}")
            return []

    def fetch_policies_for_node(self, node_id):
        """Fetches policies applicable to a given node."""
        # This is a simplified example; in a real system, policy application might be more complex.
        # Here, we assume a direct mapping or that all policies are relevant.
        try:
            self.cursor.execute("""
                SELECT policy_id, policy_name, policy_type, description
                FROM Policies
                LIMIT 5
            """) # Fetch some policies, assuming they might be generally relevant or specific to nodes
            columns = [description[0] for description in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error fetching policies for node {node_id}: {e}")
            return []

    def fetch_recovery_tactics_for_node(self, node_id):
        """Fetches potential recovery tactics relevant to a given node (simplified)."""
        try:
            self.cursor.execute("""
                SELECT tactic_id, tactic_name, description, estimated_time_seconds, priority
                FROM RecoveryTactics
                LIMIT 5
            """) # Fetch some tactics, assuming general relevance or specific to nodes
            columns = [description[0] for description in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error fetching recovery tactics for node {node_id}: {e}")
            return []

    def store_user_feedback(self, anomaly_id, proposed_plan, user_decision, user_input, classified_intent, extracted_entities):
        """
        Stores user feedback into the UserFeedback table.
        """
        try:
            self.cursor.execute(
                """
                INSERT INTO UserFeedback (anomaly_id, timestamp, proposed_plan, user_decision, user_input, classified_intent, extracted_entities)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (anomaly_id, int(time.time()), json.dumps(proposed_plan), user_decision, user_input, classified_intent, json.dumps(extracted_entities))
            )
            self.conn.commit()
            logger.info(f"User feedback stored for anomaly {anomaly_id}. Decision: {user_decision}")
        except sqlite3.Error as e:
            logger.error(f"Error storing user feedback for anomaly {anomaly_id}: {e}")
            self.conn.rollback()
            raise

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed.")

# --- HealingAgent Class ---
class HealingAgent:
    def __init__(self, context, sub_socket_address_a2a, push_socket_address_mcp):
        self.context = context
        self.a2a_subscriber_socket = self.context.socket(zmq.SUB)
        self.a2a_subscriber_socket.connect(sub_socket_address_a2a)
        self.a2a_subscriber_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        self.mcp_push_socket = self.context.socket(zmq.PUSH)
        self.mcp_push_socket.connect(push_socket_address_mcp)
        self.llm = self._initialize_llm()
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Load pretrained SentenceTransformer: all-MiniLM-L6-v2")
        self.db_manager = DatabaseManager() # Initialize DatabaseManager
        self.rag_index = None
        self.rag_documents = []
        self._load_rag_data() # Load RAG data from database
        self.anomaly_queue = asyncio.Queue()
        self.in_progress_anomalies = {}
        self.processed_anomaly_ids = set()
        logger.info("LLM (Gemini) initialized successfully.")
        logger.info("Healing Agent started. Listening for anomalies...")


    def _initialize_llm(self):
        """Initializes the GenerativeModel with the API key."""
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            logger.error("GOOGLE_API_KEY not found in environment variables.")
            raise ValueError("GOOGLE_API_KEY is not set. Please set it in your .env file or environment.")
        genai.configure(api_key=google_api_key)
        # Use a model that supports function calling if needed, e.g., 'gemini-1.5-pro'
        # For general text generation, 'gemini-pro' is also suitable.
        return genai.GenerativeModel('gemini-pro')

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3),
           retry=retry_if_exception_type(google.api_core.exceptions.ResourceExhausted))
    async def _send_llm_request(self, prompt, temperature=0.7, max_output_tokens=1024):
        """Sends a request to the LLM with retry logic."""
        try:
            response = self.llm.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                ),
                safety_settings=[
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
            )
            # Access the text attribute if response.text is not directly available
            if hasattr(response, 'text'):
                return response.text
            elif hasattr(response, 'candidates') and response.candidates:
                # Assuming the first candidate's content.parts[0].text holds the response
                return response.candidates[0].content.parts[0].text
            else:
                logger.error(f"LLM response did not contain expected text content: {response}")
                return None
        except google.api_core.exceptions.ResourceExhausted as e:
            logger.warning(f"ResourceExhausted error from LLM, retrying: {e}")
            raise # Re-raise to trigger tenacity retry
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return None

    async def _handle_anomaly(self, anomaly_message):
        anomaly_id = anomaly_message.get('anomaly_id')
        if anomaly_id in self.processed_anomaly_ids:
            logger.info(f"Anomaly {anomaly_id} already processed. Skipping.")
            return

        if anomaly_id in self.in_progress_anomalies:
            logger.info(f"Anomaly {anomaly_id} is already being processed. Skipping duplicate.")
            return

        self.in_progress_anomalies[anomaly_id] = time.time()
        logger.info(f"Received anomaly: {anomaly_message}")

        node_id = anomaly_message.get('node_id')
        if not node_id:
            logger.error(f"Anomaly message {anomaly_id} missing 'node_id'. Cannot process.")
            del self.in_progress_anomalies[anomaly_id]
            return

        # Step 1: Contextualization using RAG
        context_info = self._get_rag_context(node_id, anomaly_message.get('description', ''))

        # Step 2: Anomaly Analysis and Healing Plan Generation with LLM
        prompt = self._construct_llm_prompt(anomaly_message, context_info)
        healing_plan_json = await self._send_llm_request(prompt)

        if healing_plan_json:
            try:
                healing_plan = json.loads(healing_plan_json)
                logger.info(f"Generated Healing Plan for {anomaly_id}: {healing_plan}")

                # --- NEW: User Confirmation Step ---
                print(f"\n--- PROPOSED HEALING PLAN for Anomaly {anomaly_id} ---")
                print(json.dumps(healing_plan, indent=2))
                user_response = input("Do you approve this plan? (yes/no/other input for feedback): ").strip().lower()

                if user_response == 'yes':
                    logger.info(f"User approved healing plan for anomaly {anomaly_id}. Sending to MCP.")
                    await self._send_to_mcp(healing_plan)
                    self.db_manager.store_user_feedback(anomaly_id, healing_plan, 'approved', 'User approved the plan.', None, None)
                    self.processed_anomaly_ids.add(anomaly_id) # Mark as processed
                else:
                    logger.info(f"User did not approve healing plan for anomaly {anomaly_id}. Processing feedback.")
                    await self._process_user_feedback(anomaly_message, healing_plan, user_response)
                    # We don't mark as processed if not approved, allowing for re-evaluation or manual intervention
                    # depending on the desired workflow after feedback.
                    # self.processed_anomaly_ids.add(anomaly_id) # Only uncomment if disapproved also means 'processed'
                # --- END NEW: User Confirmation Step ---

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse healing plan JSON for {anomaly_id}: {e}. Raw response: {healing_plan_json[:500]}...")
            except Exception as e:
                logger.error(f"An unexpected error occurred while processing healing plan for {anomaly_id}: {e}")
        else:
            logger.warning(f"No healing plan generated for anomaly {anomaly_id}.")

        del self.in_progress_anomalies[anomaly_id]

    async def _process_user_feedback(self, original_anomaly_message, proposed_healing_plan, user_raw_input):
        """
        Processes user feedback, classifying its intent and extracting entities,
        then stores it in the database. This is the 'intent translation' part for user feedback.
        """
        logger.info(f"User feedback received: '{user_raw_input}' for anomaly {original_anomaly_message.get('anomaly_id')}")

        classified_intent = "unclassified"
        extracted_entities = {}
        user_decision = "disapproved" # Default if not 'yes'

        if user_raw_input.lower() == 'no':
            user_decision = "disapproved"
            classified_intent = "explicit_disapproval"
            logger.info("User explicitly disapproved the plan.")
        else:
            user_decision = "other_input"
            # Use LLM to classify intent and extract entities from user's free-form input
            feedback_prompt = (
                f"You are an AI assistant tasked with understanding user feedback on proposed network healing plans. "
                f"Given the user's input, classify its primary intent and extract any relevant entities.\n\n"
                f"Possible Intents:\n"
                f"- 'correction': User suggests a specific change or alternative action.\n"
                f"- 'request_more_info': User wants more details or context.\n"
                f"- 'new_information': User provides new data relevant to the anomaly.\n"
                f"- 'general_disapproval': User disapproves without a specific alternative.\n"
                f"- 'other': Any other type of input.\n\n"
                f"Extract Entities (if applicable): node_id, link_id, alternative_tactic, desired_info, etc.\n\n"
                f"Original Anomaly: {original_anomaly_message.get('description')}\n"
                f"Proposed Plan: {json.dumps(proposed_healing_plan)}\n"
                f"User Input: '{user_raw_input}'\n\n"
                f"Provide your response as a JSON object with 'intent' and 'entities' (an object).\n"
                f"Example: {{ \"intent\": \"correction\", \"entities\": {{ \"alternative_tactic\": \"restart_device_firmware\" }} }}"
            )

            feedback_classification_json = await self._send_llm_request(feedback_prompt)
            if feedback_classification_json:
                try:
                    feedback_data = json.loads(feedback_classification_json)
                    classified_intent = feedback_data.get('intent', 'unclassified')
                    extracted_entities = feedback_data.get('entities', {})
                    logger.info(f"User feedback classified as intent: '{classified_intent}' with entities: {extracted_entities}")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse feedback classification JSON: {e}. Raw response: {feedback_classification_json[:500]}")
                    classified_intent = "parse_error"
                    extracted_entities = {"raw_json_error": feedback_classification_json}
            else:
                logger.warning("LLM failed to classify user feedback.")
                classified_intent = "llm_failure"

        # Store the feedback in the database
        try:
            self.db_manager.store_user_feedback(
                original_anomaly_message.get('anomaly_id'),
                proposed_healing_plan,
                user_decision,
                user_raw_input,
                classified_intent,
                extracted_entities
            )
        except Exception as e:
            logger.error(f"Failed to store user feedback: {e}")


    async def _send_to_mcp(self, healing_plan):
        """Sends the healing plan to the MCP via ZeroMQ PUSH socket."""
        try:
            message = json.dumps(healing_plan).encode('utf-8')
            await self.mcp_push_socket.send(message)
            logger.info(f"Healing plan sent to MCP for anomaly: {healing_plan.get('anomaly_id')}")
        except Exception as e:
            logger.error(f"Failed to send healing plan to MCP: {e}")

    def _get_rag_context(self, node_id, anomaly_description):
        """
        Retrieves relevant context from the RAG knowledge base using embeddings.
        """
        if not self.rag_index or not self.rag_documents:
            logger.warning("RAG index not built or documents empty. Providing limited context.")
            # Fallback to basic node info if RAG is not available
            node_info = self.db_manager.fetch_node_by_id(node_id)
            if node_info:
                return f"Basic node information for {node_id}: {node_info}"
            return "No additional context available."

        query_text = f"Information about node {node_id} and anomaly: {anomaly_description}"
        query_embedding = self.embedding_model.encode([query_text]).astype('float32')

        D, I = self.rag_index.search(query_embedding, k=3) # Search for top 3 relevant documents

        context_docs = [self.rag_documents[i] for i in I[0] if i != -1]

        if context_docs:
            logger.info(f"Retrieved {len(context_docs)} RAG context documents for node {node_id}.")
            return "\n\n".join(context_docs)
        else:
            logger.info(f"No specific RAG context found for node {node_id}. Fetching basic node info.")
            node_info = self.db_manager.fetch_node_by_id(node_id)
            if node_info:
                return f"Basic node information for {node_id}: {node_info}"
            return "No relevant context found in RAG."

    def _construct_llm_prompt(self, anomaly_message, context_info):
        """
        Constructs a detailed prompt for the LLM based on the anomaly and RAG context.
        """
        prompt = (
            f"You are an AI-powered network healing agent. Your task is to analyze network anomalies "
            f"and propose a detailed healing plan in JSON format. "
            f"The goal is to restore network health with minimal disruption.\n\n"
            f"Anomaly Details:\n"
            f"Anomaly ID: {anomaly_message.get('anomaly_id')}\n"
            f"Timestamp: {anomaly_message.get('timestamp')}\n"
            f"Node ID: {anomaly_message.get('node_id')}\n"
            f"Severity: {anomaly_message.get('severity')}\n"
            f"Description: {anomaly_message.get('description')}\n\n"
            f"Relevant Network Context (RAG):\n"
            f"{context_info}\n\n"
            f"Based on the anomaly details and network context, generate a healing plan. "
            f"The plan should be a JSON object with the following structure:\n"
            f"{{\n"
            f"  \"anomaly_id\": \"<anomaly_id_from_message>\",\n"
            f"  \"healing_actions\": [\n"
            f"    {{\n"
            f"      \"action_id\": \"<unique_action_id>\",\n"
            f"      \"type\": \"<type_of_action>\", (e.g., 'reroute_traffic', 'restart_device', 'escalate_human', 'apply_policy')\n"
            f"      \"target_node_id\": \"<node_id_affected_by_action>\", (Optional, if action is node-specific)\n"
            f"      \"target_link_id\": \"<link_id_affected_by_action>\", (Optional, if action is link-specific)\n"
            f"      \"description\": \"<brief_description_of_action>\",\n"
            f"      \"priority\": \"<priority>\", (e.g., 'high', 'medium', 'low')\n"
            f"      \"estimated_time_seconds\": <estimated_time_in_seconds> (integer),\n"
            f"      \"reasoning\": \"<brief_explanation_for_this_action>\"\n"
            f"    }}\n"
            f"    // ... potentially more actions\n"
            f"  ],\n"
            f"  \"overall_strategy\": \"<brief_summary_of_the_overall_healing_approach>\"\n"
            f"}}\n\n"
            f"Ensure the JSON is valid and directly parsable. Do not include any additional text or formatting outside the JSON object."
        )
        return prompt

    def _load_rag_data(self):
        """
        Loads knowledge base data from the database and builds the RAG index.
        """
        logger.info("Rebuilding RAG index from database...")

        # --- MODIFIED CALL TO LOAD INITIAL DATA ---
        # schema_file is no longer needed as schema is created in _ensure_tables
        data_files = [
            'rag_training_database_nodes.sql',
            'rag_training_database_links.sql',
            'rag_training_database_anomalies.sql',
            'rag_training_database_traffic_flows.sql',
            'rag_training_database_policies.sql',
            'rag_training_database_recovery_tactics.sql'
        ]
        try:
            self.db_manager.load_initial_data(data_files)
        except Exception as e:
            logger.error(f"Failed to load initial database data: {e}")
            # Decide if you want to stop or continue with an empty RAG
            # For now, we continue and the RAG will be empty, leading to the warning below.
        # --- END OF MODIFIED CALL ---

        try:
            nodes = self.db_manager.fetch_all_nodes()
            if not nodes:
                logger.warning("No knowledge entries found in the database to build RAG index. RAG will not be effective without knowledge.")
                return

            self.rag_documents = []
            for node in nodes:
                node_id = node['node_id']
                # Construct a comprehensive document for each node
                doc_parts = [
                    f"Node ID: {node['node_id']}",
                    f"Node Name: {node['node_name']}",
                    f"Layer: {node['layer_name']}",
                    f"Type: {node['node_type_name']}",
                    f"IP Address: {node['ip_address']}",
                    f"Location: {node['location']}",
                    f"Status: {node['status']}"
                ]

                # Fetch and add related information (links, anomalies, policies, traffic flows, recovery tactics)
                links = self.db_manager.fetch_links_for_node(node_id)
                if links:
                    doc_parts.append("Connected Links:")
                    for link in links:
                        doc_parts.append(f"  - Link ID: {link['link_id']}, From: {link['source_node_id']}, To: {link['target_node_id']}, Type: {link['link_type']}, Bandwidth: {link['bandwidth_gbps']} Gbps, Latency: {link['latency_ms']} ms, Status: {link['status']}")

                anomalies = self.db_manager.fetch_anomalies_for_node(node_id)
                if anomalies:
                    doc_parts.append("Known Anomalies:")
                    for anomaly in anomalies:
                        doc_parts.append(f"  - Anomaly ID: {anomaly['anomaly_id']}, Timestamp: {anomaly['timestamp']}, Severity: {anomaly['severity']}, Description: {anomaly['description']}")

                traffic_flows = self.db_manager.fetch_traffic_flows_for_node(node_id)
                if traffic_flows:
                    doc_parts.append("Associated Traffic Flows:")
                    for flow in traffic_flows:
                        doc_parts.append(f"  - Flow ID: {flow['flow_id']}, Source: {flow['source_node_id']}, Destination: {flow['destination_node_id']}, Bandwidth: {flow['bandwidth_usage_gbps']} Gbps, Type: {flow['flow_type']}")

                policies = self.db_manager.fetch_policies_for_node(node_id)
                if policies:
                    doc_parts.append("Applicable Policies:")
                    for policy in policies:
                        doc_parts.append(f"  - Policy ID: {policy['policy_id']}, Name: {policy['policy_name']}, Type: {policy['policy_type']}, Description: {policy['description']}")

                recovery_tactics = self.db_manager.fetch_recovery_tactics_for_node(node_id)
                if recovery_tactics:
                    doc_parts.append("Potential Recovery Tactics:")
                    for tactic in recovery_tactics:
                        doc_parts.append(f"  - Tactic ID: {tactic['tactic_id']}, Name: {tactic['tactic_name']}, Description: {tactic['description']}, Est. Time: {tactic['estimated_time_seconds']}s, Priority: {tactic['priority']}")

                self.rag_documents.append(" ".join(doc_parts))

            # Generate embeddings and build FAISS index
            if self.rag_documents:
                logger.info(f"Generating embeddings for {len(self.rag_documents)} RAG documents...")
                document_embeddings = self.embedding_model.encode(self.rag_documents, show_progress_bar=True)
                self.rag_index = faiss.IndexFlatL2(document_embeddings.shape[1])
                self.rag_index.add(np.array(document_embeddings).astype('float32'))
                logger.info("RAG index built successfully.")
            else:
                logger.warning("No documents to build RAG index after fetching from database.")

        except Exception as e:
            logger.error(f"Error rebuilding RAG index: {e}")

    async def start(self):
        """Starts the anomaly listening and processing loop."""
        logger.info("Starting Healing Agent anomaly listener...")
        await self._listen_for_anomalies()

    async def _listen_for_anomalies(self):
        """Listens for anomaly messages from the A2A channel."""
        while True:
            try:
                message = await self.a2a_subscriber_socket.recv_json()
                logger.debug(f"Raw anomaly message received: {message}")
                if 'anomaly_id' in message:
                    await self._handle_anomaly(message)
                else:
                    logger.warning(f"Received message without 'anomaly_id': {message}")
            except zmq.Again:
                # No message received yet, continue listening
                await asyncio.sleep(0.1) # Small delay to prevent busy-waiting
            except Exception as e:
                logger.exception(f"Error receiving anomaly message: {e}")


# --- Main execution for standalone testing ---
async def main():
    # Define socket addresses
    test_sub_address_a2a = "tcp://127.0.0.1:5556"
    test_push_address_mcp = "tcp://127.0.0.1:5558"

    # Create a ZeroMQ context and Healing Agent instance
    # For standalone testing, create a local context
    local_context = zmq.asyncio.Context()
    healing_agent = HealingAgent(
        context=local_context, # Pass local context for standalone
        sub_socket_address_a2a=test_sub_address_a2a,
        push_socket_address_mcp=test_push_address_mcp
    )

    try:
        await healing_agent.start() # Await the start method
    except KeyboardInterrupt:
        logger.info("\nHealing Agent standalone test stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logger.exception(f"An unhandled exception occurred during Healing Agent runtime: {e}")
    finally:
        # Ensure cleanup ZeroMQ context and sockets on shutdown
        if healing_agent.a2a_subscriber_socket:
            healing_agent.a2a_subscriber_socket.close()
            logger.info("A2A subscriber socket closed.")
        if healing_agent.mcp_push_socket:
            healing_agent.mcp_push_socket.close()
            logger.info("MCP push socket closed.")
        if healing_agent.db_manager:
            healing_agent.db_manager.close()
        if local_context:
            local_context.term()
            logger.info("ZeroMQ context terminated.")
        sys.exit(0)


if __name__ == '__main__':
    asyncio.run(main())