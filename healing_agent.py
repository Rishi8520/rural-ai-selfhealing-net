# --- File: healing_agent.py ---
import asyncio
import json
import numpy as np
import zmq.asyncio
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import sys # For sys.exit()
import time # For time.time() in timestamps
import logging # Added logging
import platform
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# New imports for enhancements
import os
from dotenv import load_dotenv # For loading environment variables from .env
import google.generativeai as genai # For Gemini API
import google.api_core.exceptions # For Gemini API specific exceptions
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type # For robust error handling
from sentence_transformers import SentenceTransformer # For advanced RAG
import faiss # For efficient similarity search with dense vectors

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- ADDED CODE FOR DEBUGGING GOOGLE_API_KEY ---
api_key_status = os.getenv("GOOGLE_API_KEY")
if api_key_status:
    logger.info(f"GOOGLE_API_KEY is loaded: {api_key_status[:5]}...{api_key_status[-5:]}") # Prints first/last 5 chars for security
else:
    logger.error("GOOGLE_API_KEY is NOT loaded. Please ensure it's set or in your .env file.")
# --- END OF ADDED CODE ---


# --- Placeholder for RAG Knowledge Base ---
# This knowledge base is structured per node, allowing for contextual retrieval.
# In a real system, this would be loaded from a persistent database or configuration files.
NODE_KNOWLEDGE_BASE = {
    "node_00": [ # Changed to node_00 to match monitor_agent's formatting
        {"doc_id": "doc_00_1", "content": "Node 00 is a core router. Common issues: high latency, CPU spikes. Healing: restart interface, check routing table, verify BGP sessions."},
        {"doc_id": "doc_00_2", "content": "Node 00 firmware update policy: quarterly. Downtime window: 2 AM - 4 AM UTC. Critical service: VoIP."},
        {"doc_id": "doc_00_3", "content": "Past incident: Node 00 packet loss due to faulty transceiver. Resolution: Replace transceiver, update firmware. Check optical power levels."},
    ],
    "node_01": [ # Changed to node_01
        {"doc_id": "doc_01_1", "content": "Node 01 is a distribution switch. Issues: port errors, VLAN misconfigurations. Healing: clear counters, verify VLAN tags, check trunk links."},
        {"doc_id": "doc_01_2", "content": "Node 01 power redundancy check: monthly. Battery backup capacity: 8 hours. Located in IDF 3."},
        {"doc_id": "doc_01_3", "content": "Recent log: Node 01 received excessive broadcast traffic. Action: Implement broadcast storm control, review STP configuration."},
    ],
    "node_02": [
        {"doc_id": "doc_02_1", "content": "Node 02 is a core firewall. Issues: high connection count, VPN tunnel drops. Healing: review ACLs, check session table limits, verify IKE/IPsec settings."},
        {"doc_id": "doc_02_2", "content": "Node 02 maintenance window: 1st Saturday of month. Primary function: network segmentation, external access control."},
        {"doc_id": "doc_02_3", "content": "Security alert: Node 02 detected port scan from external IP. Blocked source. Review IPS/IDS logs."},
    ],
    "node_03": [
        {"doc_id": "doc_03_1", "content": "Node 03 is a core switch. Issues: spanning tree loops, high CPU utilization. Healing: verify STP root bridge, disable unused ports, monitor interface statistics."},
        {"doc_id": "doc_03_2", "content": "Node 03 is part of datacenter core. Redundancy: HSRP configured. Last firmware version: 15.2(4)E7."},
        {"doc_id": "doc_03_3", "content": "Performance issue: Node 03 experienced intermittent packet drops. Root cause: faulty SFP module. Replaced module."},
    ],
    "node_04": [
        {"doc_id": "doc_04_1", "content": "Node 04 is a border router. Issues: BGP neighbor flaps, route inconsistencies. Healing: check peer configuration, verify AS path, clear BGP sessions."},
        {"doc_id": "doc_04_2", "content": "Node 04 connects to ISP A and ISP B. Primary BGP route preference to ISP A. Located at main demarcation point."},
        {"doc_id": "doc_04_3", "content": "Connectivity loss: Node 04 lost external routes for 5 minutes. Cause: ISP A maintenance. Failover to ISP B successful."},
    ],
    "node_05": [
        {"doc_id": "doc_05_1", "content": "Node 05 is a distribution router. Issues: OSPF neighbor issues, routing table overflow. Healing: check OSPF area configuration, verify link state database, filter routes."},
        {"doc_id": "doc_05_2", "content": "Node 05 serves the engineering department. IP addressing scheme: 10.5.0.0/16. Next-gen firewall integration pending."},
        {"doc_id": "doc_05_3", "content": "High CPU: Node 05 CPU utilization spiked. Cause: large number of debug logs enabled. Disabled unnecessary debugs."},
    ],
    "node_06": [
        {"doc_id": "doc_06_1", "content": "Node 06 is an access switch. Issues: client connectivity, PoE failures. Healing: check port status, power cycle PoE device, verify VLAN assignment."},
        {"doc_id": "doc_06_2", "content": "Node 06 supports IP phones and wireless APs. PoE budget: 370W. Located in conference room area."},
        {"doc_id": "doc_06_3", "content": "Client complaint: Node 06 users report slow Wi-Fi. Action: Check AP uplink, verify bandwidth utilization, reboot APs."},
    ],
    "node_07": [
        {"doc_id": "doc_07_1", "content": "Node 07 is an access switch. Issues: authentication failures, port security violations. Healing: verify RADIUS/TACACS+ configuration, clear port security violations, check MAC address table."},
        {"doc_id": "doc_07_2", "content": "Node 07 serves the sales department. Access control: 802.1X enabled. Guest VLAN: VLAN 500."},
        {"doc_id": "doc_07_3", "content": "Security incident: Node 07 detected unauthorized device. Port disabled by port security. Investigate device."},
    ],
    "node_08": [
        {"doc_id": "doc_08_1", "content": "Node 08 is a wireless controller. Issues: AP disassociations, client roaming problems. Healing: check controller-AP connectivity, review RF profiles, verify client database."},
        {"doc_id": "doc_08_2", "content": "Node 08 manages 50 access points. Software version: 8.10.130.0. Redundancy: N+1 with Node 09."},
        {"doc_id": "doc_08_3", "content": "Wi-Fi performance: Node 08 reports high channel utilization. Action: Adjust AP transmit power, optimize channel plan, disable lower data rates."},
    ],
    "node_09": [
        {"doc_id": "doc_09_1", "content": "Node 09 is a load balancer. Issues: server down, health check failures. Healing: verify backend server status, check health monitor configuration, review load balancing algorithm."},
        {"doc_id": "doc_09_2", "content": "Node 09 provides high availability for web servers. Persistence: Source IP. Algorithms: Least Connections."},
        {"doc_id": "doc_09_3", "content": "Application slow: Node 09 reports high response times. Cause: one backend server overloaded. Removed server from pool, investigated issue."},
    ],
    "node_10": [
        {"doc_id": "doc_10_1", "content": "Node 10 is a DNS server. Issues: name resolution failures, slow responses. Healing: check DNS service status, verify zone files, clear DNS cache."},
        {"doc_id": "doc_10_2", "content": "Node 10 is primary internal DNS. Forwarders: public DNS servers. Replication with Node 11."},
        {"doc_id": "doc_10_3", "content": "Service outage: Node 10 stopped responding. Cause: Disk full. Cleared logs, expanded disk space."},
    ],
    "node_11": [
        {"doc_id": "doc_11_1", "content": "Node 11 is a DHCP server. Issues: IP address exhaustion, client lease failures. Healing: check DHCP pool usage, expand pool, verify helper addresses."},
        {"doc_id": "doc_11_2", "content": "Node 11 serves the main corporate LAN. Lease duration: 8 hours. Reservations for critical servers."},
        {"doc_id": "doc_11_3", "content": "Client reports: Node 11 not assigning IPs. Cause: incorrect helper address on switch. Corrected configuration."},
    ],
    "node_12": [
        {"doc_id": "doc_12_1", "content": "Node 12 is a VPN concentrator. Issues: user authentication failures, tunnel instability. Healing: check user credentials, verify pre-shared key, review tunnel logs."},
        {"doc_id": "doc_12_2", "content": "Node 12 supports remote access VPN. Max concurrent users: 500. Client software: AnyConnect."},
        {"doc_id": "doc_12_3", "content": "Remote access issue: Node 12 showing high CPU. Cause: DDoS attack targeting VPN. Applied rate limiting, geo-blocking."},
    ],
    "node_13": [
        {"doc_id": "doc_13_1", "content": "Node 13 is an IDS/IPS appliance. Issues: false positives, dropped legitimate traffic. Healing: fine-tune signatures, review bypass rules, update threat intelligence."},
        {"doc_id": "doc_13_2", "content": "Node 13 monitors core traffic segment. Deployment mode: inline. Signature updates: daily."},
        {"doc_id": "doc_13_3", "content": "Security event: Node 13 alerted on SQL injection. Blocked traffic. Confirmed application vulnerability patched."},
    ],
    "node_14": [
        {"doc_id": "doc_14_1", "content": "Node 14 is a logging server (Syslog/SIEM). Issues: log ingestion failures, disk full. Healing: check log forwarders, prune old logs, expand storage."},
        {"doc_id": "doc_14_2", "content": "Node 14 collects logs from all network devices. Retention policy: 90 days. Backups: daily to NAS."},
        {"doc_id": "doc_14_3", "content": "Log gap: Node 14 not receiving logs from Node 20. Cause: incorrect logging configuration on Node 20. Corrected source IP."},
    ],
    "node_15": [
        {"doc_id": "doc_15_1", "content": "Node 15 is a proxy server. Issues: slow Browse, content filtering bypass. Healing: check proxy service status, review caching policy, update content categories."},
        {"doc_id": "doc_15_2", "content": "Node 15 handles all outbound HTTP/HTTPS traffic. Authentication: Active Directory. Bypass list for critical applications."},
        {"doc_id": "doc_15_3", "content": "User reports: Node 15 is slow. Cause: high resource utilization due to large downloads. Implemented bandwidth limits, configured QoS."},
    ],
    "node_16": [
        {"doc_id": "doc_16_1", "content": "Node 16 is a VoIP gateway. Issues: one-way audio, call drops. Healing: check SIP trunk status, verify codec negotiation, review QoS markings."},
        {"doc_id": "doc_16_2", "content": "Node 16 connects internal VoIP to PSTN. Supported codecs: G.711, G.729. Max concurrent calls: 200."},
        {"doc_id": "doc_16_3", "content": "Call quality: Node 16 users report choppy audio. Cause: network congestion on WAN link. Prioritized voice traffic with QoS."},
    ],
    "node_17": [
        {"doc_id": "doc_17_1", "content": "Node 17 is a network management system (NMS). Issues: device unreachable, incorrect alerts. Healing: check SNMP/NetFlow configuration, verify device credentials, review alert thresholds."},
        {"doc_id": "doc_17_2", "content": "Node 17 monitors 1000 devices. Polling interval: 5 minutes. Integration with ticketing system."},
        {"doc_id": "doc_17_3", "content": "NMS alert storm: Node 17 generated excessive alerts due to flapping link. Suppressed alerts, investigated link stability."},
    ],
    "node_18": [
        {"doc_id": "doc_18_1", "content": "Node 18 is a core application server. Issues: application unresponsive, database errors. Healing: restart application service, check database connectivity, review application logs."},
        {"doc_id": "doc_18_2", "content": "Node 18 hosts critical ERP application. OS: Windows Server 2019. Database: SQL Server."},
        {"doc_id": "doc_18_3", "content": "Application crash: Node 18 ERP crashed. Cause: out of memory. Increased RAM, optimized application config."},
    ],
    "node_19": [
        {"doc_id": "doc_19_1", "content": "Node 19 is a backup server. Issues: backup failures, storage full. Healing: check backup job status, clear old backups, expand storage capacity."},
        {"doc_id": "doc_19_2", "content": "Node 19 backs up all core servers nightly. Backup software: Veeam. Offsite replication to DR site."},
        {"doc_id": "doc_19_3", "content": "Backup failed: Node 19 backup job failed for Node 02. Cause: firewall blocking communication. Opened necessary ports."},
    ],
    # Adding knowledge base entries for nodes 20-49 to cover the access layer
    "node_20": [
        {"doc_id": "doc_20_1", "content": "Node 20 is an access switch in building A, floor 1. Issues: port down, slow client access. Healing: check cable, power cycle device, verify VLAN."},
    ],
    "node_21": [
        {"doc_id": "doc_21_1", "content": "Node 21 is an access switch in building A, floor 2. Common issues: PoE failure for IP cameras. Healing: verify PoE budget, reset port."},
    ],
    "node_22": [
        {"doc_id": "doc_22_1", "content": "Node 22 is an access switch in building B, floor 1. Issues: broadcast storm, loop detection. Healing: enable loop guard, check STP on uplink."},
    ],
    "node_23": [
        {"doc_id": "doc_23_1", "content": "Node 23 is an access point in building B, floor 2. Issues: low signal, client disconnects. Healing: check AP placement, adjust power, check channel interference."},
    ],
    "node_24": [
        {"doc_id": "doc_24_1", "content": "Node 24 is an access switch in datacenter row 1. Critical for server rack connectivity. Healing: check link status, replace SFP."},
    ],
    "node_25": [
        {"doc_id": "doc_25_1", "content": "Node 25 is an access switch in datacenter row 2. Issues: high temperature alerts, fan failure. Healing: check cooling, replace fan module."},
    ],
    "node_26": [
        {"doc_id": "doc_26_1", "content": "Node 26 is an IoT gateway in manufacturing plant. Issues: device connectivity, sensor data loss. Healing: check gateway status, review network segment."},
    ],
    "node_27": [
        {"doc_id": "doc_27_1", "content": "Node 27 is a surveillance camera NVR. Issues: video feed loss, storage full. Healing: check camera connection, clear old recordings."},
    ],
    "node_28": [
        {"doc_id": "doc_28_1", "content": "Node 28 is an access switch in the cafeteria. Issues: Wi-Fi slow, high client count. Healing: check AP load, adjust bandwidth limits."},
    ],
    "node_29": [
        {"doc_id": "doc_29_1", "content": "Node 29 is an access switch in the main lobby. Issues: guest network access, captive portal. Healing: verify portal service, check VLAN."},
    ],
    "node_30": [
        {"doc_id": "doc_30_1", "content": "Node 30 is an access switch serving remote office 1. Issues: WAN latency, VPN drops. Healing: check WAN link, optimize VPN tunnel."},
    ],
    "node_31": [
        {"doc_id": "doc_31_1", "content": "Node 31 is an access switch serving remote office 2. Issues: VoIP quality, RTP packet loss. Healing: check QoS configuration, prioritize voice."},
    ],
    "node_32": [
        {"doc_id": "doc_32_1", "content": "Node 32 is an access switch in the executive floor. High priority for critical services. Healing: verify uplink, check dedicated VLANs."},
    ],
    "node_33": [
        {"doc_id": "doc_33_1", "content": "Node 33 is an access point in auditorium. Issues: poor coverage, many clients. Healing: add more APs, adjust power, optimize channel."},
    ],
    "node_34": [
        {"doc_id": "doc_34_1", "content": "Node 34 is an access switch in IT department. Issues: SSH/RDP connectivity, management VLAN. Healing: check ACLs, verify management interface."},
    ],
    "node_35": [
        {"doc_id": "doc_35_1", "content": "Node 35 is an access switch in training room. Issues: projector connectivity, multicast. Healing: check IGMP snooping, verify AV setup."},
    ],
    "node_36": [
        {"doc_id": "doc_36_1", "content": "Node 36 is an access switch in laboratory. Issues: specific device communication, industrial protocols. Healing: check protocol forwarding, verify firewall rules."},
    ],
    "node_37": [
        {"doc_id": "doc_37_1", "content": "Node 37 is an access switch in warehouse. Issues: scanner connectivity, barcode readers. Healing: check wireless signal, verify network access."},
    ],
    "node_38": [
        {"doc_id": "doc_38_1", "content": "Node 38 is an access point in outdoor area. Issues: environmental factors, weather damage. Healing: check physical integrity, verify enclosure."},
    ],
    "node_39": [
        {"doc_id": "doc_39_1", "content": "Node 39 is an access switch in retail store 1. Issues: POS system connectivity, credit card processing. Healing: check PCI compliance, verify secure network."},
    ],
    "node_40": [
        {"doc_id": "doc_40_1", "content": "Node 40 is an access switch in retail store 2. Issues: inventory system access, slow database. Healing: check local server connection, network performance."},
    ],
    "node_41": [
        {"doc_id": "doc_41_1", "content": "Node 41 is an access switch in the data analysis center. High bandwidth requirements. Healing: check link aggregation, monitor traffic."},
    ],
    "node_42": [
        {"doc_id": "doc_42_1", "content": "Node 42 is an access switch in the design studio. Issues: large file transfers, network drive access. Healing: optimize SMB settings, check storage connectivity."},
    ],
    "node_43": [
        {"doc_id": "doc_43_1", "content": "Node 43 is an access switch in the security operations center. Issues: SIEM data feed, security tool access. Healing: ensure high priority, verify dedicated links."},
    ],
    "node_44": [
        {"doc_id": "doc_44_1", "content": "Node 44 is an access point in the recreation area. Issues: public Wi-Fi access, bandwidth hogging. Healing: implement fair usage policy, prioritize business traffic."},
    ],
    "node_45": [
        {"doc_id": "doc_45_1", "content": "Node 45 is an access switch in the cafeteria kitchen. Issues: specific appliance connectivity, network isolation. Healing: verify VLAN segmentation, check power source."},
    ],
    "node_46": [
        {"doc_id": "doc_46_1", "content": "Node 46 is an access switch in the building management system room. Issues: HVAC control, sensor data. Healing: check Modbus/BACnet integration, network reliability."},
    ],
    "node_47": [
        {"doc_id": "doc_47_1", "content": "Node 47 is an access switch in the employee lounge. Issues: streaming services, personal devices. Healing: implement guest policies, manage bandwidth."},
    ],
    "node_48": [
        {"doc_id": "doc_48_1", "content": "Node 48 is an access switch in the shipping/receiving area. Issues: printer connectivity, barcode scanners. Healing: verify printer network settings, check local LAN."},
    ],
    "node_49": [
        {"doc_id": "doc_49_1", "content": "Node 49 is an access switch in the server testing lab. Issues: isolated network, test environment access. Healing: check VLAN segregation, review test network configuration."},
    ]
}


# Function to load knowledge base from a JSON file (or database in a real scenario)
def load_knowledge_base_from_file(file_path: str) -> dict:
    """
    Loads the knowledge base from a specified JSON file.
    Includes error handling for file operations.
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"Knowledge base file not found: {file_path}")
            return {}
        with open(file_path, 'r') as f:
            kb = json.load(f)
            logger.info(f"Knowledge base loaded successfully from {file_path}")
            return kb
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from knowledge base file {file_path}: {e}")
        return {}
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading knowledge base from {file_path}: {e}")
        return {}


class HealingAgent:
    def __init__(self, context: zmq.asyncio.Context, sub_socket_address_a2a: str, push_socket_address_mcp: str):
        logger.info("Healing Agent: Initializing...")
        self.context = context
        self.a2a_subscriber_socket = self.context.socket(zmq.SUB)
        self.a2a_subscriber_socket.connect(sub_socket_address_a2a)
        self.a2a_subscriber_socket.setsockopt_string(zmq.SUBSCRIBE, "")  # Subscribe to all messages

        self.mcp_push_socket = self.context.socket(zmq.PUSH)
        self.mcp_push_socket.connect(push_socket_address_mcp)

        # Initialize LLM and RAG components
        # Original RAG components (TF-IDF based)
        self.vectorizer = TfidfVectorizer()
        self.node_corpus = {node_id: [doc["content"] for doc in docs] for node_id, docs in NODE_KNOWLEDGE_BASE.items()}
        self.node_tfidf_matrices = {} # Will store TF-IDF matrix for each node's KB

        # Advanced RAG components (Sentence-Transformers + FAISS)
        self.rag_model = SentenceTransformer('all-MiniLM-L6-v2') # Smaller, faster model for embeddings
        self.rag_index = {} # FAISS index per node
        self.rag_documents = {} # Original documents per node

        # Ensure that GOOGLE_API_KEY is retrieved after load_dotenv()
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        if not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set. Cannot initialize LLM.")
        genai.configure(api_key=self.google_api_key)
        self.llm = genai.GenerativeModel('gemini-pro')
        self.last_rag_update = time.time()
        self.rag_update_interval = 300 # Update every 5 minutes for dynamic KB

        logger.info("Healing Agent: Initialized.")

    async def _prepare_rag_knowledge_base(self):
        """
        Dynamically loads and prepares the RAG knowledge base, including FAISS indexing.
        This function should be called periodically or upon KB updates.
        """
        logger.info("RAG: Preparing Advanced knowledge base...")

        # For this simulation, we'll use the fixed NODE_KNOWLEDGE_BASE directly for simplicity.
        # In a real system, this would be updated from a source.

        for node_id, docs in NODE_KNOWLEDGE_BASE.items():
            if not docs:
                logger.warning(f"No documents found for node {node_id} in knowledge base. Skipping RAG preparation for this node.")
                continue

            # Store original documents
            self.rag_documents[node_id] = docs
            corpus = [doc["content"] for doc in docs]

            if not corpus:
                logger.warning(f"Corpus is empty for node {node_id}. Skipping FAISS index creation.")
                continue

            # Generate embeddings
            corpus_embeddings = self.rag_model.encode(corpus)
            dimension = corpus_embeddings.shape[1]

            # Create FAISS index
            index = faiss.IndexFlatL2(dimension)
            index.add(np.array(corpus_embeddings).astype('float32'))
            self.rag_index[node_id] = index
            logger.info(f"RAG: Prepared FAISS index for '{node_id}' with {len(docs)} documents.")
        logger.info("RAG: Advanced knowledge base preparation complete.")
        self.last_rag_update = time.time()


    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3),
           retry=retry_if_exception_type(google.api_core.exceptions.ResourceExhausted))
    async def _call_llm(self, prompt: str) -> str:
        """
        Calls the LLM with a given prompt, including retry logic for specific errors.
        """
        try:
            response = await self.llm.generate_content_async(prompt)
            if response and response.candidates:
                if response.candidates[0].content and response.candidates[0].content.parts:
                    generated_text = "".join([part.text for part in response.candidates[0].content.parts])
                    return generated_text
            logger.warning("LLM response did not contain usable text content.")
            return "No specific healing action recommended by LLM."
        except google.api_core.exceptions.ResourceExhausted as e:
            logger.error(f"LLM call failed due to resource exhaustion: {e}. Retrying...")
            raise # Re-raise to trigger tenacity retry
        except google.api_core.exceptions.GoogleAPIError as e:
            logger.error(f"Google API error during LLM call: {e}. Attempting to retry if configured.")
            raise # Re-raise to trigger tenacity retry for generic API errors
        except Exception as e:
            logger.error(f"An unexpected error occurred during LLM call: {e}")
            return "Error calling LLM for healing action."


    async def _retrieve_rag_context(self, node_id: str, query: str, top_k: int = 2) -> str:
        """
        Retrieves relevant context from the RAG knowledge base for a given node and query.
        """
        if node_id not in self.rag_index or not self.rag_documents.get(node_id):
            logger.warning(f"RAG: No knowledge base or index found for node {node_id}. Cannot retrieve context.")
            return ""

        query_embedding = self.rag_model.encode([query])
        # Ensure query_embedding is float32 for FAISS
        D, I = self.rag_index[node_id].search(np.array(query_embedding).astype('float32'), top_k)

        context = []
        for i in range(len(I[0])):
            doc_index = I[0][i]
            if doc_index < len(self.rag_documents[node_id]):
                context.append(self.rag_documents[node_id][doc_index]["content"])
        logger.info(f"RAG: Retrieved {len(context)} documents for node {node_id} query: '{query[:50]}...'")
        return "\n".join(context)


    async def _determine_healing_action(self, node_id: str, anomaly_description: str) -> str:
        """
        Determines the appropriate healing action using RAG and LLM.
        """
        logger.info(f"Healing Agent: Determining action for Node {node_id} - Anomaly: {anomaly_description}")

        # Ensure RAG knowledge base is prepared (and potentially updated)
        if not self.rag_index or (time.time() - self.last_rag_update) > self.rag_update_interval:
            await self._prepare_rag_knowledge_base()

        # Retrieve relevant context using RAG
        context = await self._retrieve_rag_context(node_id, anomaly_description)

        if context:
            prompt = (f"Based on the following knowledge about node {node_id} and the anomaly description:\n\n"
                      f"Node Knowledge: {context}\n\n"
                      f"Anomaly Description for Node {node_id}: {anomaly_description}\n\n"
                      f"Recommend a concise, specific healing action. If no specific action is clear, suggest 'Investigate further'.")
        else:
            prompt = (f"Anomaly Description for Node {node_id}: {anomaly_description}\n\n"
                      f"Based on general network knowledge, recommend a concise, specific healing action for node {node_id}. If no specific action is clear, suggest 'Investigate further'.")

        llm_response = await self._call_llm(prompt)
        logger.info(f"LLM: Generated healing action for Node {node_id}: {llm_response[:100]}...") # Log first 100 chars
        return llm_response


    async def start(self):
        logger.info("Healing Agent: Starting...")
        await self._prepare_rag_knowledge_base() # Initial preparation

        while True:
            try:
                # Polling for messages from the A2A (Anomaly to Action) channel
                message = await self.a2a_subscriber_socket.recv_string()
                timestamp = time.time() # Capture reception time

                # Assume message is a JSON string with 'node_id' and 'anomaly_description'
                anomaly_data = json.loads(message)
                node_id = anomaly_data.get("node_id")
                anomaly_description = anomaly_data.get("anomaly_description")

                if node_id and anomaly_description:
                    logger.info(f"Healing Agent: Received anomaly for Node {node_id}: {anomaly_description}")
                    healing_action = await self._determine_healing_action(node_id, anomaly_description)

                    # Prepare message for MCP Agent
                    mcp_message = {
                        "timestamp": timestamp,
                        "source_agent": "HealingAgent",
                        "target_agent": "MCPAgent",
                        "node_id": node_id,
                        "action": healing_action,
                        "anomaly_description": anomaly_description # Include original anomaly for context
                    }
                    mcp_message_str = json.dumps(mcp_message)
                    await self.mcp_push_socket.send_string(mcp_message_str)
                    logger.info(f"Healing Agent: Sent action to MCP Agent for Node {node_id}: {healing_action[:50]}...")
                else:
                    logger.warning(f"Healing Agent: Received malformed anomaly message: {message}")

                # Periodically update RAG knowledge base
                if (time.time() - self.last_rag_update) > self.rag_update_interval:
                    await self._prepare_rag_knowledge_base()

                await asyncio.sleep(0.1) # Small delay to prevent busy-looping
            except zmq.error.Again:
                # No message received, continue loop after a small delay
                await asyncio.sleep(0.1)
            except json.JSONDecodeError as e:
                logger.error(f"Healing Agent: Error decoding JSON message: {e}. Message: {message[:100]}...")
                await asyncio.sleep(1) # Wait before retrying on bad message
            except Exception as e:
                logger.error(f"Healing Agent: Unexpected error during message processing: {e}. Retrying in 1 second...")
                await asyncio.sleep(1) # Wait before retrying on general error


# --- Main function to run the Healing Agent (for standalone testing) ---
if __name__ == "__main__":
    logger.info("Running standalone test for Healing Agent...")

    # Define ZeroMQ addresses for standalone testing
    # These should match the addresses used by Calculation Agent and MCP Agent
    test_sub_address_a2a = "tcp://127.0.0.1:5556" # Matches Calculation Agent's PUB address
    test_push_address_mcp = "tcp://127.0.0.1:5558" # Matches MCP Agent's PULL address

    # Initialize and start the Healing Agent
    # For standalone testing, create a local context
    local_context = zmq.asyncio.Context()
    healing_agent = HealingAgent(
        context=local_context, # Pass local context for standalone
        sub_socket_address_a2a=test_sub_address_a2a,
        push_socket_address_mcp=test_push_address_mcp
    )

    try:
        asyncio.run(healing_agent.start())
    except KeyboardInterrupt:
        logger.info("\nHealing Agent standalone test stopped by user (KeyboardInterrupt).")
        # Clean up ZeroMQ context and sockets on shutdown
        if healing_agent.a2a_subscriber_socket:
            healing_agent.a2a_subscriber_socket.close()
            logger.info("A2A subscriber socket closed.")
        if healing_agent.mcp_push_socket:
            healing_agent.mcp_push_socket.close()
            logger.info("MCP push socket closed.")
        if local_context:
            local_context.term()
            logger.info("ZeroMQ context terminated.")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"An unhandled exception occurred during Healing Agent runtime: {e}")
        # Ensure cleanup even on other exceptions
        if healing_agent.a2a_subscriber_socket:
            healing_agent.a2a_subscriber_socket.close()
        if healing_agent.mcp_push_socket:
            healing_agent.mcp_push_socket.close()
        if local_context:
            local_context.term()
        sys.exit(1) # Exit with error code