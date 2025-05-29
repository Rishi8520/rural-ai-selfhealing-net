# --- File: healing_agent.py ---
import asyncio
import json
import numpy as np
import zmq.asyncio
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import sys # For sys.exit()
import time # For time.time() in timestamps

# --- Placeholder for RAG Knowledge Base ---
# This knowledge base is structured per node, allowing for contextual retrieval.
# In a real system, this would be loaded from a persistent database or configuration files.
NODE_KNOWLEDGE_BASE = {
    "node_1": [
        {"doc_id": "doc_1_1", "content": "Node 1 is a core router. Common issues: high latency, CPU spikes. Healing: restart interface, check routing table, verify BGP sessions."},
        {"doc_id": "doc_1_2", "content": "Node 1 firmware update policy: quarterly. Downtime window: 2 AM - 4 AM UTC. Critical service: VoIP."},
        {"doc_id": "doc_1_3", "content": "Past incident: Node 1 packet loss due to faulty transceiver. Resolution: Replace transceiver, update firmware. Check optical power levels."},
    ],
    "node_2": [
        {"doc_id": "doc_2_1", "content": "Node 2 is an edge switch. Common issues: port errors, signal degradation. Healing: disable/enable port, check cable, inspect SFP module."},
        {"doc_id": "doc_2_2", "content": "Node 2 is part of VoIP cluster. Prioritize voice traffic. Ensure QoS policies are applied."},
    ],
    # ... up to 50 nodes
}

# Populate for all 50 nodes for demonstration if not explicitly defined
for i in range(1, 51):
    if f"node_{i}" not in NODE_KNOWLEDGE_BASE:
        NODE_KNOWLEDGE_BASE[f"node_{i}"] = [
            {"doc_id": f"doc_{i}_1", "content": f"Node {i} is a general purpose network device. Standard healing procedures apply. High CPU usually indicates misconfiguration or excessive traffic. Check process list."},
            {"doc_id": f"doc_{i}_2", "content": f"Node {i} operates in a data center environment. Temperature control is critical. Power fluctuations should be immediately investigated. Verify redundant power supplies."},
            {"doc_id": f"doc_{i}_3", "content": f"Node {i} has a standard software stack. If memory usage is high, consider restarting non-critical services first."},
        ]

# --- Retrieval-Augmented Generation (RAG) Component ---
# This class handles retrieving relevant documents from the knowledge base.
class RetrievalAugmentedGenerator:
    """
    Manages the knowledge base and performs semantic search to retrieve relevant documents.
    Uses TF-IDF vectorization and cosine similarity for document retrieval.
    """
    def __init__(self, knowledge_base):
        """
        Initializes the RAG component with a given knowledge base.

        Args:
            knowledge_base (dict): A dictionary where keys are node IDs and values are lists
                                   of dictionaries, each containing 'doc_id' and 'content' for documents.
        """
        self.knowledge_base = knowledge_base
        self.vectorizers = {} # Stores TfidfVectorizer instance per node
        self.doc_contents = {} # Stores list of document content strings per node

        self._prepare_knowledge_base()

    def _prepare_knowledge_base(self):
        """
        Pre-processes the knowledge base for efficient retrieval.
        It fits a TfidfVectorizer for each node's documents.
        """
        print("RAG: Preparing knowledge base...")
        # Ensure a 'default' entry exists for nodes without specific KB
        if "default" not in self.knowledge_base:
            self.knowledge_base["default"] = [
                {"doc_id": "doc_default_1", "content": "General network troubleshooting: Check connectivity, power, and basic services. Consult logs for errors."},
                {"doc_id": "doc_default_2", "content": "If no specific node information, assume standard operating procedures for network devices."},
            ]

        for node_id, docs in self.knowledge_base.items():
            contents = [doc["content"] for doc in docs]
            if contents:
                vectorizer = TfidfVectorizer().fit(contents)
                self.vectorizers[node_id] = vectorizer
                self.doc_contents[node_id] = contents
            else:
                self.vectorizers[node_id] = None
                self.doc_contents[node_id] = []
        print("RAG: Knowledge base preparation complete.")

    def retrieve_context(self, node_id, query, top_k=3):
        """
        Retrieves relevant context documents from the knowledge base for a given node and query.
        Uses cosine similarity on TF-IDF vectors for retrieval.

        Args:
            node_id (str): The ID of the node for which to retrieve context.
            query (str): The query string (e.g., anomaly description) to search for.
            top_k (int): The number of top similar documents to retrieve.

        Returns:
            list: A list of strings, where each string is the content of a retrieved document.
        """
        # Fallback to a 'default' node if the specific node_id is not in the knowledge base
        actual_node_id = node_id
        if node_id not in self.vectorizers or not self.vectorizers[node_id]:
            actual_node_id = "default"
            print(f"RAG: Warning: No specific knowledge base found or prepared for node {node_id}. Using default context.")

        vectorizer = self.vectorizers.get(actual_node_id)
        docs = self.doc_contents.get(actual_node_id, [])

        if not vectorizer or not docs:
            print(f"RAG: Warning: No context available for node {actual_node_id}. Returning empty context.")
            return []

        # Transform the query and documents into TF-IDF vectors
        query_vec = vectorizer.transform([query])
        doc_vecs = vectorizer.transform(docs)

        # Calculate cosine similarity between query and all documents
        similarities = cosine_similarity(query_vec, doc_vecs).flatten()
        sorted_indices = similarities.argsort()[::-1] # Sort in descending order of similarity

        retrieved_docs = []
        for idx in sorted_indices[:top_k]:
            # Only include documents with a similarity score above a certain threshold
            if similarities[idx] > 0.1: # Threshold to filter less relevant documents
                retrieved_docs.append(docs[idx])
        return retrieved_docs

# --- Healing Agent Class ---
# This agent receives anomaly alerts, uses RAG to find context, and generates recommendations using an LLM.
class HealingAgent:
    """
    The Healing Agent receives anomaly alerts from the Calculation Agent,
    retrieves contextual information using RAG, generates detailed healing recommendations
    using an LLM (Gemini API), and pushes these recommendations to the Master Control Plane (MCP).
    """
    def __init__(self, sub_socket_address_a2a, push_socket_address_mcp):
        """
        Initializes the Healing Agent.

        Args:
            sub_socket_address_a2a (str): ZeroMQ address to subscribe to Calculation Agent's PUB socket.
            push_socket_address_mcp (str): ZeroMQ address to push healing recommendations to MCP's PULL socket.
        """
        self.sub_socket_address_a2a = sub_socket_address_a2a
        self.push_socket_address_mcp = push_socket_address_mcp

        self.context = zmq.asyncio.Context()
        
        # A2A communication: SUB socket to receive anomaly alerts from Calculation Agent (PUB)
        self.a2a_subscriber_socket = self.context.socket(zmq.SUB)
        self.a2a_subscriber_socket.connect(self.sub_socket_address_a2a)
        self.a2a_subscriber_socket.setsockopt_string(zmq.SUBSCRIBE, "") # Subscribe to all messages
        print(f"Healing Agent: A2A Subscriber connected to {self.sub_socket_address_a2a}")

        # MCP communication: PUSH socket to send healing recommendations to MCP (PULL)
        self.mcp_push_socket = self.context.socket(zmq.PUSH)
        self.mcp_push_socket.connect(self.push_socket_address_mcp) # Connect to MCP's PULL socket
        print(f"Healing Agent: MCP PUSH connected to {self.push_socket_address_mcp}")

        self.rag = RetrievalAugmentedGenerator(NODE_KNOWLEDGE_BASE)

    async def generate_recommendations_with_llm(self, anomaly_context, retrieved_docs):
        """
        Generates healing recommendations using a simulated Gemini API (gemini-2.0-flash),
        conditioned on the anomaly context and retrieved knowledge base documents.

        Args:
            anomaly_context (str): A JSON string detailing the anomaly report.
            retrieved_docs (list): A list of strings, each being a relevant document from the KB.

        Returns:
            str: The LLM-generated detailed recommendations.
        """
        prompt = self.build_prompt(anomaly_context, retrieved_docs)
        
        # --- Python-compatible placeholder for LLM call ---
        # This simulates the LLM's response without requiring an actual API key or network call.
        print("Healing Agent: Simulating LLM call to Gemini API...")
        await asyncio.sleep(1) # Simulate API latency

        try:
            # Parse anomaly_context safely
            anomaly_dict = json.loads(anomaly_context)
            node_id = anomaly_dict.get('node_id', 'N/A')
            severity_classification = anomaly_dict.get('severity_classification', 'issue')
            root_cause_indicators = anomaly_dict.get('root_cause_indicators', [])
            
            # Format root causes for the diagnosis
            root_causes_text = ', '.join([rc.get('feature', 'unknown') for rc in root_cause_indicators]) if root_cause_indicators else 'unknown factors'

            mock_diagnosis = f"Diagnosis for {node_id}: Possible {severity_classification} due to {root_causes_text}."
            mock_recommendations_list = [
                "Verify power supply and network cables.",
                "Check device logs for specific error codes.",
                "Consider a controlled restart of the affected service/device during off-peak hours.",
            ]
            mock_important_note = "Ensure all configurations are backed up before making changes."

            # Construct the mock LLM response similar to what a real LLM might return
            mock_llm_response_text = f"""
Diagnosis for {node_id}: Possible {severity_classification} due to {root_causes_text}.

Recommendations:
1. Verify power supply and network cables.
2. Check device logs for specific error codes.
3. Consider a controlled restart of the affected service/device during off-peak hours.
{f'4. Specific RAG Context: {"; ".join(retrieved_docs)}' if retrieved_docs else ''}

Important: {mock_important_note}
"""
            # Simulate the structure of a Gemini API response
            mock_llm_response = {
                "candidates": [{
                    "content": {
                        "parts": [{
                            "text": mock_llm_response_text
                        }]
                    }
                }]
            }

            result = mock_llm_response

            if result and result.get("candidates") and len(result["candidates"]) > 0 and \
               result["candidates"][0].get("content") and result["candidates"][0]["content"].get("parts") and \
               len(result["candidates"][0]["content"]["parts"]) > 0:
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                return text
            else:
                print(f"Healing Agent: LLM response structure unexpected: {result}")
                return "Failed to generate recommendations from LLM. Response structure unexpected."
        except json.JSONDecodeError:
            print(f"Healing Agent: Could not decode anomaly_context as JSON: {anomaly_context}")
            return "Failed to generate recommendations: Anomaly context was malformed."
        except Exception as e:
            print(f"Healing Agent: Error during simulated Gemini API call: {e}")
            return f"Failed to generate recommendations from LLM due to simulated API error: {e}"

    def build_prompt(self, anomaly_context, docs):
        """
        Constructs the prompt for the LLM, combining anomaly context and retrieved documents.

        Args:
            anomaly_context (str): A JSON string of the anomaly data.
            docs (list): List of retrieved knowledge base document contents.

        Returns:
            str: The formatted prompt string for the LLM.
        """
        docs_text = "\n---\n".join(docs) if docs else "No relevant knowledge base documents found."
        prompt = f"""
You are an intelligent network healing assistant. Your task is to analyze anomaly reports and provide detailed, step-by-step healing recommendations.

Anomaly Report Details:
{anomaly_context}

Relevant Knowledge Base Documents:
{docs_text}

Based on the anomaly report and the provided knowledge, please provide:
1. A brief diagnosis of the potential issue.
2. Step-by-step, actionable healing recommendations.
3. Any important considerations or warnings.
"""
        return prompt

    async def process_anomaly_alert(self, alert_message):
        """
        Processes an incoming anomaly alert from the Calculation Agent.
        It retrieves context, generates recommendations, and pushes to MCP.

        Args:
            alert_message (dict): The anomaly alert message received from Calculation Agent.
        """
        node_id = alert_message.get("node_id", "N/A")
        anomaly_data = alert_message.get("anomaly_data", {})
        severity = anomaly_data.get("severity_classification", "N/A")
        root_causes = anomaly_data.get("root_cause_indicators", [])
        affected_components = anomaly_data.get("affected_components", [])

        print(f"\nHealing Agent: Received A2A alert for Node {node_id}: Severity {severity}")
        print(f"  Root Causes: {root_causes}")
        print(f"  Affected Components: {affected_components}")

        # Construct a query for RAG based on anomaly data
        # Ensure root_causes are correctly extracted for the query if they are dicts
        root_cause_features = [rc.get('feature', '') for rc in root_causes if isinstance(rc, dict)]
        rag_query = f"Anomaly on {node_id}. Severity: {severity}. Affected: {', '.join(affected_components)}. Root causes: {', '.join(root_cause_features) if root_cause_features else 'N/A'}. Provide healing steps."


        # Retrieve contextual information from the knowledge base using RAG
        contextual_info = self.rag.retrieve_context(node_id, rag_query)
        print(f"  Retrieved RAG Context: {contextual_info}")

        # Prepare anomaly context string for the LLM prompt
        anomaly_context_str = json.dumps(anomaly_data, indent=2)

        # Generate healing recommendations using the LLM (Gemini API)
        generated_llm_recommendations = await self.generate_recommendations_with_llm(
            anomaly_context_str, contextual_info
        )
        print(f"  LLM Generated Recommendations:\n{generated_llm_recommendations}")

        # Split the LLM response into diagnosis, recommendations, and important note for structured output
        # This is a basic parsing; a more robust solution might use regex or force JSON output from LLM
        diagnosis = "No diagnosis generated."
        recommendations_list = []
        important_note = "No important note provided."

        # Simple parsing based on the mock LLM output format
        lines = generated_llm_recommendations.split('\n')
        rec_start = False
        for line in lines:
            line = line.strip()
            if line.startswith("Diagnosis for"):
                diagnosis = line
            elif line.startswith("Recommendations:"):
                rec_start = True
            elif line.startswith("Important:"):
                important_note = line.replace("Important: ", "").strip()
                rec_start = False # Stop adding to recommendations
            elif rec_start and line and not line.startswith("---"): # Avoid adding markdown separator to recommendations
                # Remove numbering, but only if the line starts with a digit followed by a dot and space
                if line and len(line) > 2 and line[0].isdigit() and line[1] == '.' and line[2] == ' ':
                    recommendations_list.append(line.split('. ', 1)[1])
                else:
                    recommendations_list.append(line)

        # Ensure recommendations_list is not empty if the parsing fails to find anything
        if not recommendations_list:
            recommendations_list.append("No specific actions extracted from LLM output. Manual investigation required.")
        
        # Prepare the final healing recommendation message to be sent to MCP
        # Initialize final_recommendation_message here to prevent UnboundLocalError
        final_recommendation_message = {
            "node_id": node_id,
            "timestamp": alert_message.get("timestamp", time.time()),
            "severity": severity,
            "affected_components": affected_components,
            "root_cause_indicators": root_causes,
            "time_to_failure": anomaly_data.get("time_to_failure", "N/A"),
            "diagnosis": diagnosis,
            "recommended_actions": recommendations_list,
            "important_note": important_note,
            "raw_llm_output": generated_llm_recommendations # Include raw output for debugging/completeness
        }

        print(f"Healing Agent: Final Healing Recommendation for MCP: {json.dumps(final_recommendation_message, indent=2)}")

        # MCP Communication: Push the healing recommendation to MCP
        mcp_message = {
            "source": "HealingAgent",
            "type": "healing_recommendation",
            "payload": final_recommendation_message
        }
        await self.mcp_push_socket.send_json(mcp_message)
        print(f"Healing Agent: Pushed healing recommendation for Node {node_id} to MCP.")

    async def start(self):
        """
        Starts the Healing Agent, continuously listening for anomaly alerts
        from the Calculation Agent.
        """
        print("Healing Agent started. Waiting for anomaly alerts from Calculation Agent...")
        while True:
            try:
                # Listen for messages from Calculation Agent via A2A subscriber socket
                alert_message = await self.a2a_subscriber_socket.recv_json()
                if alert_message.get("type") == "anomaly_alert":
                    asyncio.create_task(self.process_anomaly_alert(alert_message))
                else:
                    print(f"Healing Agent: Received unknown message type: {alert_message.get('type')}")
            except zmq.error.ZMQError as e:
                print(f"Healing Agent: ZMQ Error: {e}. Retrying in 1 second...")
                await asyncio.sleep(1) # Wait before retrying on ZMQ error
            except Exception as e:
                print(f"Healing Agent: Unexpected error: {e}. Retrying in 1 second...")
                await asyncio.sleep(1) # Wait before retrying on general error

# --- Main function to run the Healing Agent (for standalone testing) ---
if __name__ == "__main__":
    print("Running standalone test for Healing Agent...")

    # Define ZeroMQ addresses for standalone testing
    # These should match the addresses used by Calculation Agent and MCP Agent
    test_sub_address_a2a = "tcp://127.0.0.1:5556" # Matches Calculation Agent's PUB address
    test_push_address_mcp = "tcp://127.0.0.1:5558" # Matches MCP Agent's PULL address

    # Initialize and start the Healing Agent
    healing_agent = HealingAgent(
        sub_socket_address_a2a=test_sub_address_a2a,
        push_socket_address_mcp=test_push_address_mcp
    )

    try:
        asyncio.run(healing_agent.start())
    except KeyboardInterrupt:
        print("\nHealing Agent standalone test stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"An error occurred during standalone Healing Agent run: {e}")
        sys.exit(1)

# --- End of File: healing_agent.py ---