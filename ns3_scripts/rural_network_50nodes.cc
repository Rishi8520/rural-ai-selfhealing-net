/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * COMPLETE ENHANCED RURAL NETWORK SIMULATION WITH RAG DATABASE
 * Combines working original visualization with enhanced RAG features
 * ALL ISSUES FIXED: No recovery, no percentages, no size changes, proper traffic flow
 */

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/wifi-module.h"
#include "ns3/mobility-module.h"
#include "ns3/applications-module.h"
#include "ns3/netanim-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/energy-module.h"
#include "ns3/error-model.h"
#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <iomanip>
#include <map>
#include <cmath>
#include <sstream>
#include <random>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("EnhancedRuralNetworkRAG");

// **FIXED: Simple ID generator without UUID**
class SimpleIdGenerator {
private:
    static uint64_t counter;
public:
    static std::string GenerateId(const std::string& prefix = "id") {
        return prefix + "_" + std::to_string(++counter) + "_" + std::to_string(time(nullptr) % 100000);
    }
};
uint64_t SimpleIdGenerator::counter = 0;

// **CONFIGURATION STRUCTURE**
struct SimulationConfig {
    std::string mode;
    double totalSimulationTime;
    double dataCollectionInterval;
    double baselineDuration;
    double faultStartTime;
    bool enableFaultInjection;
    bool enableVisualization;
    bool enableFaultVisualization;
    bool useHighSpeedNetwork; 
    int targetDataPoints;
    std::string outputPrefix;
    
    // RAG database options (optional)
    bool enableDatabaseGeneration;
    bool enableLinkTracking;
    bool enableAnomalyClassification;
    bool enableTrafficFlowAnalysis;
    bool enablePolicyLoading;
    std::string databaseFormat;
};

// **ORIGINAL FAULT PATTERN (from working code)**
struct GradualFaultPattern {
    uint32_t targetNode;
    uint32_t connectedNode;
    std::string faultType;
    std::string faultDescription;
    Time startDegradation;
    Time faultOccurrence;
    Time faultDuration;
    double degradationRate;
    double severity;
    bool isActive;
    double currentSeverity;
    bool visualIndicatorActive;
    std::string visualMessage;
    
    // **MINIMAL: Only for RAG database**
    std::string anomalyId;
};

struct FaultEvent {
    double timestamp;
    std::string eventType;
    std::string faultType;
    std::vector<uint32_t> affectedNodes;
    std::string description;
    std::string visualEffect;
};

// **RAG DATABASE STRUCTURES (optional features)**
struct LinkRecord {
    std::string linkId;
    std::string sourceNodeId;
    std::string destinationNodeId;
    std::string linkType;
    double totalBandwidthMbps;
    double currentBandwidthUtilPercent;
    double latencyMs;
    double packetLossRate;
    std::string status;
    bool isRedundant;
    double timestamp;
};

struct AnomalyRecord {
    std::string anomalyId;
    double timestamp;
    std::string nodeId;
    std::string severityClassification;
    std::string anomalyDescription;
    std::string rootCauseIndicators;
    std::string affectedComponents;
    std::string timeToFailure;
    std::string status;
    int healingRecommendationId;
    int anomalyTypeId;
};

struct RecoveryTactic {
    int tacticId;
    std::string tacticName;
    std::string description;
    int estimatedDowntimeSeconds;
    std::string riskLevel;
    bool isAutomatedCapable;
    int policyId;
};

struct PolicyRecord {
    int policyId;
    std::string policyName;
    std::string policyCategory;
    std::string description;
    std::string fullTextReference;
    std::string impactOnRecovery;
    std::string impactOnLoadDistribution;
    std::string lastUpdated;
};

struct TrafficFlowRecord {
    std::string flowId;
    std::string sourceNodeId;
    std::string destinationNodeId;
    std::vector<std::string> currentPathLinks;
    double trafficVolumeMbps;
    std::string trafficType;
    std::string priority;
    double startTime;
    double endTime;
    double timestamp;
};

struct NodeType {
    int nodeTypeId;
    std::string typeName;
    std::string description;
    std::string typicalRole;
};

struct NetworkLayer {
    int layerId;
    std::string layerName;
    std::string description;
};

struct EnhancedNodeRecord {
    std::string nodeId;
    std::string nodeName;
    int layerId;
    int nodeTypeId;
    std::string ipAddress;
    std::string location;
    std::string status;
    double lastHeartbeat;
    double currentCpuLoadPercent;
    double currentMemoryLoadPercent;
    double currentBandwidthUtilPercent;
    double maxCapacityUnits;
    std::string operationalState;
    std::string firmwareVersion;
    double lastConfigChange;
    double timestamp;
};

// **MAIN SIMULATION CLASS**
class EnhancedRuralNetworkRAG
{
public:
    EnhancedRuralNetworkRAG(const SimulationConfig& config);
    void Run();
    
    static SimulationConfig CreateRAGDataConfig(int targetDataPoints = 500);
    static SimulationConfig CreateFaultDemoConfig();

private:
    SimulationConfig m_config;
    NodeContainer coreNodes, distributionNodes, accessNodes, allNodes;
    std::map<std::pair<uint32_t, uint32_t>, bool> linkStatus;
    NetDeviceContainer coreDevices, distributionDevices, accessDevices;
    std::vector<Ipv4InterfaceContainer> allInterfaces;
    PointToPointHelper p2pHelper;
    MobilityHelper mobility;
    InternetStackHelper stack;
    Ipv4AddressHelper address;
    ApplicationContainer sourceApps, sinkApps;
    FlowMonitorHelper flowHelper;
    Ptr<FlowMonitor> flowMonitor;
    AnimationInterface* animInterface;
    
    std::vector<GradualFaultPattern> gradualFaults;
    std::vector<FaultEvent> faultEvents;
    
    // **RAG DATABASE (optional)**
    std::vector<LinkRecord> linkRecords;
    std::vector<AnomalyRecord> anomalyRecords;
    std::vector<RecoveryTactic> recoveryTactics;
    std::vector<PolicyRecord> policyRecords;
    std::vector<TrafficFlowRecord> trafficFlowRecords;
    std::vector<EnhancedNodeRecord> nodeRecords;
    std::vector<NodeType> nodeTypes;
    std::vector<NetworkLayer> networkLayers;
    
    // **OUTPUT FILES**
    std::ofstream nodesDbFile, linksDbFile, anomaliesDbFile;
    std::ofstream recoveryTacticsDbFile, policiesDbFile, trafficFlowsDbFile;
    std::ofstream databaseSchemaFile;
    std::ofstream metricsFile, topologyFile, configFile, faultLogFile;
    
    // **CORE METHODS (from working original)**
    void SetupRobustTopology();
    void SetupRobustApplications();
    void SetupCoreLayer();
    void SetupDistributionLayer();
    void SetupAccessLayer();
    void SetupRobustRouting();
    void SetupEnergyModel();
    void CreateComprehensiveTraffic();
    void CreateBaselineTraffic();
    void SetupRobustNetAnimVisualization();
    
    // **FAULT METHODS (enhanced from original)**
    void ScheduleGradualFaultPatterns();
    void CreateRealisticFiberCutPattern(uint32_t nodeA, uint32_t nodeB, Time startTime);
    void CreateRealisticPowerFluctuationPattern(uint32_t nodeId, Time startTime);
    void UpdateFaultProgression();
    double CalculateNodeDegradation(uint32_t nodeId, const std::string& metric);
    
    // **VISUAL METHODS (fixed from original)**
    void ProcessFaultVisualization();
    void UpdateVisualFaultIndicators();
    void UpdateNodeVisualStatus(uint32_t nodeId, const std::string& status);
    void AnnounceFaultEvent(const GradualFaultPattern& fault, const std::string& eventType);
    void LogFaultEvent(const FaultEvent& event);
    std::string GetNodeVisualName(uint32_t nodeId);
    void HideFiberLink(uint32_t nodeA, uint32_t nodeB);
    void RestoreFiberLink(uint32_t nodeA, uint32_t nodeB);
    void ShowPowerIssue(uint32_t nodeId);
    void HidePowerIssue(uint32_t nodeId);
    void UpdateGradualVisualization(const GradualFaultPattern& fault);
    void UpdatePeakVisualization(const GradualFaultPattern& fault);
    
    // **DATA COLLECTION**
    void CollectComprehensiveMetrics();
    void WriteTopologyInfo();
    void WriteConfigurationInfo();
    void WriteFaultEventLog();
    double GetTimeOfDayMultiplier();
    double GetTrafficPatternMultiplier();
    double GetSeasonalVariation();
    
    // **RAG DATABASE METHODS (optional)**
    void InitializeDatabaseStructures();
    void LoadRecoveryTactics();
    void LoadPolicyKnowledgeBase();
    void InitializeReferenceData();
    void CreateLinkTopology();
    void CollectLinkMetrics();
    void ClassifyAndRecordAnomaly(const GradualFaultPattern& fault, const std::string& eventType);
    std::string GenerateAnomalyId();
    std::string GenerateRootCauseJSON(const GradualFaultPattern& fault);
    std::string GenerateAffectedComponentsJSON(const GradualFaultPattern& fault);
    std::string ClassifyAnomalySeverity(double severity);
    void InitializeTrafficFlowTracking();
    void UpdateTrafficFlows();
    std::string GenerateLinkId(uint32_t nodeA, uint32_t nodeB);
    std::string GenerateFlowId(uint32_t source, uint32_t dest);
    std::vector<std::string> TracePath(uint32_t source, uint32_t dest);
    void CollectEnhancedNodeData();
    EnhancedNodeRecord GetEnhancedNodeRecord(uint32_t nodeId);
    std::string GenerateNodeId(uint32_t nodeId);
    std::string GetNodeIpAddress(uint32_t nodeId);
    void ExportDatabaseTables();
    void ExportNodesTable();
    void ExportLinksTable();
    void ExportAnomaliesTable();
    void ExportRecoveryTacticsTable();
    void ExportPoliciesTable();
    void ExportTrafficFlowsTable();
    void ExportReferenceTablesSQL();
    void GenerateDatabaseSchema();
    
    struct NodeMetrics {
        uint32_t nodeId;
        double throughputMbps;
        double latencyMs;
        double packetLossRate;
        double jitterMs;
        double signalStrengthDbm;
        double cpuUsage;
        double memoryUsage;
        double bufferOccupancy;
        uint32_t activeLinks;
        uint32_t neighborCount;
        double linkUtilization;
        double criticalServiceLoad;
        double normalServiceLoad;
        double energyLevel;
        Vector position;
        std::string nodeType;
        bool isOperational;
        double voltageLevel;
        double powerStability;
        double degradationLevel;
        double faultSeverity;
    };
    
    NodeMetrics GetEnhancedNodeMetrics(uint32_t nodeId);
};

// **CONFIGURATION FACTORY METHODS**
SimulationConfig EnhancedRuralNetworkRAG::CreateRAGDataConfig(int targetDataPoints)
{
    SimulationConfig config;
    config.mode = "rag_training";
    config.dataCollectionInterval = 5.0;
    config.totalSimulationTime = targetDataPoints * config.dataCollectionInterval;
    config.baselineDuration = config.totalSimulationTime * 0.6;
    config.faultStartTime = config.baselineDuration;
    config.enableFaultInjection = true;
    config.useHighSpeedNetwork = true;  
    config.enableVisualization = false;
    config.enableFaultVisualization = false;
    config.targetDataPoints = targetDataPoints;
    config.outputPrefix = "rag_training";
    
    config.enableDatabaseGeneration = true;
    config.enableLinkTracking = true;
    config.enableAnomalyClassification = true;
    config.enableTrafficFlowAnalysis = true;
    config.enablePolicyLoading = true;
    config.databaseFormat = "sql";
    
    std::cout << "=== RAG TRAINING CONFIGURATION ===" << std::endl;
    std::cout << "Target data points: " << targetDataPoints << std::endl;
    std::cout << "Database generation: ENABLED" << std::endl;
    std::cout << "===================================" << std::endl;
    
    return config;
}

SimulationConfig EnhancedRuralNetworkRAG::CreateFaultDemoConfig()
{
    SimulationConfig config;
    config.mode = "fault_demo";
    config.dataCollectionInterval = 2.0;    
    config.totalSimulationTime = 300.0;
    config.baselineDuration = 30.0;
    config.faultStartTime = config.baselineDuration;
    config.enableFaultInjection = true;
    config.enableVisualization = true;
    config.enableFaultVisualization = true;
    config.useHighSpeedNetwork = true; 
    config.targetDataPoints = 150;
    config.outputPrefix = "fault_demo";
    
    config.enableDatabaseGeneration = true;
    config.enableLinkTracking = true;
    config.enableAnomalyClassification = true;
    config.enableTrafficFlowAnalysis = true;
    config.enablePolicyLoading = true;
    config.databaseFormat = "sql";
    std::cout << "=== FAULT DEMO: HIGH SPEED NETWORK ===" << std::endl;
    return config;
}

// **CONSTRUCTOR**
EnhancedRuralNetworkRAG::EnhancedRuralNetworkRAG(const SimulationConfig& config) 
    : m_config(config), animInterface(nullptr)
{
    std::string metricsFileName = m_config.outputPrefix + "_network_metrics.csv";
    std::string topologyFileName = m_config.outputPrefix + "_topology.json";
    std::string configFileName = m_config.outputPrefix + "_config.json";
    std::string faultLogFileName = m_config.outputPrefix + "_fault_events.log";
    
    metricsFile.open(metricsFileName);
    metricsFile << "Time,NodeId,NodeType,Throughput_Mbps,Latency_ms,PacketLoss_Rate,Jitter_ms,"
                << "SignalStrength_dBm,CPU_Usage,Memory_Usage,Buffer_Occupancy,Active_Links,"
                << "Neighbor_Count,Link_Utilization,Critical_Load,Normal_Load,Energy_Level,"
                << "X_Position,Y_Position,Z_Position,Operational_Status,"
                << "Voltage_Level,Power_Stability,Degradation_Level,Fault_Severity,"
                << "Time_Of_Day_Factor,Traffic_Pattern_Factor,Seasonal_Factor\n";
    
    topologyFile.open(topologyFileName);
    configFile.open(configFileName);
    faultLogFile.open(faultLogFileName);
    
    if (m_config.enableDatabaseGeneration) {
        std::string dbPrefix = m_config.outputPrefix + "_database_";
        
        nodesDbFile.open(dbPrefix + "nodes.sql");
        linksDbFile.open(dbPrefix + "links.sql");
        anomaliesDbFile.open(dbPrefix + "anomalies.sql");
        recoveryTacticsDbFile.open(dbPrefix + "recovery_tactics.sql");
        policiesDbFile.open(dbPrefix + "policies.sql");
        trafficFlowsDbFile.open(dbPrefix + "traffic_flows.sql");
        databaseSchemaFile.open(dbPrefix + "schema.sql");
        
        std::cout << "RAG database generation: ENABLED" << std::endl;
        InitializeDatabaseStructures();
    }
    
    std::cout << "Enhanced simulation files initialized" << std::endl;
}

// **CORE SETUP METHODS (from working original)**
void EnhancedRuralNetworkRAG::SetupRobustTopology()
{
    std::cout << "Setting up RURAL NETWORK topology (50 nodes)..." << std::endl;
    
    // Create 50 nodes: 5 core, 15 distribution, 30 access
    coreNodes.Create(5);
    distributionNodes.Create(15);
    accessNodes.Create(30);
    
    allNodes.Add(coreNodes);
    allNodes.Add(distributionNodes);
    allNodes.Add(accessNodes);
    
    std::cout << "Created " << allNodes.GetN() << " nodes total" << std::endl;
    
    // **CRITICAL: Install mobility models on ALL nodes**
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    mobility.Install(allNodes);
    
    // Setup layers in order
    SetupCoreLayer();
    SetupDistributionLayer();
    SetupAccessLayer();
    
    // Setup routing and energy
    SetupRobustRouting();
    SetupEnergyModel();
    
    std::cout << "RURAL network topology completed" << std::endl;
}

void EnhancedRuralNetworkRAG::SetupCoreLayer()
{
    // Configure speeds based on mode
    if (m_config.enableVisualization) {
        p2pHelper.SetDeviceAttribute("DataRate", StringValue("1Gbps"));
        p2pHelper.SetChannelAttribute("Delay", StringValue("2ms"));
    } else {
        p2pHelper.SetDeviceAttribute("DataRate", StringValue("1Mbps"));
        p2pHelper.SetChannelAttribute("Delay", StringValue("10ms"));
    }
    std::cout << "Core layer speed: " << (m_config.useHighSpeedNetwork ? "HIGH SPEED (1Gbps)" : "DEMO SPEED (1Mbps)") << std::endl;
    // **RURAL: Position core nodes as regional hubs**
    Ptr<ListPositionAllocator> corePositions = CreateObject<ListPositionAllocator>();
    corePositions->Add(Vector(0.0, 0.0, 0.0));      // CORE-0 - Central hub
    corePositions->Add(Vector(100.0, 0.0, 0.0));    // CORE-1 - East region
    corePositions->Add(Vector(-100.0, 0.0, 0.0));   // CORE-2 - West region
    corePositions->Add(Vector(0.0, 100.0, 0.0));    // CORE-3 - North region
    corePositions->Add(Vector(0.0, -100.0, 0.0));   // CORE-4 - South region
    
    // Set positions using mobility model
    for (uint32_t i = 0; i < coreNodes.GetN(); ++i) {
        Ptr<ConstantPositionMobilityModel> mob = coreNodes.Get(i)->GetObject<ConstantPositionMobilityModel>();
        mob->SetPosition(corePositions->GetNext());
    }
    
    // **RURAL: Star topology with central hub + some redundancy**
    // Central hub connections
    for (uint32_t i = 1; i < coreNodes.GetN(); ++i) {
        NetDeviceContainer link = p2pHelper.Install(coreNodes.Get(0), coreNodes.Get(i));
        coreDevices.Add(link);
    }
    
    // **REDUNDANCY: Cross-connections for resilience**
    NetDeviceContainer link13 = p2pHelper.Install(coreNodes.Get(1), coreNodes.Get(3));
    coreDevices.Add(link13);
    NetDeviceContainer link24 = p2pHelper.Install(coreNodes.Get(2), coreNodes.Get(4));
    coreDevices.Add(link24);
    
    std::cout << "Core layer setup: 5 nodes with star+redundancy topology" << std::endl;
}

void EnhancedRuralNetworkRAG::SetupDistributionLayer()
{
    // Configure speeds
    if (m_config.enableVisualization) {
        p2pHelper.SetDeviceAttribute("DataRate", StringValue("512Kbps"));
        p2pHelper.SetChannelAttribute("Delay", StringValue("20ms"));
    } else {
        p2pHelper.SetDeviceAttribute("DataRate", StringValue("100Mbps"));
        p2pHelper.SetChannelAttribute("Delay", StringValue("10ms"));
    }
    
    // **RURAL: Position distribution nodes around regions**
    for (uint32_t i = 0; i < distributionNodes.GetN(); ++i) {
        double angle = (2.0 * M_PI * i) / distributionNodes.GetN();
        double radius = 150.0;  // Outer ring
        double x = radius * cos(angle);
        double y = radius * sin(angle);
        
        Ptr<ConstantPositionMobilityModel> mob = distributionNodes.Get(i)->GetObject<ConstantPositionMobilityModel>();
        mob->SetPosition(Vector(x, y, 0.0));
    }
    
    // **RURAL: Connect each distribution to nearest core (3:1 ratio)**
    for (uint32_t i = 0; i < distributionNodes.GetN(); ++i) {
        uint32_t coreIndex = i % coreNodes.GetN();
        NetDeviceContainer link = p2pHelper.Install(distributionNodes.Get(i), coreNodes.Get(coreIndex));
        distributionDevices.Add(link);
    }
    
    std::cout << "Distribution layer setup: 15 nodes in regional ring" << std::endl;
}

void EnhancedRuralNetworkRAG::SetupAccessLayer()
{
    // Configure speeds
    if (m_config.enableVisualization) {
        p2pHelper.SetDeviceAttribute("DataRate", StringValue("256Kbps"));
        p2pHelper.SetChannelAttribute("Delay", StringValue("50ms"));
    } else {
        p2pHelper.SetDeviceAttribute("DataRate", StringValue("50Mbps"));
        p2pHelper.SetChannelAttribute("Delay", StringValue("5ms"));
    }
    
    // **RURAL: Position access nodes organically**
    if (m_config.enableVisualization) {
        // **DEMO: Organized grid for clear visualization**
        for (uint32_t i = 0; i < accessNodes.GetN(); ++i) {
            double x = (i % 6) * 60.0 - 150.0;
            double y = (i / 6) * 60.0 - 150.0;
            
            Ptr<ConstantPositionMobilityModel> mob = accessNodes.Get(i)->GetObject<ConstantPositionMobilityModel>();
            mob->SetPosition(Vector(x, y, 0.0));
        }
    } else {
        // **RAG TRAINING: Random rural positioning**
        std::mt19937 gen(12345); // Fixed seed for reproducibility
        std::uniform_real_distribution<> dis(-250.0, 250.0);

        for (uint32_t i = 0; i < accessNodes.GetN(); ++i) {
            double x = dis(gen);
            double y = dis(gen);
            
            Ptr<ConstantPositionMobilityModel> mob = accessNodes.Get(i)->GetObject<ConstantPositionMobilityModel>();
            mob->SetPosition(Vector(x, y, 0.0));
        }
    }
    
    // **RURAL: Connect access to distribution (2:1 ratio)**
    for (uint32_t i = 0; i < accessNodes.GetN(); ++i) {
        uint32_t distIndex = i % distributionNodes.GetN();
        NetDeviceContainer link = p2pHelper.Install(accessNodes.Get(i), distributionNodes.Get(distIndex));
        accessDevices.Add(link);
    }
    
    std::cout << "Access layer setup: 30 nodes connected to distribution" << std::endl;
}

// **ROUTING SETUP (from working original)**
void EnhancedRuralNetworkRAG::SetupRobustRouting()
{
    // Use SIMPLE global routing for guaranteed functionality
    stack.Install(allNodes);
    
    // Assign IP addresses systematically
    address.SetBase("10.1.1.0", "255.255.255.0");
    
    // Core network IPs
    for (uint32_t i = 0; i < coreDevices.GetN(); i += 2) {
        Ipv4InterfaceContainer iface = address.Assign(NetDeviceContainer(coreDevices.Get(i), coreDevices.Get(i+1)));
        allInterfaces.push_back(iface);
        address.NewNetwork();
    }
    
    // Distribution network IPs
    for (uint32_t i = 0; i < distributionDevices.GetN(); i += 2) {
        Ipv4InterfaceContainer iface = address.Assign(NetDeviceContainer(distributionDevices.Get(i), distributionDevices.Get(i+1)));
        allInterfaces.push_back(iface);
        address.NewNetwork();
    }
    
    // Access network IPs
    for (uint32_t i = 0; i < accessDevices.GetN(); i += 2) {
        Ipv4InterfaceContainer iface = address.Assign(NetDeviceContainer(accessDevices.Get(i), accessDevices.Get(i+1)));
        allInterfaces.push_back(iface);
        address.NewNetwork();
    }
    
    // **CRITICAL: Populate routing tables**
    Ipv4GlobalRoutingHelper::PopulateRoutingTables();
    
    std::cout << "Routing setup complete with " << allInterfaces.size() << " interface pairs" << std::endl;
}

void EnhancedRuralNetworkRAG::SetupEnergyModel()
{
    BasicEnergySourceHelper basicSourceHelper;
    basicSourceHelper.Set("BasicEnergySourceInitialEnergyJ", DoubleValue(10000));
    energy::EnergySourceContainer sources = basicSourceHelper.Install(allNodes);
    
    std::cout << "Energy model setup complete" << std::endl;
}

// **IMPROVED TRAFFIC SETUP**
void EnhancedRuralNetworkRAG::SetupRobustApplications()
{
    if (m_config.enableVisualization) {
        CreateComprehensiveTraffic();
    } else {
        CreateBaselineTraffic();
    }
    
    std::cout << "Applications setup complete for " << m_config.mode << " mode" << std::endl;
}

void EnhancedRuralNetworkRAG::CreateComprehensiveTraffic()
{
    std::cout << "Creating COMPREHENSIVE traffic for ALL nodes..." << std::endl;
    
    uint16_t port = 8080;
    
    // **FIXED: Create servers on ALL access nodes for guaranteed traffic**
    for (uint32_t i = 0; i < accessNodes.GetN(); ++i) {
        UdpEchoServerHelper echoServer(port);
        ApplicationContainer serverApp = echoServer.Install(accessNodes.Get(i));
        serverApp.Start(Seconds(1.0));
        serverApp.Stop(Seconds(m_config.totalSimulationTime - 10.0));
        sinkApps.Add(serverApp);
        
        port++;
        if (port > 8200) port = 8080; // Wrap around
    }
    
    // **FIXED: Create clients to ensure EVERY access node gets traffic**
    port = 8080;
    for (uint32_t coreIdx = 0; coreIdx < coreNodes.GetN(); ++coreIdx) {
        // Each core sends to multiple access nodes
        for (uint32_t accessIdx = coreIdx; accessIdx < accessNodes.GetN(); accessIdx += coreNodes.GetN()) {
            
            // Find IP address for this access node
            uint32_t interfaceIndex = (coreDevices.GetN() / 2) + (distributionDevices.GetN() / 2) + accessIdx;
            if (interfaceIndex < allInterfaces.size()) {
                Ipv4Address targetAddr = allInterfaces[interfaceIndex].GetAddress(0);
                
                UdpEchoClientHelper echoClient(targetAddr, port);
                echoClient.SetAttribute("MaxPackets", UintegerValue(100));
                echoClient.SetAttribute("Interval", TimeValue(Seconds(3.0)));  // Slow for visibility
                echoClient.SetAttribute("PacketSize", UintegerValue(1024));
                
                ApplicationContainer clientApp = echoClient.Install(coreNodes.Get(coreIdx));
                clientApp.Start(Seconds(15.0 + coreIdx * 2.0));
                clientApp.Stop(Seconds(m_config.totalSimulationTime - 10.0));
                sourceApps.Add(clientApp);
                
                std::cout << "Traffic: CORE-" << coreIdx << " → ACC-" << accessIdx 
                         << " (" << targetAddr << ":" << port << ")" << std::endl;
            }
            
            port++;
            if (port > 8200) port = 8080;
        }
    }
    
    std::cout << "✅ COMPREHENSIVE traffic configured - ALL nodes will receive packets!" << std::endl;
}

void EnhancedRuralNetworkRAG::CreateBaselineTraffic()
{
    std::cout << "Creating baseline traffic for RAG training..." << std::endl;
    
    uint16_t port = 8080;
    
    // Create servers on every 3rd access node
    for (uint32_t i = 0; i < accessNodes.GetN(); i += 3) {
        UdpEchoServerHelper echoServer(port);
        ApplicationContainer serverApp = echoServer.Install(accessNodes.Get(i));
        serverApp.Start(Seconds(1.0));
        serverApp.Stop(Seconds(m_config.totalSimulationTime));
        sinkApps.Add(serverApp);
        port++;
    }
    
    // Create clients on core nodes
    port = 8080;
    for (uint32_t i = 0; i < coreNodes.GetN(); ++i) {
        for (uint32_t j = 0; j < accessNodes.GetN(); j += 10) {
            uint32_t interfaceIndex = (coreDevices.GetN() / 2) + (distributionDevices.GetN() / 2) + j;
            if (interfaceIndex < allInterfaces.size()) {
                Ipv4Address targetAddr = allInterfaces[interfaceIndex].GetAddress(0);
                
                UdpEchoClientHelper echoClient(targetAddr, port);
                echoClient.SetAttribute("MaxPackets", UintegerValue(1000));
                echoClient.SetAttribute("Interval", TimeValue(Seconds(1.0)));
                echoClient.SetAttribute("PacketSize", UintegerValue(512));
                
                ApplicationContainer clientApp = echoClient.Install(coreNodes.Get(i));
                clientApp.Start(Seconds(2.0 + i * 0.1));
                clientApp.Stop(Seconds(m_config.totalSimulationTime));
                sourceApps.Add(clientApp);
            }
        }
    }
    
    std::cout << "Baseline traffic configured for RAG training" << std::endl;
}

// **NETANIM SETUP (from working original)**
void EnhancedRuralNetworkRAG::SetupRobustNetAnimVisualization()
{
    if (m_config.enableVisualization) {
        std::cout << "Setting up NetAnim visualization..." << std::endl;
        
        std::string animFileName = m_config.outputPrefix + "_network_animation.xml";
        animInterface = new AnimationInterface(animFileName);
        
        // **CRITICAL: Enable packet metadata**
        animInterface->EnablePacketMetadata(true);
        animInterface->SetMaxPktsPerTraceFile(50000);
        animInterface->SetMobilityPollInterval(Seconds(1));
        
        // Set node colors and descriptions
        for (uint32_t i = 0; i < allNodes.GetN(); ++i) {
            std::string nodeDesc = GetNodeVisualName(i);
            
            if (i < 5) {
                animInterface->UpdateNodeColor(allNodes.Get(i), 0, 100, 255);  // Blue core
                animInterface->UpdateNodeSize(allNodes.Get(i), 3.0, 3.0);
            } else if (i < 20) {
                animInterface->UpdateNodeColor(allNodes.Get(i), 0, 255, 0);    // Green distribution
                animInterface->UpdateNodeSize(allNodes.Get(i), 2.0, 2.0);
            } else {
                animInterface->UpdateNodeColor(allNodes.Get(i), 255, 255, 0);  // Yellow access
                animInterface->UpdateNodeSize(allNodes.Get(i), 1.5, 1.5);
            }
            
            animInterface->UpdateNodeDescription(allNodes.Get(i), nodeDesc);
        }
        
        std::cout << "NetAnim configured: " << animFileName << std::endl;
    }
}

void EnhancedRuralNetworkRAG::ScheduleGradualFaultPatterns()
{
    std::cout << "Scheduling fault patterns..." << std::endl;
    
    if (m_config.mode == "fault_demo") {
        // **BETTER TIMING: Later in simulation for visibility**
        CreateRealisticFiberCutPattern(0, 1, Seconds(60.0));   // 1 minute
        CreateRealisticFiberCutPattern(5, 20, Seconds(120.0)); // 2 minutes
        
        CreateRealisticPowerFluctuationPattern(7, Seconds(90.0));   // 1.5 minutes
        CreateRealisticPowerFluctuationPattern(25, Seconds(150.0)); // 2.5 minutes
        
        std::cout << "🎬 DEMO MODE: 4 fault patterns scheduled at better times" << std::endl;
    }
    
    if (m_config.enableFaultVisualization && m_config.enableVisualization) {
        std::cout << "📺 Scheduling visual fault updates every 1 second..." << std::endl;
        Simulator::Schedule(Seconds(1.0), &EnhancedRuralNetworkRAG::ProcessFaultVisualization, this);
    }
}


void EnhancedRuralNetworkRAG::CreateRealisticFiberCutPattern(uint32_t nodeA, uint32_t nodeB, Time startTime)
{
    std::string nodeAName = GetNodeVisualName(nodeA);
    std::string nodeBName = GetNodeVisualName(nodeB);
    
    GradualFaultPattern pattern;
    pattern.targetNode = nodeA;
    pattern.connectedNode = nodeB;
    pattern.faultType = "fiber_cut";
    pattern.faultDescription = "FIBER CUT between " + nodeAName + " and " + nodeBName;
    pattern.startDegradation = startTime;
    pattern.faultOccurrence = startTime + Seconds(45.0);
    pattern.faultDuration = Seconds(999999.0);  // **NO AUTO-RECOVERY**
    pattern.degradationRate = 0.8;
    pattern.severity = 1.0;
    pattern.isActive = true;
    pattern.currentSeverity = 0.0;
    pattern.visualIndicatorActive = false;
    pattern.visualMessage = "🔥 FIBER CUT: " + nodeAName + "↔" + nodeBName;
    pattern.anomalyId = GenerateAnomalyId();
    
    gradualFaults.push_back(pattern);
    
    // Also create pattern for connected node
    pattern.targetNode = nodeB;
    pattern.connectedNode = nodeA;
    pattern.severity = 1.0;
    pattern.anomalyId = GenerateAnomalyId();
    gradualFaults.push_back(pattern);
    
    Simulator::Schedule(startTime + Seconds(45.0), 
                       &EnhancedRuralNetworkRAG::HideFiberLink, this, nodeA, nodeB);
    
    // **NO RECOVERY SCHEDULING**
    std::cout << "📋 FIBER CUT: " << nodeAName << "↔" << nodeBName 
              << " at " << startTime.GetSeconds() << "s (NO AUTO-RECOVERY)" << std::endl;
}

void EnhancedRuralNetworkRAG::CreateRealisticPowerFluctuationPattern(uint32_t nodeId, Time startTime)
{
    std::string nodeName = GetNodeVisualName(nodeId);
    
    GradualFaultPattern pattern;
    pattern.targetNode = nodeId;
    pattern.connectedNode = 0;
    pattern.faultType = "power_fluctuation";
    pattern.faultDescription = "POWER FLUCTUATION at " + nodeName;
    pattern.startDegradation = startTime;
    pattern.faultOccurrence = startTime + Seconds(60.0);
    pattern.faultDuration = Seconds(999999.0);  // **NO AUTO-RECOVERY**
    pattern.degradationRate = 0.6;
    pattern.severity = 0.7;
    pattern.isActive = true;
    pattern.currentSeverity = 0.0;
    pattern.visualIndicatorActive = false;
    pattern.visualMessage = "⚡ POWER ISSUE: " + nodeName;
    pattern.anomalyId = GenerateAnomalyId();
    
    gradualFaults.push_back(pattern);
    
    // **NO RECOVERY SCHEDULING**
    std::cout << "📋 POWER FLUCTUATION: " << nodeName 
              << " at " << startTime.GetSeconds() << "s (NO AUTO-RECOVERY)" << std::endl;
}

// **FAULT PROGRESSION (NO RECOVERY)**
void EnhancedRuralNetworkRAG::UpdateFaultProgression()
{
    Time currentTime = Simulator::Now();
    double currentSeconds = currentTime.GetSeconds();
    
    std::cout << "🔍 DEBUG: UpdateFaultProgression called at " << currentSeconds << "s" << std::endl;
    std::cout << "🔍 DEBUG: Total faults: " << gradualFaults.size() << std::endl;
    
    for (auto& fault : gradualFaults) {
        if (!fault.isActive) continue;
        
        double previousSeverity = fault.currentSeverity;
        std::string nodeName = GetNodeVisualName(fault.targetNode);
        
        if (currentTime < fault.startDegradation) {
            fault.currentSeverity = 0.0;
        }
        else if (currentTime < fault.faultOccurrence) {
            // **GRADUAL DEGRADATION PHASE**
            double progress = (currentTime - fault.startDegradation).GetSeconds() / 
                            (fault.faultOccurrence - fault.startDegradation).GetSeconds();
            fault.currentSeverity = progress * fault.degradationRate;
            
            // **DEBUG OUTPUT**
            std::cout << "🟡 DEGRADING: " << nodeName << " (" << fault.faultType 
                      << ") severity=" << (int)(fault.currentSeverity * 100) << "%" << std::endl;
            
            // **FORCE COLOR UPDATE**
            if (m_config.enableFaultVisualization) {
                UpdateGradualVisualization(fault);
            }
        }
        else {
            // **PEAK FAULT PHASE**
            fault.currentSeverity = fault.severity;
            
            std::cout << "🔴 PEAK FAULT: " << nodeName << " (" << fault.faultType 
                      << ") severity=100%" << std::endl;
            
            // **FORCE PEAK VISUALIZATION**
            if (m_config.enableFaultVisualization) {
                UpdatePeakVisualization(fault);
            }
        }
        
        // **TRIGGER EVENTS**
        if (m_config.enableFaultVisualization) {
            if (previousSeverity == 0.0 && fault.currentSeverity > 0.0) {
                AnnounceFaultEvent(fault, "DEGRADATION_START");
            }
            else if (previousSeverity < fault.severity && fault.currentSeverity >= fault.severity) {
                AnnounceFaultEvent(fault, "FAULT_PEAK");
            }
        }
    }
}

// **FIXED: Visual methods WITHOUT size changes or percentages**
std::string EnhancedRuralNetworkRAG::GetNodeVisualName(uint32_t nodeId)
{
    if (nodeId < 5) {
        return "CORE-" + std::to_string(nodeId);
    } else if (nodeId < 20) {
        return "DIST-" + std::to_string(nodeId - 5);
    } else {
        return "ACC-" + std::to_string(nodeId - 20);
    }
}

void EnhancedRuralNetworkRAG::HideFiberLink(uint32_t nodeA, uint32_t nodeB)
{
    std::string nodeAName = GetNodeVisualName(nodeA);
    std::string nodeBName = GetNodeVisualName(nodeB);
    
    std::cout << "🔥 ENHANCED FIBER LINK BLOCKING: " << nodeAName << " ↔ " << nodeBName << std::endl;
    
    // **METHOD 1: Error Model on Both Devices**
    Ptr<Node> nodeAPtr = allNodes.Get(nodeA);
    Ptr<Node> nodeBPtr = allNodes.Get(nodeB);
    
    bool linkFound = false;
    
    // Find and block the channel between these nodes
    for (uint32_t i = 0; i < nodeAPtr->GetNDevices(); ++i) {
        Ptr<NetDevice> deviceA = nodeAPtr->GetDevice(i);
        Ptr<PointToPointNetDevice> p2pDeviceA = DynamicCast<PointToPointNetDevice>(deviceA);
        
        if (p2pDeviceA) {
            Ptr<Channel> channel = p2pDeviceA->GetChannel();
            Ptr<PointToPointChannel> p2pChannel = DynamicCast<PointToPointChannel>(channel);
            
            if (p2pChannel && p2pChannel->GetNDevices() == 2) {
                // Check if this channel connects to nodeB
                Ptr<NetDevice> deviceB = nullptr;
                if (p2pChannel->GetDevice(0) == deviceA) {
                    deviceB = p2pChannel->GetDevice(1);
                } else {
                    deviceB = p2pChannel->GetDevice(0);
                }
                
                if (deviceB && deviceB->GetNode()->GetId() == nodeB) {
                    linkFound = true;
                    
                    // **AGGRESSIVE BLOCKING: Apply error model to BOTH devices**
                    Ptr<RateErrorModel> errorModelA = CreateObject<RateErrorModel>();
                    errorModelA->SetAttribute("ErrorRate", DoubleValue(1.0));
                    errorModelA->SetAttribute("ErrorUnit", StringValue("ERROR_UNIT_PACKET"));
                    
                    Ptr<RateErrorModel> errorModelB = CreateObject<RateErrorModel>();
                    errorModelB->SetAttribute("ErrorRate", DoubleValue(1.0));
                    errorModelB->SetAttribute("ErrorUnit", StringValue("ERROR_UNIT_PACKET"));
                    
                    // Apply to both directions
                    p2pDeviceA->SetAttribute("ReceiveErrorModel", PointerValue(errorModelA));
                    DynamicCast<PointToPointNetDevice>(deviceB)->SetAttribute("ReceiveErrorModel", PointerValue(errorModelB));
                    
                    std::cout << "✅ 100% packet loss applied to BOTH devices" << std::endl;
                    
                    // **METHOD 2: Additional channel-level blocking**
                    // Set the channel to drop all packets by disabling transmission
                    p2pChannel->SetAttribute("Delay", StringValue("999999s")); // Infinite delay
                    
                    std::cout << "✅ Channel delay set to infinite" << std::endl;
                    break;
                }
            }
        }
    }
    
    if (!linkFound) {
        std::cout << "❌ WARNING: Link between " << nodeAName << " and " << nodeBName << " not found!" << std::endl;
    }
    
    // **METHOD 3: Disable the link at routing level**
    linkStatus[std::make_pair(std::min(nodeA, nodeB), std::max(nodeA, nodeB))] = false;
    
    // **METHOD 4: Force immediate routing table update**
    Simulator::ScheduleNow(&Ipv4GlobalRoutingHelper::PopulateRoutingTables);
    
    if (animInterface) {
        // Visual indication
        std::string breakMsg = "❌ LINK CUT to " + nodeBName;
        animInterface->UpdateNodeDescription(allNodes.Get(nodeA), nodeAName + "\n" + breakMsg);
        
        breakMsg = "❌ LINK CUT to " + nodeAName;
        animInterface->UpdateNodeDescription(allNodes.Get(nodeB), nodeBName + "\n" + breakMsg);
        
        std::cout << "🔴 VISUAL: Fiber link " << nodeAName << "↔" << nodeBName << " BLOCKED" << std::endl;
    }
    
    // Update database records
    if (m_config.enableDatabaseGeneration) {
        for (auto& link : linkRecords) {
            std::string nodeAId = GenerateNodeId(nodeA);
            std::string nodeBId = GenerateNodeId(nodeB);
            
            if ((link.sourceNodeId == nodeAId && link.destinationNodeId == nodeBId) ||
                (link.sourceNodeId == nodeBId && link.destinationNodeId == nodeAId)) {
                link.status = "down";
                link.currentBandwidthUtilPercent = 0.0;
                link.packetLossRate = 1.0;
                link.latencyMs = 999999.0; // Infinite latency
                break;
            }
        }
    }
    
    std::cout << "🚫 COMPLETE LINK BLOCKING APPLIED: " << nodeAName << "↔" << nodeBName << std::endl;
}

void EnhancedRuralNetworkRAG::RestoreFiberLink(uint32_t nodeA, uint32_t nodeB)
{
    if (!animInterface) return;
    
    std::string nodeAName = GetNodeVisualName(nodeA);
    std::string nodeBName = GetNodeVisualName(nodeB);
    
    // Restore normal descriptions
    animInterface->UpdateNodeDescription(allNodes.Get(nodeA), nodeAName);
    animInterface->UpdateNodeDescription(allNodes.Get(nodeB), nodeBName);
    
    // Restore link status
    linkStatus[std::make_pair(std::min(nodeA, nodeB), std::max(nodeA, nodeB))] = true;
    
    std::cout << "🟢 VISUAL: Fiber link " << nodeAName << "↔" << nodeBName << " RESTORED" << std::endl;
}

void EnhancedRuralNetworkRAG::ShowPowerIssue(uint32_t nodeId)
{
    if (!animInterface) return;
    
    std::string nodeName = GetNodeVisualName(nodeId);
    
    // **FIXED: Simple power issue indication (NO PERCENTAGES)**
    std::string powerMsg = "⚡ POWER ISSUE";
    animInterface->UpdateNodeDescription(allNodes.Get(nodeId), nodeName + "\n" + powerMsg);
    
    std::cout << "🟡 VISUAL: Power issue indicator shown on " << nodeName << std::endl;
}

void EnhancedRuralNetworkRAG::HidePowerIssue(uint32_t nodeId)
{
    if (!animInterface) return;
    
    std::string nodeName = GetNodeVisualName(nodeId);
    
    // Restore normal description
    animInterface->UpdateNodeDescription(allNodes.Get(nodeId), nodeName);
    
    std::cout << "🟢 VISUAL: Power issue resolved on " << nodeName << std::endl;
}

// **FIXED: Visual status updates WITHOUT size changes or percentages**
void EnhancedRuralNetworkRAG::ProcessFaultVisualization()
{
    if (!m_config.enableFaultVisualization || !animInterface) {
        return;
    }
    
    UpdateVisualFaultIndicators();
    
    if (Simulator::Now().GetSeconds() < m_config.totalSimulationTime - 1.0) {
        Simulator::Schedule(Seconds(1.0), &EnhancedRuralNetworkRAG::ProcessFaultVisualization, this);
    }
}

void EnhancedRuralNetworkRAG::UpdateVisualFaultIndicators()
{
    for (const auto& fault : gradualFaults) {
        if (fault.isActive && fault.currentSeverity > 0.0) {
            if (fault.currentSeverity > 0.8) {
                UpdateNodeVisualStatus(fault.targetNode, "CRITICAL");
            } else if (fault.currentSeverity > 0.5) {
                UpdateNodeVisualStatus(fault.targetNode, "HIGH");
            } else if (fault.currentSeverity > 0.2) {
                UpdateNodeVisualStatus(fault.targetNode, "MEDIUM");
            } else {
                UpdateNodeVisualStatus(fault.targetNode, "LOW");
            }
        } else if (!fault.isActive) {
            UpdateNodeVisualStatus(fault.targetNode, "NORMAL");
        }
    }
}

void EnhancedRuralNetworkRAG::UpdateNodeVisualStatus(uint32_t nodeId, const std::string& status)
{
    if (!animInterface) return;
    
    // **FIXED: Only color changes, NO size changes**
    if (status == "CRITICAL") {
        animInterface->UpdateNodeColor(allNodes.Get(nodeId), 255, 0, 0);  // Red
        // **NO SIZE CHANGE**
    } else if (status == "HIGH") {
        animInterface->UpdateNodeColor(allNodes.Get(nodeId), 255, 165, 0);  // Orange
    } else if (status == "MEDIUM") {
        animInterface->UpdateNodeColor(allNodes.Get(nodeId), 255, 255, 0);  // Yellow
    } else if (status == "LOW") {
        animInterface->UpdateNodeColor(allNodes.Get(nodeId), 255, 200, 0);  // Light yellow
    } else { // NORMAL
        // **RESTORE ORIGINAL COLORS**
        if (nodeId < 5) {
            animInterface->UpdateNodeColor(allNodes.Get(nodeId), 0, 100, 255);  // Blue core
        } else if (nodeId < 20) {
            animInterface->UpdateNodeColor(allNodes.Get(nodeId), 0, 255, 0);    // Green dist
        } else {
            animInterface->UpdateNodeColor(allNodes.Get(nodeId), 255, 255, 0);  // Yellow access
        }
    }
}

void EnhancedRuralNetworkRAG::AnnounceFaultEvent(const GradualFaultPattern& fault, const std::string& eventType)
{
    // **RAG DATABASE: Classify and record anomaly**
    if (m_config.enableAnomalyClassification) {
        ClassifyAndRecordAnomaly(fault, eventType);
    }
    
    double currentTime = Simulator::Now().GetSeconds();
    std::string nodeAName = GetNodeVisualName(fault.targetNode);
    std::string nodeBName = fault.connectedNode > 0 ? GetNodeVisualName(fault.connectedNode) : "";
    
    FaultEvent event;
    event.timestamp = currentTime;
    event.eventType = eventType;
    event.faultType = fault.faultType;
    event.affectedNodes = {fault.targetNode};
    if (fault.connectedNode > 0) {
        event.affectedNodes.push_back(fault.connectedNode);
    }
    
    std::string visualNodes = nodeAName;
    if (!nodeBName.empty()) {
        visualNodes += "↔" + nodeBName;
    }
    
    if (eventType == "DEGRADATION_START") {
        event.description = "🟡 DEGRADATION STARTED: " + fault.faultDescription;
        event.visualEffect = "Nodes " + visualNodes + " changing color";
    } else if (eventType == "FAULT_PEAK") {
        event.description = "🔴 FAULT CRITICAL: " + fault.faultDescription;
        event.visualEffect = "Nodes " + visualNodes + " turned RED";
        
        // **TRIGGER LINK DISABLING**
        if (fault.faultType == "fiber_cut" && fault.connectedNode > 0) {
            HideFiberLink(fault.targetNode, fault.connectedNode);
        } else if (fault.faultType == "power_fluctuation") {
            ShowPowerIssue(fault.targetNode);
        }
    }
    
    LogFaultEvent(event);
    
    std::cout << std::endl;
    std::cout << "📢 ============ FAULT EVENT ============" << std::endl;
    std::cout << "⏰ TIME: " << std::fixed << std::setprecision(1) << currentTime << "s" << std::endl;
    std::cout << "🎯 EVENT: " << event.description << std::endl;
    std::cout << "🎨 VISUAL: " << event.visualEffect << std::endl;
    std::cout << "🆔 ANOMALY ID: " << fault.anomalyId.substr(0, 8) << "..." << std::endl;
    std::cout << "=======================================" << std::endl;
    std::cout << std::endl;
}

void EnhancedRuralNetworkRAG::LogFaultEvent(const FaultEvent& event)
{
    faultLogFile << "[" << std::fixed << std::setprecision(1) << event.timestamp << "s] "
                 << event.eventType << " - " << event.description << std::endl;
    faultLogFile << "    Affected nodes: ";
    for (uint32_t nodeId : event.affectedNodes) {
        faultLogFile << nodeId << " ";
    }
    faultLogFile << std::endl;
    faultLogFile << "    Visual effect: " << event.visualEffect << std::endl;
    faultLogFile << std::endl;
    faultLogFile.flush();
    
    faultEvents.push_back(event);
}

// **BASELINE VARIATION METHODS (from working original)**
double EnhancedRuralNetworkRAG::GetTimeOfDayMultiplier()
{
    double currentTime = Simulator::Now().GetSeconds();
    double timeOfDay = fmod(currentTime, 86400.0);
    double hour = timeOfDay / 3600.0;
    
    if (hour >= 8.0 && hour <= 18.0) {
        return 1.0 + 0.3 * sin((hour - 8.0) / 10.0 * M_PI);
    } else {
        return 0.6 + 0.2 * sin(hour / 24.0 * 2 * M_PI);
    }
}

double EnhancedRuralNetworkRAG::GetTrafficPatternMultiplier()
{
    double currentTime = Simulator::Now().GetSeconds();
    double weekTime = fmod(currentTime, 604800.0);
    double dayOfWeek = weekTime / 86400.0;
    
    if (dayOfWeek >= 1.0 && dayOfWeek <= 5.0) {
        return 1.0 + 0.2 * sin((dayOfWeek - 1.0) / 4.0 * M_PI);
    } else {
        return 0.8 + 0.1 * sin(dayOfWeek / 7.0 * 2 * M_PI);
    }
}

double EnhancedRuralNetworkRAG::GetSeasonalVariation()
{
    double currentTime = Simulator::Now().GetSeconds();
    double seasonalCycle = sin(currentTime / 2592000.0 * 2 * M_PI);
    return 1.0 + 0.1 * seasonalCycle;
}

double EnhancedRuralNetworkRAG::CalculateNodeDegradation(uint32_t nodeId, const std::string& metric)
{
    double maxDegradation = 0.0;
    
    for (const auto& fault : gradualFaults) {
        if (fault.targetNode == nodeId && fault.isActive) {
            double degradation = fault.currentSeverity;
            
            if (fault.faultType == "fiber_cut") {
                if (metric == "throughput") degradation *= 0.9;
                else if (metric == "latency") degradation *= 0.8;
                else if (metric == "packet_loss") degradation *= 1.0;
            }
            else if (fault.faultType == "power_fluctuation") {
                if (metric == "voltage") degradation *= 1.0;
                else if (metric == "throughput") degradation *= 0.4;
            }
            
            maxDegradation = std::max(maxDegradation, degradation);
        }
    }
    
    return maxDegradation;
}

// **DATA COLLECTION**
void EnhancedRuralNetworkRAG::CollectComprehensiveMetrics()
{
    // Update fault progression if enabled
    if (m_config.enableFaultInjection && Simulator::Now().GetSeconds() >= m_config.faultStartTime) {
        UpdateFaultProgression();
    }
    
    // **RAG DATABASE: Collect enhanced data**
    if (m_config.enableDatabaseGeneration) {
        CollectEnhancedNodeData();
        CollectLinkMetrics();
        UpdateTrafficFlows();
    }
    
    // Get baseline variation factors
    double timeOfDayFactor = GetTimeOfDayMultiplier();
    double trafficPatternFactor = GetTrafficPatternMultiplier();
    double seasonalFactor = GetSeasonalVariation();
    
    // Collect metrics for all nodes
    for (uint32_t i = 0; i < allNodes.GetN(); ++i) {
        NodeMetrics metrics = GetEnhancedNodeMetrics(i);
        
        // Apply baseline variations if not in fault period
        if (!m_config.enableFaultInjection || Simulator::Now().GetSeconds() < m_config.faultStartTime) {
            metrics.throughputMbps *= timeOfDayFactor * trafficPatternFactor * seasonalFactor;
            metrics.latencyMs *= (2.0 - timeOfDayFactor);
            metrics.cpuUsage *= timeOfDayFactor;
            metrics.linkUtilization *= trafficPatternFactor;
            
            // Add realistic variations
            metrics.throughputMbps *= (0.95 + (rand() % 100) / 1000.0);
            metrics.latencyMs *= (0.95 + (rand() % 100) / 1000.0);
            metrics.voltageLevel += (rand() % 10 - 5) * 0.1;
        }
        
        metricsFile << std::fixed << std::setprecision(3)
                   << Simulator::Now().GetSeconds() << ","
                   << metrics.nodeId << ","
                   << metrics.nodeType << ","
                   << metrics.throughputMbps << ","
                   << metrics.latencyMs << ","
                   << metrics.packetLossRate << ","
                   << metrics.jitterMs << ","
                   << metrics.signalStrengthDbm << ","
                   << metrics.cpuUsage << ","
                   << metrics.memoryUsage << ","
                   << metrics.bufferOccupancy << ","
                   << metrics.activeLinks << ","
                   << metrics.neighborCount << ","
                   << metrics.linkUtilization << ","
                   << metrics.criticalServiceLoad << ","
                   << metrics.normalServiceLoad << ","
                   << metrics.energyLevel << ","
                   << metrics.position.x << ","
                   << metrics.position.y << ","
                   << metrics.position.z << ","
                   << (metrics.isOperational ? 1 : 0) << ","
                   << metrics.voltageLevel << ","
                   << metrics.powerStability << ","
                   << metrics.degradationLevel << ","
                   << metrics.faultSeverity << ","
                   << timeOfDayFactor << ","
                   << trafficPatternFactor << ","
                   << seasonalFactor << "\n";
    }
    
    metricsFile.flush();
    
    // Schedule next collection
    if (Simulator::Now().GetSeconds() < m_config.totalSimulationTime - m_config.dataCollectionInterval) {
        Simulator::Schedule(Seconds(m_config.dataCollectionInterval), 
                          &EnhancedRuralNetworkRAG::CollectComprehensiveMetrics, this);
    }
}

EnhancedRuralNetworkRAG::NodeMetrics EnhancedRuralNetworkRAG::GetEnhancedNodeMetrics(uint32_t nodeId)
{
    NodeMetrics metrics;
    metrics.nodeId = nodeId;
    
    // Determine node type
    if (nodeId < 5) {
        metrics.nodeType = "core";
    } else if (nodeId < 20) {
        metrics.nodeType = "distribution";
    } else {
        metrics.nodeType = "access";
    }
    
    Ptr<Node> node = allNodes.Get(nodeId);
    Ptr<MobilityModel> mobility = node->GetObject<MobilityModel>();
    if (mobility) {
        metrics.position = mobility->GetPosition();
    }
    
    // Get degradation factors
    double throughputDegradation = CalculateNodeDegradation(nodeId, "throughput");
    double latencyDegradation = CalculateNodeDegradation(nodeId, "latency");
    double packetLossDegradation = CalculateNodeDegradation(nodeId, "packet_loss");
    double voltageDegradation = CalculateNodeDegradation(nodeId, "voltage");
    double operationalDegradation = CalculateNodeDegradation(nodeId, "operational");
    
    // Store degradation and severity levels
    metrics.degradationLevel = std::max({throughputDegradation, latencyDegradation, voltageDegradation});
    metrics.faultSeverity = operationalDegradation;
    
    // Generate realistic base metrics
    if (metrics.nodeType == "core") {
        metrics.throughputMbps = (800.0 + (rand() % 200) - 100) * (1.0 - throughputDegradation);
        metrics.latencyMs = (5.0 + (rand() % 10)) * (1.0 + latencyDegradation * 20);
        metrics.packetLossRate = (0.001 + (rand() % 10) * 0.0001) + packetLossDegradation * 0.8;
        metrics.activeLinks = 4;
    } else if (metrics.nodeType == "distribution") {
        metrics.throughputMbps = (60.0 + (rand() % 40) - 20) * (1.0 - throughputDegradation);
        metrics.latencyMs = (15.0 + (rand() % 20)) * (1.0 + latencyDegradation * 15);
        metrics.packetLossRate = (0.005 + (rand() % 10) * 0.001) + packetLossDegradation * 0.6;
        metrics.activeLinks = 3;
    } else {
        metrics.throughputMbps = (25.0 + (rand() % 30) - 15) * (1.0 - throughputDegradation);
        metrics.latencyMs = (25.0 + (rand() % 35)) * (1.0 + latencyDegradation * 10);
        metrics.packetLossRate = (0.01 + (rand() % 20) * 0.001) + packetLossDegradation * 0.5;
        metrics.activeLinks = 1;
    }
    
    // Apply voltage degradation
    metrics.voltageLevel = (220.0 + (rand() % 20) - 10) * (1.0 - voltageDegradation * 0.3);
    metrics.powerStability = (0.95 + (rand() % 10) * 0.001) * (1.0 - voltageDegradation * 0.2);
    
    // Operational status
    metrics.isOperational = operationalDegradation < 0.8;
    
    // Ensure realistic bounds
    metrics.throughputMbps = std::max(0.0, metrics.throughputMbps);
    metrics.latencyMs = std::max(1.0, metrics.latencyMs);
    metrics.packetLossRate = std::min(1.0, std::max(0.0, metrics.packetLossRate));
    metrics.voltageLevel = std::max(100.0, std::min(300.0, metrics.voltageLevel));
    metrics.powerStability = std::max(0.1, std::min(1.0, metrics.powerStability));
    
    // Other metrics
    metrics.jitterMs = metrics.latencyMs * 0.1 + (rand() % 5);
    metrics.signalStrengthDbm = -60.0 - (rand() % 30);
    metrics.cpuUsage = 30.0 + (rand() % 50);
    metrics.memoryUsage = 40.0 + (rand() % 40);
    metrics.bufferOccupancy = 20.0 + (rand() % 60);
    metrics.neighborCount = metrics.activeLinks;
    metrics.linkUtilization = 30.0 + (rand() % 50);
    metrics.criticalServiceLoad = 10.0 + (rand() % 30);
    metrics.normalServiceLoad = 40.0 + (rand() % 40);
    metrics.energyLevel = 100.0 - (Simulator::Now().GetSeconds() / m_config.totalSimulationTime) * 20.0;
    
    return metrics;
}

// **RAG DATABASE METHODS**
std::string EnhancedRuralNetworkRAG::GenerateAnomalyId()
{
    return SimpleIdGenerator::GenerateId("anomaly");
}

std::string EnhancedRuralNetworkRAG::GenerateLinkId(uint32_t nodeA, uint32_t nodeB)
{
    uint32_t minNode = std::min(nodeA, nodeB);
    uint32_t maxNode = std::max(nodeA, nodeB);
    return "link_" + GenerateNodeId(minNode) + "_" + GenerateNodeId(maxNode);
}

std::string EnhancedRuralNetworkRAG::GenerateNodeId(uint32_t nodeId)
{
    if (nodeId < 5) {
        return "CORE-" + std::to_string(nodeId);
    } else if (nodeId < 20) {
        return "DIST-" + std::to_string(nodeId - 5);
    } else {
        return "ACC-" + std::to_string(nodeId - 20);
    }
}

std::string EnhancedRuralNetworkRAG::GenerateFlowId(uint32_t source, uint32_t dest)
{
    return "flow_" + GenerateNodeId(source) + "_to_" + GenerateNodeId(dest) + "_" + 
           std::to_string((int)Simulator::Now().GetSeconds());
}

void EnhancedRuralNetworkRAG::InitializeDatabaseStructures()
{
    if (!m_config.enableDatabaseGeneration) return;
    
    std::cout << "Initializing RAG database structures..." << std::endl;
    InitializeReferenceData();
    LoadRecoveryTactics();
    LoadPolicyKnowledgeBase();
    std::cout << "Database structures initialized successfully" << std::endl;
}

void EnhancedRuralNetworkRAG::InitializeReferenceData()
{
    networkLayers.push_back({1, "Core", "High-capacity backbone routing and switching"});
    networkLayers.push_back({2, "Distribution", "Regional traffic aggregation and distribution"});
    networkLayers.push_back({3, "Access", "End-user connection points and edge access"});
    
    nodeTypes.push_back({1, "Core_Router", "High-performance core network router", "Inter-region routing and traffic management"});
    nodeTypes.push_back({2, "Distribution_Switch", "Regional distribution switch", "Traffic aggregation and VLAN management"});
    nodeTypes.push_back({3, "Access_Point", "End-user access point", "Direct user connectivity and edge services"});
}

void EnhancedRuralNetworkRAG::LoadRecoveryTactics()
{
    recoveryTactics.push_back({1, "Emergency_Reroute", "Immediately reroute traffic through alternative paths", 30, "medium", true, 1});
    recoveryTactics.push_back({2, "Physical_Repair", "Dispatch repair team for physical fiber restoration", 7200, "low", false, 2});
    recoveryTactics.push_back({3, "Redundant_Path_Activation", "Activate pre-configured redundant fiber paths", 60, "low", true, 1});
    
    recoveryTactics.push_back({4, "Backup_Power_Switch", "Switch to backup power source", 120, "medium", true, 3});
    recoveryTactics.push_back({5, "Load_Shedding", "Reduce power consumption by shedding non-critical loads", 15, "high", true, 3});
    recoveryTactics.push_back({6, "Generator_Deployment", "Deploy emergency generator", 1800, "low", false, 2});
    
    recoveryTactics.push_back({7, "Traffic_Load_Balance", "Redistribute traffic across available links", 45, "low", true, 1});
    recoveryTactics.push_back({8, "QoS_Prioritization", "Adjust QoS policies to prioritize critical traffic", 30, "medium", true, 4});
    recoveryTactics.push_back({9, "Node_Restart", "Restart affected network node", 300, "high", true, 4});
    
    std::cout << "Recovery tactics loaded: " << recoveryTactics.size() << " tactics available" << std::endl;
}

void EnhancedRuralNetworkRAG::LoadPolicyKnowledgeBase()
{
    policyRecords.push_back({
        1, "FCC_Rural_Broadband_Policy", "Compliance", 
        "FCC regulations for rural broadband infrastructure",
        "FCC Rural Digital Opportunity Fund (RDOF) requirements for network availability and performance standards",
        "Requires 99.5% uptime for broadband services, recovery time must not exceed 4 hours",
        "Traffic prioritization must ensure equal access to broadband services",
        "2025-01-15"
    });
    
    policyRecords.push_back({
        2, "NIST_SP_800-53_Rev5_AC-4", "Security", 
        "NIST access control policy for information flow enforcement",
        "NIST Special Publication 800-53 Revision 5 - Security and Privacy Controls for Information Systems",
        "All recovery actions must maintain information flow controls and security boundaries",
        "Load balancing must not violate security zones and traffic classification",
        "2024-12-01"
    });
    
    policyRecords.push_back({
        3, "USDA_Rural_Utilities_Service", "Performance", 
        "USDA RUS technical standards for rural telecommunications",
        "USDA Rural Utilities Service 7 CFR Part 1755 - Telecommunications Standards and Specifications",
        "Network recovery must prioritize essential services (emergency, healthcare, education)",
        "Load distribution must maintain geographic coverage requirements",
        "2024-11-30"
    });
    
    policyRecords.push_back({
        4, "Emergency_Communications_Policy", "Security", 
        "Emergency communications and disaster recovery standards",
        "FCC Part 4 - Disruptions to Communications Networks and Emergency Communications",
        "Emergency traffic must have priority during recovery operations",
        "Critical infrastructure traffic has precedence over commercial traffic",
        "2025-02-01"
    });
    
    std::cout << "Policy knowledge base loaded: " << policyRecords.size() << " policies available" << std::endl;
}

void EnhancedRuralNetworkRAG::ClassifyAndRecordAnomaly(const GradualFaultPattern& fault, const std::string& eventType)
{
    if (!m_config.enableAnomalyClassification) return;
    
    AnomalyRecord anomaly;
    anomaly.anomalyId = GenerateAnomalyId();
    anomaly.timestamp = Simulator::Now().GetSeconds();
    anomaly.nodeId = GenerateNodeId(fault.targetNode);
    anomaly.severityClassification = ClassifyAnomalySeverity(fault.currentSeverity);
    anomaly.anomalyDescription = fault.faultDescription + " (" + eventType + ")";
    anomaly.rootCauseIndicators = GenerateRootCauseJSON(fault);
    anomaly.affectedComponents = GenerateAffectedComponentsJSON(fault);
    anomaly.status = "detected";
    anomaly.healingRecommendationId = 0;
    
    if (fault.faultType == "fiber_cut") {
        anomaly.anomalyTypeId = 1;
        anomaly.timeToFailure = "immediate";
    } else if (fault.faultType == "power_fluctuation") {
        anomaly.anomalyTypeId = 2;
        anomaly.timeToFailure = (fault.currentSeverity > 0.8) ? "within 5 minutes" : "within 30 minutes";
    }
    
    anomalyRecords.push_back(anomaly);
}

std::string EnhancedRuralNetworkRAG::ClassifyAnomalySeverity(double severity)
{
    if (severity >= 0.8) return "critical";
    else if (severity >= 0.5) return "major";
    else if (severity >= 0.2) return "minor";
    else return "warning";
}

std::string EnhancedRuralNetworkRAG::GenerateRootCauseJSON(const GradualFaultPattern& fault)
{
    std::stringstream json;
    json << "[";
    
    if (fault.faultType == "fiber_cut") {
        json << "{\"feature\": \"physical_connectivity\", \"value\": " << (fault.currentSeverity * 100) << ", \"unit\": \"percent_degraded\"},";
        json << "{\"feature\": \"link_status\", \"value\": \"down\", \"affected_link\": \"" 
             << GenerateNodeId(fault.targetNode) << "_to_" << GenerateNodeId(fault.connectedNode) << "\"}";
    } else if (fault.faultType == "power_fluctuation") {
        json << "{\"feature\": \"voltage_stability\", \"value\": " << (220.0 * (1.0 - fault.currentSeverity)) << ", \"unit\": \"volts\"},";
        json << "{\"feature\": \"power_quality\", \"value\": " << (fault.currentSeverity * 100) << ", \"unit\": \"percent_degraded\"}";
    }
    
    json << "]";
    return json.str();
}

std::string EnhancedRuralNetworkRAG::GenerateAffectedComponentsJSON(const GradualFaultPattern& fault)
{
    std::stringstream json;
    json << "[";
    
    if (fault.faultType == "fiber_cut") {
        json << "\"interface_" << GenerateNodeId(fault.targetNode) << "_port1\",";
        json << "\"interface_" << GenerateNodeId(fault.connectedNode) << "_port1\"";
    } else if (fault.faultType == "power_fluctuation") {
        json << "\"power_supply_unit_1\",";
        json << "\"voltage_regulator_" << GenerateNodeId(fault.targetNode) << "\"";
    }
    
    json << "]";
    return json.str();
}

void EnhancedRuralNetworkRAG::CreateLinkTopology()
{
    if (!m_config.enableLinkTracking) return;
    
    std::cout << "Creating link topology for RAG database..." << std::endl;
    
    // Core mesh links
    for (uint32_t i = 0; i < 5; ++i) {
        for (uint32_t j = i + 1; j < 5; ++j) {
            LinkRecord link;
            link.linkId = GenerateLinkId(i, j);
            link.sourceNodeId = GenerateNodeId(i);
            link.destinationNodeId = GenerateNodeId(j);
            link.linkType = "Fiber";
            link.totalBandwidthMbps = 1000.0;
            link.currentBandwidthUtilPercent = 30.0 + (rand() % 40);
            link.latencyMs = 2.0 + (rand() % 3);
            link.packetLossRate = 0.001;
            link.status = "up";
            link.isRedundant = true;
            link.timestamp = Simulator::Now().GetSeconds();
            
            linkRecords.push_back(link);
        }
    }
    
    // Distribution to core links
    for (uint32_t i = 0; i < 15; ++i) {
        uint32_t coreNode = i % 5;
        uint32_t distNode = i + 5;
        
        LinkRecord link;
        link.linkId = GenerateLinkId(distNode, coreNode);
        link.sourceNodeId = GenerateNodeId(distNode);
        link.destinationNodeId = GenerateNodeId(coreNode);
        link.linkType = "Fiber";
        link.totalBandwidthMbps = 100.0;
        link.currentBandwidthUtilPercent = 40.0 + (rand() % 30);
        link.latencyMs = 10.0 + (rand() % 5);
        link.packetLossRate = 0.005;
        link.status = "up";
        link.isRedundant = false;
        link.timestamp = Simulator::Now().GetSeconds();
        
        linkRecords.push_back(link);
    }
    
    // Access to distribution links
    for (uint32_t i = 0; i < 30; ++i) {
        uint32_t distNode = (i % 15) + 5;
        uint32_t accessNode = i + 20;
        
        LinkRecord link;
        link.linkId = GenerateLinkId(accessNode, distNode);
        link.sourceNodeId = GenerateNodeId(accessNode);
        link.destinationNodeId = GenerateNodeId(distNode);
        link.linkType = "Ethernet";
        link.totalBandwidthMbps = 50.0;
        link.currentBandwidthUtilPercent = 50.0 + (rand() % 35);
        link.latencyMs = 5.0 + (rand() % 10);
        link.packetLossRate = 0.01;
        link.status = "up";
        link.isRedundant = false;
        link.timestamp = Simulator::Now().GetSeconds();
        
        linkRecords.push_back(link);
    }
    
    std::cout << "Link topology created: " << linkRecords.size() << " links tracked" << std::endl;
}

void EnhancedRuralNetworkRAG::CollectLinkMetrics()
{
    if (!m_config.enableLinkTracking) return;
    
    double currentTime = Simulator::Now().GetSeconds();
    
    for (auto& link : linkRecords) {
        link.timestamp = currentTime;
        
        // Check if link is affected by faults
        for (const auto& fault : gradualFaults) {
            if (fault.isActive && fault.currentSeverity > 0.0) {
                std::string faultedNodeId = GenerateNodeId(fault.targetNode);
                std::string connectedNodeId = GenerateNodeId(fault.connectedNode);
                
                if ((link.sourceNodeId == faultedNodeId && link.destinationNodeId == connectedNodeId) ||
                    (link.sourceNodeId == connectedNodeId && link.destinationNodeId == faultedNodeId)) {
                    
                    if (fault.faultType == "fiber_cut" && fault.currentSeverity > 0.8) {
                        link.status = "down";
                        link.currentBandwidthUtilPercent = 0.0;
                        link.packetLossRate = 1.0;
                        link.latencyMs = 0.0;
                    } else {
                        link.status = "degraded";
                        link.currentBandwidthUtilPercent *= (1.0 - fault.currentSeverity * 0.7);
                        link.packetLossRate += fault.currentSeverity * 0.5;
                        link.latencyMs *= (1.0 + fault.currentSeverity * 5.0);
                    }
                    break;
                }
            }
        }
        
        if (link.status != "up") {
            // Check if fault is resolved (would be done by AI agents)
            bool linkAffected = false;
            for (const auto& fault : gradualFaults) {
                if (fault.isActive && fault.currentSeverity > 0.0) {
                    std::string faultedNodeId = GenerateNodeId(fault.targetNode);
                    std::string connectedNodeId = GenerateNodeId(fault.connectedNode);
                    
                    if ((link.sourceNodeId == faultedNodeId && link.destinationNodeId == connectedNodeId) ||
                        (link.sourceNodeId == connectedNodeId && link.destinationNodeId == faultedNodeId)) {
                        linkAffected = true;
                        break;
                    }
                }
            }
            
            if (!linkAffected) {
                // Restore to baseline if no active faults (would be done by AI agents)
                link.status = "up";
                link.currentBandwidthUtilPercent = 30.0 + (rand() % 40);
                link.packetLossRate = 0.001 + (rand() % 10) * 0.001;
            }
        }
    }
}

void EnhancedRuralNetworkRAG::InitializeTrafficFlowTracking()
{
    if (!m_config.enableTrafficFlowAnalysis) return;
    
    std::cout << "Initializing traffic flow tracking..." << std::endl;
    
    // Create initial traffic flows based on application setup
    for (uint32_t coreId = 0; coreId < 5; ++coreId) {
        for (uint32_t accessId = 20; accessId < 50; accessId += 10) {
            TrafficFlowRecord flow;
            flow.flowId = GenerateFlowId(coreId, accessId);
            flow.sourceNodeId = GenerateNodeId(coreId);
            flow.destinationNodeId = GenerateNodeId(accessId);
            flow.currentPathLinks = TracePath(coreId, accessId);
            flow.trafficVolumeMbps = 10.0 + (rand() % 20);
            flow.trafficType = (rand() % 3 == 0) ? "VoIP" : ((rand() % 2 == 0) ? "HTTP" : "Database");
            flow.priority = (flow.trafficType == "VoIP") ? "high" : "medium";
            flow.startTime = Simulator::Now().GetSeconds();
            flow.endTime = -1; // Ongoing
            flow.timestamp = flow.startTime;
            
            trafficFlowRecords.push_back(flow);
        }
    }
    
    std::cout << "Traffic flow tracking initialized: " << trafficFlowRecords.size() << " flows" << std::endl;
}

std::vector<std::string> EnhancedRuralNetworkRAG::TracePath(uint32_t source, uint32_t dest)
{
    std::vector<std::string> path;
    
    // Simplified path calculation
    if (source < 5 && dest >= 20) {
        // Core to access: core -> distribution -> access
        uint32_t intermediateDistNode = ((dest - 20) % 15) + 5;
        
        path.push_back(GenerateLinkId(source, intermediateDistNode));
        path.push_back(GenerateLinkId(intermediateDistNode, dest));
    } else if (source >= 20 && dest < 5) {
        // Access to core: access -> distribution -> core
        uint32_t intermediateDistNode = ((source - 20) % 15) + 5;
        
        path.push_back(GenerateLinkId(source, intermediateDistNode));
        path.push_back(GenerateLinkId(intermediateDistNode, dest));
    }
    
    return path;
}

void EnhancedRuralNetworkRAG::CollectEnhancedNodeData()
{
    nodeRecords.clear();
    
    for (uint32_t i = 0; i < allNodes.GetN(); ++i) {
        EnhancedNodeRecord record = GetEnhancedNodeRecord(i);
        record.timestamp = Simulator::Now().GetSeconds();
        nodeRecords.push_back(record);
    }
}

EnhancedNodeRecord EnhancedRuralNetworkRAG::GetEnhancedNodeRecord(uint32_t nodeId)
{
    EnhancedNodeRecord record;
    
    record.nodeId = GenerateNodeId(nodeId);
    record.nodeName = record.nodeId + "_Router";
    record.ipAddress = GetNodeIpAddress(nodeId);
    record.lastHeartbeat = Simulator::Now().GetSeconds();
    record.lastConfigChange = 0.0;
    record.firmwareVersion = "IOS_XE_17.6.1";
    
    if (nodeId < 5) {
        record.layerId = 1;
        record.nodeTypeId = 1;
        record.location = "DataCenter_A_Rack_" + std::to_string(nodeId + 1);
        record.maxCapacityUnits = 1000.0;
    } else if (nodeId < 20) {
        record.layerId = 2;
        record.nodeTypeId = 2;
        record.location = "RegionalPOP_" + std::to_string(nodeId - 4) + "_Floor_2";
        record.maxCapacityUnits = 100.0;
    } else {
        record.layerId = 3;
        record.nodeTypeId = 3;
        record.location = "CommunityCenter_" + std::to_string(nodeId - 19) + "_Equipment_Room";
        record.maxCapacityUnits = 50.0;
    }
    
    NodeMetrics metrics = GetEnhancedNodeMetrics(nodeId);
    record.currentCpuLoadPercent = metrics.cpuUsage;
    record.currentMemoryLoadPercent = metrics.memoryUsage;
    record.currentBandwidthUtilPercent = metrics.linkUtilization;
    
    if (metrics.faultSeverity > 0.8) {
        record.status = "offline";
        record.operationalState = "maintenance";
    } else if (metrics.faultSeverity > 0.2) {
        record.status = "degraded";
        record.operationalState = "active";
    } else {
        record.status = "online";
        record.operationalState = "active";
    }
    
    return record;
}

std::string EnhancedRuralNetworkRAG::GetNodeIpAddress(uint32_t nodeId)
{
    if (nodeId < 5) {
        return "10.1.1." + std::to_string(nodeId + 1);
    } else if (nodeId < 20) {
        return "10.2." + std::to_string(nodeId - 4) + ".1";
    } else {
        return "192.168." + std::to_string((nodeId - 20) / 10 + 1) + "." + std::to_string((nodeId - 20) % 10 + 1);
    }
}

void EnhancedRuralNetworkRAG::UpdateTrafficFlows()
{
    if (!m_config.enableTrafficFlowAnalysis) return;
    
    for (auto& flow : trafficFlowRecords) {
        if (flow.endTime > 0) continue;
        
        flow.timestamp = Simulator::Now().GetSeconds();
        
        // Adjust traffic volume based on network conditions
        bool pathAffected = false;
        
        for (const auto& linkId : flow.currentPathLinks) {
            for (const auto& link : linkRecords) {
                if (link.linkId == linkId && link.status != "up") {
                    pathAffected = true;
                    break;
                }
            }
            if (pathAffected) break;
        }
        
        if (pathAffected) {
            flow.trafficVolumeMbps *= 0.3; // Reduce traffic due to degraded path
        }
    }
}

// **DATABASE EXPORT METHODS**
void EnhancedRuralNetworkRAG::ExportDatabaseTables()
{
    if (!m_config.enableDatabaseGeneration) return;
    
    std::cout << "Exporting RAG database tables..." << std::endl;
    
    GenerateDatabaseSchema();
    ExportNodesTable();
    ExportLinksTable();
    ExportAnomaliesTable();
    ExportRecoveryTacticsTable();
    ExportPoliciesTable();
    ExportTrafficFlowsTable();
    ExportReferenceTablesSQL();
    
    std::cout << "Database export completed successfully" << std::endl;
}

void EnhancedRuralNetworkRAG::GenerateDatabaseSchema()
{
    databaseSchemaFile << "-- RAG TRAINING DATABASE SCHEMA\n";
    databaseSchemaFile << "-- Generated by Enhanced Rural Network Simulation\n\n";
    
    // Nodes table schema
    databaseSchemaFile << "CREATE TABLE Nodes (\n";
    databaseSchemaFile << "    node_id VARCHAR(50) PRIMARY KEY,\n";
    databaseSchemaFile << "    node_name VARCHAR(100) NOT NULL,\n";
    databaseSchemaFile << "    layer_id INT NOT NULL,\n";
    databaseSchemaFile << "    node_type_id INT NOT NULL,\n";
    databaseSchemaFile << "    ip_address VARCHAR(50),\n";
    databaseSchemaFile << "    location VARCHAR(200),\n";
    databaseSchemaFile << "    status VARCHAR(20),\n";
    databaseSchemaFile << "    last_heartbeat TIMESTAMP,\n";
    databaseSchemaFile << "    current_cpu_load_percent DECIMAL(5,2),\n";
    databaseSchemaFile << "    current_memory_load_percent DECIMAL(5,2),\n";
    databaseSchemaFile << "    current_bandwidth_util_percent DECIMAL(5,2),\n";
    databaseSchemaFile << "    max_capacity_units DECIMAL(10,2),\n";
    databaseSchemaFile << "    operational_state VARCHAR(20),\n";
    databaseSchemaFile << "    firmware_version VARCHAR(50),\n";
    databaseSchemaFile << "    last_config_change TIMESTAMP\n";
    databaseSchemaFile << ");\n\n";
    
    // Links table schema
    databaseSchemaFile << "CREATE TABLE Links (\n";
    databaseSchemaFile << "    link_id VARCHAR(100) PRIMARY KEY,\n";
    databaseSchemaFile << "    source_node_id VARCHAR(50) NOT NULL,\n";
    databaseSchemaFile << "    destination_node_id VARCHAR(50) NOT NULL,\n";
    databaseSchemaFile << "    link_type VARCHAR(50),\n";
    databaseSchemaFile << "    total_bandwidth_mbps DECIMAL(10,2),\n";
    databaseSchemaFile << "    current_bandwidth_util_percent DECIMAL(5,2),\n";
    databaseSchemaFile << "    latency_ms DECIMAL(8,3),\n";
    databaseSchemaFile << "    packet_loss_rate DECIMAL(8,6),\n";
    databaseSchemaFile << "    status VARCHAR(20),\n";
    databaseSchemaFile << "    is_redundant BOOLEAN,\n";  // ✅ FIXED: Added semicolon
    databaseSchemaFile << "    timestamp TIMESTAMP\n";
    databaseSchemaFile << ");\n\n";
    
    // Anomalies table schema
    databaseSchemaFile << "CREATE TABLE Anomalies (\n";
    databaseSchemaFile << "    anomaly_id VARCHAR(100) PRIMARY KEY,\n";
    databaseSchemaFile << "    timestamp TIMESTAMP NOT NULL,\n";
    databaseSchemaFile << "    node_id VARCHAR(50) NOT NULL,\n";
    databaseSchemaFile << "    severity_classification VARCHAR(20),\n";
    databaseSchemaFile << "    anomaly_description TEXT,\n";
    databaseSchemaFile << "    root_cause_indicators TEXT,\n";
    databaseSchemaFile << "    affected_components TEXT,\n";
    databaseSchemaFile << "    time_to_failure VARCHAR(50),\n";
    databaseSchemaFile << "    status VARCHAR(20),\n";
    databaseSchemaFile << "    healing_recommendation_id INT,\n";
    databaseSchemaFile << "    anomaly_type_id INT\n";
    databaseSchemaFile << ");\n\n";
    
    // Recovery Tactics table schema
    databaseSchemaFile << "CREATE TABLE RecoveryTactics (\n";
    databaseSchemaFile << "    tactic_id INT PRIMARY KEY,\n";
    databaseSchemaFile << "    tactic_name VARCHAR(100) NOT NULL,\n";
    databaseSchemaFile << "    description TEXT,\n";
    databaseSchemaFile << "    estimated_downtime_seconds INT,\n";
    databaseSchemaFile << "    risk_level VARCHAR(20),\n";
    databaseSchemaFile << "    is_automated_capable BOOLEAN,\n";
    databaseSchemaFile << "    policy_id INT\n";
    databaseSchemaFile << ");\n\n";
    
    // Policies table schema
    databaseSchemaFile << "CREATE TABLE Policies (\n";
    databaseSchemaFile << "    policy_id INT PRIMARY KEY,\n";
    databaseSchemaFile << "    policy_name VARCHAR(200) NOT NULL,\n";
    databaseSchemaFile << "    policy_category VARCHAR(50),\n";
    databaseSchemaFile << "    description TEXT,\n";
    databaseSchemaFile << "    full_text_reference TEXT,\n";
    databaseSchemaFile << "    impact_on_recovery TEXT,\n";
    databaseSchemaFile << "    impact_on_load_distribution TEXT,\n";
    databaseSchemaFile << "    last_updated DATE\n";
    databaseSchemaFile << ");\n\n";
    
    // Traffic Flows table schema
    databaseSchemaFile << "CREATE TABLE TrafficFlows (\n";
    databaseSchemaFile << "    flow_id VARCHAR(100) PRIMARY KEY,\n";
    databaseSchemaFile << "    source_node_id VARCHAR(50) NOT NULL,\n";
    databaseSchemaFile << "    destination_node_id VARCHAR(50) NOT NULL,\n";
    databaseSchemaFile << "    traffic_volume_mbps DECIMAL(10,2),\n";
    databaseSchemaFile << "    traffic_type VARCHAR(50),\n";
    databaseSchemaFile << "    priority VARCHAR(20),\n";
    databaseSchemaFile << "    start_time TIMESTAMP,\n";
    databaseSchemaFile << "    end_time TIMESTAMP,\n";
    databaseSchemaFile << "    timestamp TIMESTAMP\n";
    databaseSchemaFile << ");\n\n";
    
    // Reference tables
    databaseSchemaFile << "CREATE TABLE NetworkLayers (\n";
    databaseSchemaFile << "    layer_id INT PRIMARY KEY,\n";
    databaseSchemaFile << "    layer_name VARCHAR(50) NOT NULL,\n";
    databaseSchemaFile << "    description TEXT\n";
    databaseSchemaFile << ");\n\n";
    
    databaseSchemaFile << "CREATE TABLE NodeTypes (\n";
    databaseSchemaFile << "    node_type_id INT PRIMARY KEY,\n";
    databaseSchemaFile << "    type_name VARCHAR(50) NOT NULL,\n";
    databaseSchemaFile << "    description TEXT,\n";
    databaseSchemaFile << "    typical_role TEXT\n";
    databaseSchemaFile << ");\n\n";
    }
    
// **FIXED: UpdateGradualVisualization method WITHOUT percentages and size changes**
void EnhancedRuralNetworkRAG::UpdateGradualVisualization(const GradualFaultPattern& fault)
{
    if (!animInterface) {
        std::cout << "❌ DEBUG: animInterface is NULL - no visualization possible" << std::endl;
        return;
    }
    
    double severity = fault.currentSeverity;
    uint32_t nodeId = fault.targetNode;
    std::string nodeName = GetNodeVisualName(nodeId);
    
    // **ENHANCED: More visible color progression**
    uint8_t r, g, b;
    if (severity > 0.8) {
        r = 255; g = 0; b = 0;      // Bright red
    } else if (severity > 0.5) {
        r = 255; g = 100; b = 0;    // Red-orange
    } else if (severity > 0.2) {
        r = 255; g = 165; b = 0;    // Orange
    } else {
        r = 255; g = 255; b = 0;    // Yellow
    }
    
    // **APPLY COLOR**
    animInterface->UpdateNodeColor(allNodes.Get(nodeId), r, g, b);
    
    // **SIMPLE DESCRIPTION**
    std::string description = nodeName + " [" + fault.faultType + "]";
    animInterface->UpdateNodeDescription(allNodes.Get(nodeId), description);
    
    // **ENHANCED DEBUG OUTPUT**
    std::cout << "🎨 COLOR UPDATE: " << nodeName << " severity=" << std::fixed << std::setprecision(2) 
              << (severity * 100) << "% RGB=(" << (int)r << "," << (int)g << "," << (int)b << ")"
              << " [Target: " << (severity > 0.8 ? "RED" : (severity > 0.5 ? "RED-ORANGE" : (severity > 0.2 ? "ORANGE" : "YELLOW"))) << "]" << std::endl;
}

void EnhancedRuralNetworkRAG::UpdatePeakVisualization(const GradualFaultPattern& fault)
{
    if (!animInterface) {
        std::cout << "❌ DEBUG: animInterface is NULL" << std::endl;
        return;
    }
    
    uint32_t nodeId = fault.targetNode;
    std::string nodeName = GetNodeVisualName(nodeId);
    
    // **PEAK FAULT: Bright red for ALL affected nodes**
    animInterface->UpdateNodeColor(allNodes.Get(nodeId), 255, 0, 0);  // Bright red
    
    std::string description = nodeName + " [" + fault.faultType + " CRITICAL]";
    animInterface->UpdateNodeDescription(allNodes.Get(nodeId), description);
    
    std::cout << "🔴 PEAK VISUALIZATION: " << nodeName << " turned BRIGHT RED (severity=" 
              << (int)(fault.currentSeverity * 100) << "%)" << std::endl;
    
    // **TRIGGER LINK EFFECTS ONLY ONCE PER FIBER CUT**
    if (fault.faultType == "fiber_cut" && fault.connectedNode > 0) {
        // Only trigger link hiding from the lower node ID to avoid duplication
        if (fault.targetNode < fault.connectedNode) {
            std::cout << "🔥 TRIGGERING LINK BLOCK from " << nodeName << std::endl;
            HideFiberLink(fault.targetNode, fault.connectedNode);
        }
    } else if (fault.faultType == "power_fluctuation") {
        ShowPowerIssue(fault.targetNode);
    }
}

void EnhancedRuralNetworkRAG::ExportNodesTable()
{
    if (nodeRecords.empty()) return;
    
    nodesDbFile << "-- NODES TABLE\n";
    nodesDbFile << "INSERT INTO Nodes (node_id, node_name, layer_id, node_type_id, ip_address, location, status) VALUES\n";
    
    for (size_t i = 0; i < nodeRecords.size(); ++i) {
        const auto& node = nodeRecords[i];
        nodesDbFile << "('" << node.nodeId << "', '" << node.nodeName << "', "
                   << node.layerId << ", " << node.nodeTypeId << ", '"
                   << node.ipAddress << "', '" << node.location << "', '"
                   << node.status << "')";
        
        if (i < nodeRecords.size() - 1) nodesDbFile << ",\n";
        else nodesDbFile << ";\n\n";
    }
}

void EnhancedRuralNetworkRAG::ExportLinksTable()
{
    if (linkRecords.empty()) return;
    
    linksDbFile << "-- LINKS TABLE\n";
    linksDbFile << "INSERT INTO Links (link_id, source_node_id, destination_node_id, link_type, total_bandwidth_mbps, current_bandwidth_util_percent, status) VALUES\n";
    
    for (size_t i = 0; i < linkRecords.size(); ++i) {
        const auto& link = linkRecords[i];
        linksDbFile << "('" << link.linkId << "', '" << link.sourceNodeId << "', '"
                   << link.destinationNodeId << "', '" << link.linkType << "', "
                   << link.totalBandwidthMbps << ", " << link.currentBandwidthUtilPercent
                   << ", '" << link.status << "')";
        
        if (i < linkRecords.size() - 1) linksDbFile << ",\n";
        else linksDbFile << ";\n\n";
    }
}

void EnhancedRuralNetworkRAG::ExportAnomaliesTable()
{
    if (anomalyRecords.empty()) return;
    
    anomaliesDbFile << "-- ANOMALIES TABLE\n";
    
    for (const auto& anomaly : anomalyRecords) {
        anomaliesDbFile << "INSERT INTO Anomalies VALUES ('"
                       << anomaly.anomalyId << "', '" << std::to_string(anomaly.timestamp) << "', '"
                       << anomaly.nodeId << "', '" << anomaly.severityClassification << "', '"
                       << anomaly.anomalyDescription << "', '" << anomaly.rootCauseIndicators << "', '"
                       << anomaly.affectedComponents << "', '" << anomaly.timeToFailure << "', '"
                       << anomaly.status << "', " << anomaly.healingRecommendationId << ", "
                       << anomaly.anomalyTypeId << ");\n";
    }
    anomaliesDbFile << "\n";
}

void EnhancedRuralNetworkRAG::ExportRecoveryTacticsTable()
{
    recoveryTacticsDbFile << "-- RECOVERY TACTICS TABLE\n";
    
    for (const auto& tactic : recoveryTactics) {
        recoveryTacticsDbFile << "INSERT INTO RecoveryTactics VALUES ("
                             << tactic.tacticId << ", '" << tactic.tacticName << "', '"
                             << tactic.description << "', " << tactic.estimatedDowntimeSeconds
                             << ", '" << tactic.riskLevel << "', " 
                             << (tactic.isAutomatedCapable ? "TRUE" : "FALSE") << ", "
                             << tactic.policyId << ");\n";
    }
    recoveryTacticsDbFile << "\n";
}

void EnhancedRuralNetworkRAG::ExportPoliciesTable()
{
    policiesDbFile << "-- POLICIES TABLE\n";
    
    for (const auto& policy : policyRecords) {
        policiesDbFile << "INSERT INTO Policies VALUES ("
                      << policy.policyId << ", '" << policy.policyName << "', '"
                      << policy.policyCategory << "', '" << policy.description << "', '"
                      << policy.fullTextReference << "', '" << policy.impactOnRecovery << "', '"
                      << policy.impactOnLoadDistribution << "', '" << policy.lastUpdated << "');\n";
    }
    policiesDbFile << "\n";
}

void EnhancedRuralNetworkRAG::ExportTrafficFlowsTable()
{
    if (trafficFlowRecords.empty()) return;
    
    trafficFlowsDbFile << "-- TRAFFIC FLOWS TABLE\n";
    
    for (const auto& flow : trafficFlowRecords) {
        trafficFlowsDbFile << "INSERT INTO TrafficFlows VALUES ('"
                          << flow.flowId << "', '" << flow.sourceNodeId << "', '"
                          << flow.destinationNodeId << "', " << flow.trafficVolumeMbps
                          << ", '" << flow.trafficType << "', '" << flow.priority << "', '"
                          << std::to_string(flow.startTime) << "', '"
                          << (flow.endTime > 0 ? std::to_string(flow.endTime) : "NULL") << "', '"
                          << std::to_string(flow.timestamp) << "');\n";
    }
    trafficFlowsDbFile << "\n";
}

void EnhancedRuralNetworkRAG::ExportReferenceTablesSQL()
{
    databaseSchemaFile << "\n-- REFERENCE DATA\n";
    
    // Network Layers
    databaseSchemaFile << "INSERT INTO NetworkLayers VALUES\n";
    for (size_t i = 0; i < networkLayers.size(); ++i) {
        const auto& layer = networkLayers[i];
        databaseSchemaFile << "(" << layer.layerId << ", '" << layer.layerName << "', '"
                          << layer.description << "')";
        if (i < networkLayers.size() - 1) databaseSchemaFile << ",\n";
        else databaseSchemaFile << ";\n\n";
    }
    
    // Node Types
    databaseSchemaFile << "INSERT INTO NodeTypes VALUES\n";
    for (size_t i = 0; i < nodeTypes.size(); ++i) {
        const auto& type = nodeTypes[i];
        databaseSchemaFile << "(" << type.nodeTypeId << ", '" << type.typeName << "', '"
                          << type.description << "', '" << type.typicalRole << "')";
        if (i < nodeTypes.size() - 1) databaseSchemaFile << ",\n";
        else databaseSchemaFile << ";\n\n";
    }
}

void EnhancedRuralNetworkRAG::Run()
{
    std::cout << "========================================" << std::endl;
    std::cout << "  ENHANCED RURAL NETWORK RAG SIMULATION " << std::endl;
    std::cout << "  Mode: " << m_config.mode << std::endl;
    std::cout << "  **DEBUG: Total simulation time: " << m_config.totalSimulationTime << "s**" << std::endl;
    std::cout << "  **DEBUG: Fault start time: " << m_config.faultStartTime << "s**" << std::endl;
    std::cout << "========================================" << std::endl;
    
    SetupRobustTopology();
    SetupRobustApplications();
    SetupRobustNetAnimVisualization();
    
    if (m_config.enableDatabaseGeneration) {
        CreateLinkTopology();
        InitializeTrafficFlowTracking();
    }
    
    for (double t = 30.0; t < m_config.totalSimulationTime; t += 30.0) {
        Simulator::Schedule(Seconds(t), [t]() {
            std::cout << "🕒 SIMULATION PROGRESS: " << t << "s" << std::endl;
        });
    }
    
    Simulator::Schedule(Seconds(m_config.dataCollectionInterval), 
                       &EnhancedRuralNetworkRAG::CollectComprehensiveMetrics, this);
    
    if (m_config.enableFaultInjection) {
        ScheduleGradualFaultPatterns();
    }
    
    WriteConfigurationInfo();
    WriteTopologyInfo();
    
    Simulator::Stop(Seconds(m_config.totalSimulationTime));
    
    std::cout << "Starting simulation..." << std::endl;
    std::cout << "Duration: " << m_config.totalSimulationTime << "s" << std::endl;
    std::cout << "**EXPECTED FAULT TIMES: 60s, 90s, 120s, 150s**" << std::endl;
    
    // Check for early termination conditions
    if (m_config.totalSimulationTime < 300.0) {
    std::cout << "⚠️  WARNING: Short simulation time (" << m_config.totalSimulationTime << "s)" << std::endl;
    std::cout << "⚠️  Faults may not have time to develop properly" << std::endl;
}

    std::cout << "🚀 Starting simulation with configuration:" << std::endl;
    std::cout << "   - Mode: " << m_config.mode << std::endl;
    std::cout << "   - Duration: " << m_config.totalSimulationTime << "s" << std::endl;
    std::cout << "   - Packet limit: 50000" << std::endl;
    std::cout << "   - Expected runtime: ~" << (int)(m_config.totalSimulationTime / 60) << " minutes" << std::endl;
    
    Simulator::Run();
    
    if (m_config.enableDatabaseGeneration) {
        ExportDatabaseTables();
    }
    
    std::cout << "========================================" << std::endl;
    std::cout << "Simulation completed successfully!" << std::endl;
    if (m_config.enableDatabaseGeneration) {
        std::cout << "Database records generated:" << std::endl;
        std::cout << "- Nodes: " << nodeRecords.size() << std::endl;
        std::cout << "- Links: " << linkRecords.size() << std::endl;
        std::cout << "- Anomalies: " << anomalyRecords.size() << std::endl;
        std::cout << "- Recovery Tactics: " << recoveryTactics.size() << std::endl;
        std::cout << "- Policies: " << policyRecords.size() << std::endl;
    }
    std::cout << "========================================" << std::endl;
    
    WriteFaultEventLog();
    Simulator::Destroy();
    
    if (animInterface) {
        delete animInterface;
    }
    
    // Close all files
    metricsFile.close();
    topologyFile.close();
    configFile.close();
    faultLogFile.close();
    
    if (m_config.enableDatabaseGeneration) {
        nodesDbFile.close();
        linksDbFile.close();
        anomaliesDbFile.close();
        recoveryTacticsDbFile.close();
        policiesDbFile.close();
        trafficFlowsDbFile.close();
        databaseSchemaFile.close();
    }
}

// **MISSING METHOD IMPLEMENTATIONS**

void EnhancedRuralNetworkRAG::WriteConfigurationInfo()
{
    configFile << "{\n";
    configFile << "  \"simulation_mode\": \"" << m_config.mode << "\",\n";
    configFile << "  \"total_simulation_time\": " << m_config.totalSimulationTime << ",\n";
    configFile << "  \"data_collection_interval\": " << m_config.dataCollectionInterval << ",\n";
    configFile << "  \"baseline_duration\": " << m_config.baselineDuration << ",\n";
    configFile << "  \"fault_start_time\": " << m_config.faultStartTime << ",\n";
    configFile << "  \"enable_fault_injection\": " << (m_config.enableFaultInjection ? "true" : "false") << ",\n";
    configFile << "  \"enable_visualization\": " << (m_config.enableVisualization ? "true" : "false") << ",\n";
    configFile << "  \"enable_fault_visualization\": " << (m_config.enableFaultVisualization ? "true" : "false") << ",\n";
    configFile << "  \"target_data_points\": " << m_config.targetDataPoints << ",\n";
    configFile << "  \"output_prefix\": \"" << m_config.outputPrefix << "\",\n";
    configFile << "  \"enable_database_generation\": " << (m_config.enableDatabaseGeneration ? "true" : "false") << ",\n";
    configFile << "  \"enable_link_tracking\": " << (m_config.enableLinkTracking ? "true" : "false") << ",\n";
    configFile << "  \"enable_anomaly_classification\": " << (m_config.enableAnomalyClassification ? "true" : "false") << ",\n";
    configFile << "  \"enable_traffic_flow_analysis\": " << (m_config.enableTrafficFlowAnalysis ? "true" : "false") << ",\n";
    configFile << "  \"enable_policy_loading\": " << (m_config.enablePolicyLoading ? "true" : "false") << ",\n";
    configFile << "  \"database_format\": \"" << m_config.databaseFormat << "\",\n";
    configFile << "  \"total_nodes\": " << allNodes.GetN() << ",\n";
    configFile << "  \"core_nodes\": " << coreNodes.GetN() << ",\n";
    configFile << "  \"distribution_nodes\": " << distributionNodes.GetN() << ",\n";
    configFile << "  \"access_nodes\": " << accessNodes.GetN() << ",\n";
    configFile << "  \"total_interfaces\": " << allInterfaces.size() << ",\n";
    configFile << "  \"scheduled_faults\": " << gradualFaults.size() << "\n";
    configFile << "}\n";
    configFile.flush();
    
    std::cout << "Configuration information written" << std::endl;
}

void EnhancedRuralNetworkRAG::WriteTopologyInfo()
{
    topologyFile << "{\n";
    topologyFile << "  \"network_topology\": {\n";
    topologyFile << "    \"total_nodes\": " << allNodes.GetN() << ",\n";
    topologyFile << "    \"layers\": {\n";
    topologyFile << "      \"core\": {\n";
    topologyFile << "        \"count\": " << coreNodes.GetN() << ",\n";
    topologyFile << "        \"description\": \"High-capacity backbone routing\",\n";
    topologyFile << "        \"node_range\": \"0-4\",\n";
    topologyFile << "        \"data_rate\": \"" << (m_config.enableVisualization ? "1Mbps" : "1Gbps") << "\",\n";
    topologyFile << "        \"delay\": \"" << (m_config.enableVisualization ? "10ms" : "2ms") << "\"\n";
    topologyFile << "      },\n";
    topologyFile << "      \"distribution\": {\n";
    topologyFile << "        \"count\": " << distributionNodes.GetN() << ",\n";
    topologyFile << "        \"description\": \"Regional traffic aggregation\",\n";
    topologyFile << "        \"node_range\": \"5-19\",\n";
    topologyFile << "        \"data_rate\": \"" << (m_config.enableVisualization ? "512Kbps" : "100Mbps") << "\",\n";
    topologyFile << "        \"delay\": \"" << (m_config.enableVisualization ? "20ms" : "10ms") << "\"\n";
    topologyFile << "      },\n";
    topologyFile << "      \"access\": {\n";
    topologyFile << "        \"count\": " << accessNodes.GetN() << ",\n";
    topologyFile << "        \"description\": \"End-user connection points\",\n";
    topologyFile << "        \"node_range\": \"20-49\",\n";
    topologyFile << "        \"data_rate\": \"" << (m_config.enableVisualization ? "256Kbps" : "50Mbps") << "\",\n";
    topologyFile << "        \"delay\": \"" << (m_config.enableVisualization ? "50ms" : "5ms") << "\"\n";
    topologyFile << "      }\n";
    topologyFile << "    },\n";
    topologyFile << "    \"connections\": {\n";
    topologyFile << "      \"core_topology\": \"Star with central hub (CORE-0) + redundancy\",\n";
    topologyFile << "      \"distribution_topology\": \"Ring around regions, 3:1 ratio to core\",\n";
    topologyFile << "      \"access_topology\": \"2:1 ratio to distribution\",\n";
    topologyFile << "      \"total_interfaces\": " << allInterfaces.size() << "\n";
    topologyFile << "    },\n";
    topologyFile << "    \"fault_patterns\": [\n";
    
    for (size_t i = 0; i < gradualFaults.size(); ++i) {
        const auto& fault = gradualFaults[i];
        topologyFile << "      {\n";
        topologyFile << "        \"fault_id\": " << i << ",\n";
        topologyFile << "        \"target_node\": " << fault.targetNode << ",\n";
        topologyFile << "        \"connected_node\": " << fault.connectedNode << ",\n";
        topologyFile << "        \"fault_type\": \"" << fault.faultType << "\",\n";
        topologyFile << "        \"description\": \"" << fault.faultDescription << "\",\n";
        topologyFile << "        \"start_time\": " << fault.startDegradation.GetSeconds() << ",\n";
        topologyFile << "        \"peak_time\": " << fault.faultOccurrence.GetSeconds() << ",\n";
        topologyFile << "        \"severity\": " << fault.severity << ",\n";
        topologyFile << "        \"anomaly_id\": \"" << fault.anomalyId << "\"\n";
        topologyFile << "      }";
        if (i < gradualFaults.size() - 1) topologyFile << ",";
        topologyFile << "\n";
    }
    
    topologyFile << "    ]\n";
    topologyFile << "  }\n";
    topologyFile << "}\n";
    topologyFile.flush();
    
    std::cout << "Topology information written" << std::endl;
}

void EnhancedRuralNetworkRAG::WriteFaultEventLog()
{
    faultLogFile << "\n========== FAULT EVENT SUMMARY ==========\n";
    faultLogFile << "Total fault events recorded: " << faultEvents.size() << "\n";
    faultLogFile << "Total fault patterns scheduled: " << gradualFaults.size() << "\n";
    faultLogFile << "Simulation mode: " << m_config.mode << "\n";
    faultLogFile << "Total simulation time: " << m_config.totalSimulationTime << "s\n";
    faultLogFile << "==========================================\n\n";
    
    // Group events by fault type
    int fiberCutEvents = 0;
    int powerFluctuationEvents = 0;
    int degradationStartEvents = 0;
    int faultPeakEvents = 0;
    
    for (const auto& event : faultEvents) {
        if (event.faultType == "fiber_cut") fiberCutEvents++;
        if (event.faultType == "power_fluctuation") powerFluctuationEvents++;
        if (event.eventType == "DEGRADATION_START") degradationStartEvents++;
        if (event.eventType == "FAULT_PEAK") faultPeakEvents++;
    }
    
    faultLogFile << "FAULT EVENT STATISTICS:\n";
    faultLogFile << "- Fiber cut events: " << fiberCutEvents << "\n";
    faultLogFile << "- Power fluctuation events: " << powerFluctuationEvents << "\n";
    faultLogFile << "- Degradation start events: " << degradationStartEvents << "\n";
    faultLogFile << "- Fault peak events: " << faultPeakEvents << "\n";
    faultLogFile << "\n";
    
    faultLogFile << "SCHEDULED FAULT PATTERNS:\n";
    for (size_t i = 0; i < gradualFaults.size(); ++i) {
        const auto& fault = gradualFaults[i];
        faultLogFile << "Pattern " << i + 1 << ": " << fault.faultDescription << "\n";
        faultLogFile << "  - Type: " << fault.faultType << "\n";
        faultLogFile << "  - Target Node: " << GetNodeVisualName(fault.targetNode);
        if (fault.connectedNode > 0) {
            faultLogFile << " ↔ " << GetNodeVisualName(fault.connectedNode);
        }
        faultLogFile << "\n";
        faultLogFile << "  - Start Time: " << fault.startDegradation.GetSeconds() << "s\n";
        faultLogFile << "  - Peak Time: " << fault.faultOccurrence.GetSeconds() << "s\n";
        faultLogFile << "  - Severity: " << fault.severity << "\n";
        faultLogFile << "  - Status: " << (fault.isActive ? "Active" : "Inactive") << "\n";
        faultLogFile << "  - Anomaly ID: " << fault.anomalyId << "\n";
        faultLogFile << "\n";
    }
    
    if (m_config.enableDatabaseGeneration) {
        faultLogFile << "RAG DATABASE GENERATION:\n";
        faultLogFile << "- Node records: " << nodeRecords.size() << "\n";
        faultLogFile << "- Link records: " << linkRecords.size() << "\n";
        faultLogFile << "- Anomaly records: " << anomalyRecords.size() << "\n";
        faultLogFile << "- Recovery tactics: " << recoveryTactics.size() << "\n";
        faultLogFile << "- Policy records: " << policyRecords.size() << "\n";
        faultLogFile << "- Traffic flow records: " << trafficFlowRecords.size() << "\n";
        faultLogFile << "\n";
    }
    
    faultLogFile << "==========================================\n";
    faultLogFile << "Log completed at simulation end\n";
    faultLogFile << "==========================================\n";
    faultLogFile.flush();
    
    std::cout << "Fault event log summary written" << std::endl;
}


int main(int argc, char *argv[])
{
    CommandLine cmd;
    
    std::string mode = "rag_training";
    int dataPoints = 500;
    
    cmd.AddValue("mode", "Simulation mode: rag_training, fault_demo", mode);
    cmd.AddValue("points", "Target number of data points", dataPoints);
    cmd.Parse(argc, argv);
    
    LogComponentEnable("EnhancedRuralNetworkRAG", LOG_LEVEL_INFO);
    RngSeedManager::SetSeed(12345);
    
    SimulationConfig config;
    
    if (mode == "rag_training") {
        config = EnhancedRuralNetworkRAG::CreateRAGDataConfig(dataPoints);
    } else if (mode == "fault_demo") {
        config = EnhancedRuralNetworkRAG::CreateFaultDemoConfig();
    } else {
        std::cerr << "Invalid mode. Use: rag_training, fault_demo" << std::endl;
        return 1;
    }
    
    EnhancedRuralNetworkRAG simulation(config);
    simulation.Run();
    
    return 0;
}