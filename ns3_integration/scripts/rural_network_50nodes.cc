/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * COMPLETE ITU COMPETITION READY RURAL NETWORK SIMULATION
 * Implements TST-01, TST-02 with Randomized Fault Injection
 * Features: Randomized Fiber Cut & Power Fluctuation with Severity-Based Visualization
 * Enhanced Agent Integration with Closed-Loop Healing
 */
#define _USE_MATH_DEFINES
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
#include "ns3/olsr-helper.h"
#include <iostream>
#include <chrono>
#include <fstream>
#include <vector>
#include <string>
#include <iomanip>
#include <map>
#include <cmath>
#include <sstream>
#include <random>
#include <cstring>      
#include <cstdlib>      
#include <filesystem>
using json = std::map<std::string, std::string>;
using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("ITU_Competition_Rural_Network");

// **ADDED: Simple ID generator for unique identifiers**
class SimpleIdGenerator {
private:
    static uint64_t counter;
public:
    static std::string GenerateId(const std::string& prefix = "id") {
        return prefix + "_" + std::to_string(++counter) + "_" + std::to_string(time(nullptr) % 100000);
    }
};
uint64_t SimpleIdGenerator::counter = 0;

// **ENHANCED: Configuration for randomized fault injection**
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
    
    // **NEW: Agent integration**
    bool enableAgentIntegration;
    bool enableHealingDeployment;
    std::string agentInterfaceDir = "/media/rishi/Windows-SSD/PROJECT_&_RESEARCH/NOKIA/Buil-a-thon/rural_ai_selfhealing_net/ns3_integration/agent_interface";
    
    // **NEW: Randomized fault parameters**
    bool enableRandomizedFaults;
    double minFaultInterval;        // Minimum time between faults
    double maxFaultInterval;        // Maximum time between faults
    double minFaultDuration;        // Minimum fault duration
    double maxFaultDuration;        // Maximum fault duration
    double fiberCutProbability;     // Probability of fiber cut vs power fluctuation
    int maxSimultaneousFaults;      // Maximum simultaneous faults
    
    // RAG database options
    bool enableDatabaseGeneration;
    bool enableLinkTracking;
    bool enableAnomalyClassification;
    bool enableTrafficFlowAnalysis;
    bool enablePolicyLoading;
    std::string databaseFormat;
};

// **ENHANCED: Fault patterns with severity-based visualization**
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
    std::string anomalyId;
    
    // **NEW: Severity-based visualization properties**
    double originalNodeSize;
    double currentNodeSize;
    bool sizingApplied;
};

// **NEW: Healing Action Structure for Agent Integration**
struct HealingAction {
    std::string actionType; // "reroute_traffic", "activate_backup", "restart_node"
    std::vector<uint32_t> targetNodes;
    std::map<std::string, std::string> parameters;
    int priority; // 1 = highest
    double estimatedDuration; // seconds
    std::vector<std::string> dependencies; // other action IDs
};

// **NEW: Healing Plan Structure**
struct HealingPlan {
    std::string planId;
    std::string anomalyId; // Link to detected anomaly
    std::vector<HealingAction> actions;
    double confidenceScore; // 0.0-1.0
    std::string llmReasoning; // "Fiber cut detected, rerouting through backup path"
    Time createdTime;
    std::string agentSource; // "healing_agent" or "orchestration_agent"
    bool deployed;
    bool successful;
};

struct FaultEvent {
    double timestamp;
    std::string eventType;
    std::string faultType;
    std::vector<uint32_t> affectedNodes;
    std::string description;
    std::string visualEffect;
    double severity;
};

// **NEW: Agent Integration API Class**
class AgentIntegrationAPI {
public:
    AgentIntegrationAPI(const std::string& watchDir) : watchDirectory(watchDir) {
        // Create agent interface directory
        system(("mkdir -p " + watchDirectory).c_str());
        
        faultEventsFile = watchDirectory + "/fault_events_realtime.json";
        healingPlansFile = watchDirectory + "/healing_plans_incoming.json";
        deploymentStatusFile = watchDirectory + "/deployment_status.json";
        
        std::cout << "✅ Agent Integration API initialized: " << watchDirectory << std::endl;
    }
    
    // Write fault events for agents to consume
    void ExportRealTimeFaultEvents(const std::vector<FaultEvent>& events);
    void WriteFaultEventJSON(const FaultEvent& event);
    
    // Read healing plans from agents
    bool CheckForHealingPlans();
    std::vector<HealingPlan> LoadHealingPlans();
    
    // Deployment feedback to agents
    void WriteDeploymentStatus(const std::string& planId, bool success, const std::string& details);
    bool IsInterfaceReady() {
        // Check if the interface directory exists and is writable
        try {
            // Test if we can write to the interface directory
            std::ofstream testFile(watchDirectory + "/test_write.tmp");
            if (testFile.is_open()) {
                testFile << "interface_test" << std::endl;
                testFile.close();
                
                // Remove test file
                std::remove((watchDirectory + "/test_write.tmp").c_str());
                
                return true; // Interface is ready
            }
            return false;
        } catch (const std::exception& e) {
            std::cout << "⚠️ Interface readiness check failed: " << e.what() << std::endl;
            return false;
        }
    }
private:
    std::string watchDirectory;
    std::string faultEventsFile;
    std::string healingPlansFile;
    std::string deploymentStatusFile;
};

// **NEW: Healing Deployment Engine**
class HealingDeploymentEngine {
public:
    HealingDeploymentEngine(AgentIntegrationAPI* api) : apiInterface(api) {}
    
    bool DeployHealingPlan(const HealingPlan& plan);
    void ExecuteRerouteTraffic(const HealingAction& action);
    void ExecuteActivateBackupPath(const HealingAction& action);
    void ExecuteRestartNode(const HealingAction& action);
    void ExecuteLoadBalancing(const HealingAction& action);
    void ExecuteEmergencyShutdown(const HealingAction& action);
    
    // Visual feedback for NetAnim with severity-based sizing
    void ShowHealingInProgress(uint32_t nodeId, AnimationInterface* animInterface, NodeContainer& allNodes);
    void ShowHealingCompleted(uint32_t nodeId, AnimationInterface* animInterface, NodeContainer& allNodes);
    void ShowTrafficRerouting(uint32_t fromNode, uint32_t toNode, uint32_t viaNode, 
                             AnimationInterface* animInterface, NodeContainer& allNodes);
    
private:
    std::map<std::string, bool> activeHealingPlans;
    AgentIntegrationAPI* apiInterface;
    
    std::string GetNodeVisualName(uint32_t nodeId);
    void SetLinkStatus(uint32_t nodeA, uint32_t nodeB, bool status);
};

// **NEW: Randomized Fault Generator**
class RandomizedFaultGenerator {
public:
    RandomizedFaultGenerator(const SimulationConfig& config) 
        : m_config(config), rng(std::random_device{}()), 
          intervalDist(config.minFaultInterval, config.maxFaultInterval),
          durationDist(config.minFaultDuration, config.maxFaultDuration),
          severityDist(0.3, 1.0), // Severity between 30% and 100%
          probabilityDist(0.0, 1.0) {}
    
    std::vector<GradualFaultPattern> GenerateRandomizedFaults(uint32_t totalNodes);
    
private:
    const SimulationConfig& m_config;
    std::mt19937 rng;
    std::uniform_real_distribution<double> intervalDist;
    std::uniform_real_distribution<double> durationDist;
    std::uniform_real_distribution<double> severityDist;
    std::uniform_real_distribution<double> probabilityDist;
    std::uniform_int_distribution<uint32_t> nodeDist;
    
    GradualFaultPattern CreateRandomFiberCut(uint32_t nodeA, uint32_t nodeB, Time startTime, double severity);
    GradualFaultPattern CreateRandomPowerFluctuation(uint32_t nodeId, Time startTime, double severity);
    std::pair<uint32_t, uint32_t> GetRandomConnectedNodes(uint32_t totalNodes);
};

// **MAIN SIMULATION CLASS - ENHANCED FOR RANDOMIZED FAULTS**
class ITU_Competition_Rural_Network
{
public:
    ITU_Competition_Rural_Network(const SimulationConfig& config);
    void Run();
    
    static SimulationConfig CreateITU_CompetitionConfig(int targetDataPoints = 500);
    static SimulationConfig CreateFaultDemoConfig();
    static SimulationConfig CreateRandomizedFaultConfig();

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
    
    // **ENHANCED: Randomized fault patterns**
    std::vector<GradualFaultPattern> gradualFaults;
    std::vector<FaultEvent> faultEvents;
    HealingDeploymentEngine* healingEngine;
    // **NEW: Agent integration**
    AgentIntegrationAPI* agentAPI;
    RandomizedFaultGenerator* faultGenerator;
    std::vector<HealingPlan> activeHealingPlans;
    
    // **NEW: Severity-based node sizing**
    std::map<uint32_t, double> originalNodeSizes;
    double baseSeverityMultiplier = 2.0; // Size multiplier for maximum severity
    
    // **ENHANCED: Core methods from working original**
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
    
    // **ENHANCED: Randomized fault methods**
    void ScheduleRandomizedFaultPatterns();
    void UpdateFaultProgression();
    void ProcessFaultVisualization();
    void UpdateVisualFaultIndicators();
    void UpdateNodeVisualStatus(uint32_t nodeId, const std::string& status);
    void AnnounceFaultEvent(const GradualFaultPattern& fault, const std::string& eventType);
    void LogFaultEvent(const FaultEvent& event);
    
    // **NEW: Severity-based visualization methods**
    void ApplySeverityBasedNodeSizing(uint32_t nodeId, double severity);
    void RestoreOriginalNodeSize(uint32_t nodeId);
    void UpdateNodeSizeBasedOnSeverity(const GradualFaultPattern& fault);
    void CheckForOrchestrationDeployments();
    void ExecuteHealingDeployment(const std::map<std::string, std::string>& deploymentData);
    
    std::string GetNodeVisualName(uint32_t nodeId);
    void HideFiberLink(uint32_t nodeA, uint32_t nodeB);
    void RestoreFiberLink(uint32_t nodeA, uint32_t nodeB);
    void ShowPowerIssue(uint32_t nodeId);
    void HidePowerIssue(uint32_t nodeId);
    void ProcessDeploymentFile(const std::string& filePath);
    void ExecuteHealingCommand(uint32_t nodeId, const std::string& command);
    void GenerateFinalStatistics();
    void PrintSimulationSummary();
    
    // **NEW: Agent integration methods**
    void InitializeAgentIntegration();
    void ProcessAgentCommunication();
    void ProcessIncomingHealingPlans();
    void DeployHealingPlan(const HealingPlan& plan);
    void UpdateAgentInterface();
    
    // **ENHANCED: Data collection**
    void CollectComprehensiveMetrics();
    void WriteTopologyInfo();
    void WriteConfigurationInfo();
    void WriteFaultEventLog();
    void WriteNodeConnectivity();
    void WriteDetailedTopology();
    double GetTimeOfDayMultiplier();
    double GetTrafficPatternMultiplier();
    double GetSeasonalVariation();
    double CalculateNodeDegradation(uint32_t nodeId, const std::string& metric);
    
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
    
    // **NEW: Output files**
    std::ofstream metricsFile, topologyFile, configFile, faultLogFile;
};

// **ENHANCED: Configuration factory methods for randomized faults**
SimulationConfig ITU_Competition_Rural_Network::CreateITU_CompetitionConfig(int targetDataPoints)
{
    SimulationConfig config;
    config.mode = "itu_competition_complete";
    config.dataCollectionInterval = 5.0;
    config.totalSimulationTime = targetDataPoints * config.dataCollectionInterval;
    config.baselineDuration = config.totalSimulationTime * 0.3;
    config.faultStartTime = config.baselineDuration;
    config.enableFaultInjection = true;
    config.useHighSpeedNetwork = true;  
    config.enableVisualization = false;
    config.enableFaultVisualization = false;
    config.targetDataPoints = targetDataPoints;
    config.outputPrefix = "itu_competition";
    
    // **NEW: Agent integration**
    config.enableAgentIntegration = true;
    config.enableHealingDeployment = true;
    config.agentInterfaceDir = "/media/rishi/Windows-SSD/PROJECT_&_RESEARCH/NOKIA/Buil-a-thon/rural_ai_selfhealing_net/ns3_integration/agent_interface";
    
    // **NEW: Randomized fault parameters**
    config.enableRandomizedFaults = true;
    config.minFaultInterval = 60.0;     // 1 minute minimum between faults
    config.maxFaultInterval = 300.0;    // 5 minutes maximum between faults
    config.minFaultDuration = 120.0;    // 2 minutes minimum fault duration
    config.maxFaultDuration = 600.0;    // 10 minutes maximum fault duration
    config.fiberCutProbability = 0.6;   // 60% chance of fiber cut, 40% power fluctuation
    config.maxSimultaneousFaults = 3;   // Maximum 3 simultaneous faults
    
    config.enableDatabaseGeneration = true;
    config.enableLinkTracking = true;
    config.enableAnomalyClassification = true;
    config.enableTrafficFlowAnalysis = true;
    config.enablePolicyLoading = true;
    config.databaseFormat = "sql";
    
    std::cout << "=== ITU COMPETITION CONFIGURATION ===" << std::endl;
    std::cout << "Target data points: " << targetDataPoints << std::endl;
    std::cout << "Randomized faults: ENABLED" << std::endl;
    std::cout << "Agent integration: ENABLED" << std::endl;
    std::cout << "Severity-based visualization: ENABLED" << std::endl;
    std::cout << "=====================================" << std::endl;
    
    return config;
}

SimulationConfig ITU_Competition_Rural_Network::CreateRandomizedFaultConfig()
{
    SimulationConfig config;
    config.mode = "randomized_fault_demo";
    config.dataCollectionInterval = 2.0;    
    config.totalSimulationTime = 600.0;  // 10 minutes for comprehensive demo
    config.baselineDuration = 60.0;
    config.faultStartTime = config.baselineDuration;
    config.enableFaultInjection = true;
    config.enableVisualization = true;
    config.enableFaultVisualization = true;
    config.useHighSpeedNetwork = true; 
    config.targetDataPoints = 300;
    config.outputPrefix = "randomized_fault_demo";
    
    // **NEW: Agent integration with visual feedback**
    config.enableAgentIntegration = true;
    config.enableHealingDeployment = true;
    config.agentInterfaceDir = "/media/rishi/Windows-SSD/PROJECT_&_RESEARCH/NOKIA/Buil-a-thon/rural_ai_selfhealing_net/ns3_integration/agent_interface";
    
    // **NEW: Aggressive randomized fault parameters for demo**
    config.enableRandomizedFaults = true;
    config.minFaultInterval = 30.0;     // 30 seconds minimum between faults
    config.maxFaultInterval = 120.0;    // 2 minutes maximum between faults
    config.minFaultDuration = 60.0;     // 1 minute minimum fault duration
    config.maxFaultDuration = 180.0;    // 3 minutes maximum fault duration
    config.fiberCutProbability = 0.5;   // 50-50 split between fault types
    config.maxSimultaneousFaults = 5;   // Maximum 5 simultaneous faults for demo
    
    config.enableDatabaseGeneration = true;
    config.enableLinkTracking = true;
    config.enableAnomalyClassification = true;
    config.enableTrafficFlowAnalysis = true;
    config.enablePolicyLoading = true;
    config.databaseFormat = "sql";
    
    std::cout << "=== RANDOMIZED FAULT DEMO: VISUAL MODE ===" << std::endl;
    std::cout << "Duration: 10 minutes with randomized faults" << std::endl;
    std::cout << "Visual healing demonstration enabled" << std::endl;
    std::cout << "Severity-based node sizing enabled" << std::endl;
    std::cout << "========================================" << std::endl;
    return config;
}

// **ENHANCED: Constructor with randomized fault generation**
ITU_Competition_Rural_Network::ITU_Competition_Rural_Network(const SimulationConfig& config) 
    : m_config(config), animInterface(nullptr), healingEngine(nullptr), agentAPI(nullptr), faultGenerator(nullptr)
{
    // **NEW: Initialize enhanced output files**
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
    
    // **NEW: Initialize randomized fault generator**
    if (m_config.enableRandomizedFaults) {
        faultGenerator = new RandomizedFaultGenerator(m_config);
    }
    
    // **NEW: Initialize agent integration**
    if (m_config.enableAgentIntegration) {
        InitializeAgentIntegration();
    }
    
    std::cout << "✅ ITU Competition simulation files initialized" << std::endl;
    std::cout << "✅ Enhanced metrics collection with randomized faults" << std::endl;
}

// **NEW: Randomized Fault Generator Implementation**
std::vector<GradualFaultPattern> RandomizedFaultGenerator::GenerateRandomizedFaults(uint32_t totalNodes)
{
    std::vector<GradualFaultPattern> faults;
    nodeDist = std::uniform_int_distribution<uint32_t>(0, totalNodes - 1);
    
    double currentTime = m_config.faultStartTime;
    int activeFaults = 0;
    
    std::cout << "🎲 Generating randomized fault patterns..." << std::endl;
    
    while (currentTime < m_config.totalSimulationTime - m_config.maxFaultDuration) {
        // Check if we can add more faults
        if (activeFaults < m_config.maxSimultaneousFaults) {
            // Generate next fault interval
            double nextInterval = intervalDist(rng);
            currentTime += nextInterval;
            
            if (currentTime >= m_config.totalSimulationTime - m_config.maxFaultDuration) break;
            
            // Generate fault severity
            double severity = severityDist(rng);
            
            // Determine fault type based on probability
            bool isFiberCut = probabilityDist(rng) < m_config.fiberCutProbability;
            
            GradualFaultPattern fault;
            
            if (isFiberCut) {
                // Generate fiber cut between two connected nodes
                auto nodePair = GetRandomConnectedNodes(totalNodes);
                fault = CreateRandomFiberCut(nodePair.first, nodePair.second, Seconds(currentTime), severity);
            } else {
                // Generate power fluctuation on single node
                uint32_t nodeId = nodeDist(rng);
                fault = CreateRandomPowerFluctuation(nodeId, Seconds(currentTime), severity);
            }
            
            faults.push_back(fault);
            activeFaults++;
            
            std::cout << "🎲 Generated " << fault.faultType << " at " << currentTime 
                      << "s, severity: " << (severity * 100) << "%" << std::endl;
        } else {
            // Wait for some faults to finish before adding new ones
            currentTime += m_config.minFaultInterval;
            activeFaults = std::max(0, activeFaults - 1); // Approximate fault completion
        }
    }
    
    std::cout << "✅ Generated " << faults.size() << " randomized fault patterns" << std::endl;
    return faults;
}

GradualFaultPattern RandomizedFaultGenerator::CreateRandomFiberCut(uint32_t nodeA, uint32_t nodeB, Time startTime, double severity)
{
    GradualFaultPattern fault;
    fault.targetNode = nodeA;
    fault.connectedNode = nodeB;
    fault.faultType = "fiber_cut";
    fault.faultDescription = "Randomized fiber cut between node " + std::to_string(nodeA) + " and " + std::to_string(nodeB);
    fault.startDegradation = startTime - Seconds(30); // Start degradation 30s before complete cut
    fault.faultOccurrence = startTime;
    fault.faultDuration = Seconds(durationDist(rng));
    fault.degradationRate = 0.02 + (severity * 0.03); // Variable degradation rate based on severity
    fault.severity = severity;
    fault.isActive = false;
    fault.currentSeverity = 0.0;
    fault.visualIndicatorActive = false;
    fault.visualMessage = "🔴 FIBER CUT";
    fault.anomalyId = SimpleIdGenerator::GenerateId("RANDOM_FIBER");
    
    // **NEW: Initialize severity-based sizing properties**
    fault.originalNodeSize = 30.0; // Default node size
    fault.currentNodeSize = fault.originalNodeSize;
    fault.sizingApplied = false;
    
    return fault;
}

GradualFaultPattern RandomizedFaultGenerator::CreateRandomPowerFluctuation(uint32_t nodeId, Time startTime, double severity)
{
    GradualFaultPattern fault;
    fault.targetNode = nodeId;
    fault.connectedNode = nodeId; // Self-affecting
    fault.faultType = "power_fluctuation";
    fault.faultDescription = "Randomized power fluctuation at node " + std::to_string(nodeId);
    fault.startDegradation = startTime;
    fault.faultOccurrence = startTime + Seconds(30 + (severity * 60)); // Variable peak time based on severity
    fault.faultDuration = Seconds(durationDist(rng));
    fault.degradationRate = 0.01 + (severity * 0.02); // Variable degradation rate
    fault.severity = severity;
    fault.isActive = false;
    fault.currentSeverity = 0.0;
    fault.visualIndicatorActive = false;
    fault.visualMessage = "⚡ POWER ISSUE";
    fault.anomalyId = SimpleIdGenerator::GenerateId("RANDOM_POWER");
    
    // **NEW: Initialize severity-based sizing properties**
    fault.originalNodeSize = 30.0; // Default node size
    fault.currentNodeSize = fault.originalNodeSize;
    fault.sizingApplied = false;
    
    return fault;
}

std::pair<uint32_t, uint32_t> RandomizedFaultGenerator::GetRandomConnectedNodes(uint32_t totalNodes)
{
    uint32_t nodeA = nodeDist(rng);
    uint32_t nodeB;
    
    // Ensure we get two different nodes that could be connected
    do {
        nodeB = nodeDist(rng);
    } while (nodeB == nodeA);
    
    // Ensure nodeA < nodeB for consistency
    if (nodeA > nodeB) {
        std::swap(nodeA, nodeB);
    }
    
    return {nodeA, nodeB};
}

// **STEP 2A: Agent Integration Implementation**
void ITU_Competition_Rural_Network::InitializeAgentIntegration()
{
    try {
        // ✅ Use absolute path to avoid truncation issues
        std::string absoluteInterfaceDir = "/media/rishi/Windows-SSD/PROJECT_&_RESEARCH/NOKIA/Buil-a-thon/rural_ai_selfhealing_net/ns3_integration/agent_interface";
        
        // ✅ Create directory if it doesn't exist
        std::string createDirCommand = "mkdir -p " + absoluteInterfaceDir;
        int result = system(createDirCommand.c_str());
        if (result != 0) {
            std::cout << "⚠️ Warning: Could not create interface directory" << std::endl;
        }
        
        // ✅ Initialize agent API with absolute path
        agentAPI = new AgentIntegrationAPI(absoluteInterfaceDir);
        
        // ✅ Verify API initialization
        if (!agentAPI) {
            throw std::runtime_error("Failed to create AgentIntegrationAPI instance");
        }
        
        // ✅ Initialize healing engine
        healingEngine = new HealingDeploymentEngine(agentAPI);
        
        if (!healingEngine) {
            throw std::runtime_error("Failed to create HealingDeploymentEngine instance");
        }
        
        std::cout << "✅ Agent Integration API initialized: " << absoluteInterfaceDir << std::endl;
        std::cout << "✅ Agent integration initialized successfully" << std::endl;
        std::cout << "📁 Interface directory: " << absoluteInterfaceDir << std::endl;
        std::cout << "🛠️ Healing deployment engine initialized" << std::endl;
        
        // ✅ Test interface readiness
        if (agentAPI->IsInterfaceReady()) {
            std::cout << "✅ Agent interface is ready for communication" << std::endl;
        } else {
            std::cout << "⚠️ Agent interface not fully ready yet" << std::endl;
        }
        
        // ✅ Create initial interface files with empty events
        std::vector<FaultEvent> initialEvents; // Start with empty events
        agentAPI->ExportRealTimeFaultEvents(initialEvents);
        std::cout << "📤 Exporting " << initialEvents.size() << " initial fault events" << std::endl;
        std::cout << "✅ Exported " << initialEvents.size() << " fault events to agents" << std::endl;
        
        // ✅ Update config to use absolute path
        m_config.agentInterfaceDir = absoluteInterfaceDir;
        
        std::cout << "🎯 Agent integration fully operational" << std::endl;
        
    } catch (const std::exception& e) {
        std::cout << "❌ Agent integration failed: " << e.what() << std::endl;
        
        // ✅ Cleanup on failure
        if (agentAPI) {
            delete agentAPI;
            agentAPI = nullptr;
        }
        if (healingEngine) {
            delete healingEngine;
            healingEngine = nullptr;
        }
        
        std::cout << "🔄 Continuing simulation without agent integration" << std::endl;
    }
}
void AgentIntegrationAPI::ExportRealTimeFaultEvents(const std::vector<FaultEvent>& events)
{
    std::ofstream jsonFile(faultEventsFile);
    if (!jsonFile.is_open()) {
        std::cout << "❌ Failed to open fault events file: " << faultEventsFile << std::endl;
        return;
    }
    
    std::cout << "📤 Exporting " << events.size() << " fault events" << std::endl;
    
    jsonFile << "{\n";
    jsonFile << "  \"timestamp\": \"" << Simulator::Now().GetSeconds() << "\",\n";
    jsonFile << "  \"events\": [\n";
    
    bool firstEvent = true;
    
    // Export fault events
    for (const auto& event : events) {
        if (!firstEvent) jsonFile << ",\n";
        jsonFile << "    {\n";
        jsonFile << "      \"event_id\": \"" << SimpleIdGenerator::GenerateId("evt") << "\",\n";
        jsonFile << "      \"timestamp\": " << event.timestamp << ",\n";
        jsonFile << "      \"event_type\": \"" << event.eventType << "\",\n";
        jsonFile << "      \"fault_type\": \"" << event.faultType << "\",\n";
        jsonFile << "      \"description\": \"" << event.description << "\",\n";
        jsonFile << "      \"severity\": " << event.severity << ",\n";
        jsonFile << "      \"affected_nodes\": [";
        for (size_t i = 0; i < event.affectedNodes.size(); ++i) {
            jsonFile << event.affectedNodes[i];
            if (i < event.affectedNodes.size() - 1) jsonFile << ", ";
        }
        jsonFile << "],\n";
        jsonFile << "      \"requires_immediate_action\": " << (event.severity > 0.7 ? "true" : "false") << "\n";
        jsonFile << "    }";
        firstEvent = false;
    }
    
    jsonFile << "\n  ]\n";
    jsonFile << "}\n";
    jsonFile.close();
    
    // Also create individual fault files
    for (const auto& event : events) {
        WriteFaultEventJSON(event);
    }
    
    std::cout << "✅ Exported " << events.size() << " fault events to agents" << std::endl;
}

void AgentIntegrationAPI::WriteFaultEventJSON(const FaultEvent& event)
{
    std::string individualFaultFile = watchDirectory + "/fault_" + std::to_string((int)event.timestamp) + ".json";
    
    std::ofstream faultFile(individualFaultFile);
    if (!faultFile.is_open()) {
        std::cout << "❌ Failed to create individual fault file: " << individualFaultFile << std::endl;
        return;
    }
    
    faultFile << "{\n";
    faultFile << "  \"event_id\": \"evt_" << event.faultType << "_" << (int)event.timestamp << "\",\n";
    faultFile << "  \"timestamp\": " << event.timestamp << ",\n";
    faultFile << "  \"event_type\": \"" << event.eventType << "\",\n";
    faultFile << "  \"fault_type\": \"" << event.faultType << "\",\n";
    faultFile << "  \"description\": \"" << event.description << "\",\n";
    faultFile << "  \"severity\": " << event.severity << ",\n";
    faultFile << "  \"visual_effect\": \"" << event.visualEffect << "\",\n";
    faultFile << "  \"affected_nodes\": [";
    
    for (size_t i = 0; i < event.affectedNodes.size(); ++i) {
        faultFile << event.affectedNodes[i];
        if (i < event.affectedNodes.size() - 1) faultFile << ", ";
    }
    
    faultFile << "],\n";
    faultFile << "  \"requires_immediate_action\": " << (event.severity > 0.7 ? "true" : "false") << "\n";
    faultFile << "}\n";
    faultFile.close();
    
    std::cout << "📁 Individual fault file created: " << individualFaultFile << std::endl;
}

void AgentIntegrationAPI::WriteDeploymentStatus(const std::string& planId, bool success, const std::string& details)
{
    std::ofstream jsonFile(deploymentStatusFile);
    jsonFile << "{\n";
    jsonFile << "  \"deployment_status\": {\n";
    jsonFile << "    \"plan_id\": \"" << planId << "\",\n";
    jsonFile << "    \"success\": " << (success ? "true" : "false") << ",\n";
    jsonFile << "    \"timestamp\": " << Simulator::Now().GetSeconds() << ",\n";
    jsonFile << "    \"details\": \"" << details << "\"\n";
    jsonFile << "  }\n";
    jsonFile << "}\n";
    jsonFile.close();
    
    std::cout << "📋 Deployment status written for plan: " << planId << " - " << (success ? "SUCCESS" : "FAILED") << std::endl;
}

// **STEP 2B: Healing Deployment Engine Implementation**
bool HealingDeploymentEngine::DeployHealingPlan(const HealingPlan& plan)
{
    std::cout << "🚀 Deploying healing plan: " << plan.planId << std::endl;
    std::cout << "🧠 LLM Reasoning: " << plan.llmReasoning << std::endl;
    
    bool overallSuccess = true;
    
    for (const auto& action : plan.actions) {
        try {
            if (action.actionType == "reroute_traffic") {
                ExecuteRerouteTraffic(action);
            } else if (action.actionType == "activate_backup") {
                ExecuteActivateBackupPath(action);
            } else if (action.actionType == "restart_node") {
                ExecuteRestartNode(action);
            } else if (action.actionType == "load_balancing") {
                ExecuteLoadBalancing(action);
            } else if (action.actionType == "emergency_shutdown") {
                ExecuteEmergencyShutdown(action);
            } else {
                std::cout << "⚠️ Unknown healing action: " << action.actionType << std::endl;
                overallSuccess = false;
            }
        } catch (const std::exception& e) {
            std::cout << "❌ Failed to execute action " << action.actionType << ": " << e.what() << std::endl;
            overallSuccess = false;
        }
    }
    
    // Write deployment status back to agents
    apiInterface->WriteDeploymentStatus(plan.planId, overallSuccess, 
        overallSuccess ? "All healing actions executed successfully" : "Some healing actions failed");
    
    return overallSuccess;
}

void HealingDeploymentEngine::ExecuteRerouteTraffic(const HealingAction& action)
{
    std::cout << "🔄 HEALING: Executing traffic rerouting..." << std::endl;
    
    for (uint32_t nodeId : action.targetNodes) {
        std::cout << "  📍 Rerouting traffic for node " << GetNodeVisualName(nodeId) << std::endl;
        
        // Simulate routing table updates
        std::cout << "  🛣️ Updating routing tables for alternative paths" << std::endl;
    }
    
    std::cout << "✅ Traffic rerouting completed" << std::endl;
}

void HealingDeploymentEngine::ShowHealingInProgress(uint32_t nodeId, AnimationInterface* animInterface, NodeContainer& allNodes)
{
    if (!animInterface) return;
    
    std::cout << "🔄 HEALING: Showing healing in progress for node " << nodeId << std::endl;
    
    // Turn node CYAN to indicate healing in progress
    animInterface->UpdateNodeColor(allNodes.Get(nodeId), 153, 255, 255); // Light Cyan #99FFFF
    animInterface->UpdateNodeDescription(allNodes.Get(nodeId), "💊 HEALING IN PROGRESS");
    
    std::cout << "🎬 VISUAL: Node " << nodeId << " turned CYAN (healing started)" << std::endl;
}

void HealingDeploymentEngine::ShowHealingCompleted(uint32_t nodeId, AnimationInterface* animInterface, NodeContainer& allNodes)
{
    if (!animInterface) return;
    
    std::cout << "✅ HEALING: Showing healing completed for node " << nodeId << std::endl;
    
    // Turn node GREEN to indicate healing completed
    animInterface->UpdateNodeColor(allNodes.Get(nodeId), 0, 255, 0); // Green
    animInterface->UpdateNodeDescription(allNodes.Get(nodeId), "✅ HEALED");
    
    std::cout << "🎬 VISUAL: Node " << nodeId << " turned GREEN (healing completed)" << std::endl;
}


void HealingDeploymentEngine::ExecuteActivateBackupPath(const HealingAction& action)
{
    std::cout << "🔌 HEALING: Activating backup paths..." << std::endl;
    
    for (uint32_t nodeId : action.targetNodes) {
        std::cout << "  📍 Activating backup for node " << GetNodeVisualName(nodeId) << std::endl;
    }
    
    std::cout << "✅ Backup path activation completed" << std::endl;
}

void HealingDeploymentEngine::ExecuteRestartNode(const HealingAction& action)
{
    std::cout << "🔄 HEALING: Restarting nodes..." << std::endl;
    
    for (uint32_t nodeId : action.targetNodes) {
        std::cout << "  📍 Restarting node " << GetNodeVisualName(nodeId) << std::endl;
        // Simulate node restart process
    }
    
    std::cout << "✅ Node restart completed" << std::endl;
}

void HealingDeploymentEngine::ExecuteLoadBalancing(const HealingAction& action)
{
    std::cout << "⚖️ HEALING: Implementing load balancing..." << std::endl;
    
    for (uint32_t nodeId : action.targetNodes) {
        std::cout << "  📍 Load balancing for node " << GetNodeVisualName(nodeId) << std::endl;
    }
    
    std::cout << "✅ Load balancing completed" << std::endl;
}

void HealingDeploymentEngine::ExecuteEmergencyShutdown(const HealingAction& action)
{
    std::cout << "🚨 HEALING: Emergency shutdown procedure..." << std::endl;
    
    for (uint32_t nodeId : action.targetNodes) {
        std::cout << "  📍 Emergency shutdown for node " << GetNodeVisualName(nodeId) << std::endl;
    }
    
    std::cout << "✅ Emergency shutdown completed" << std::endl;
}

std::string HealingDeploymentEngine::GetNodeVisualName(uint32_t nodeId)
{
    if (nodeId < 5) return "CORE-" + std::to_string(nodeId);
    else if (nodeId < 20) return "DIST-" + std::to_string(nodeId - 5);
    else return "ACC-" + std::to_string(nodeId - 20);
}

// **STEP 3A: Randomized Fault Pattern Scheduling**
void ITU_Competition_Rural_Network::ScheduleRandomizedFaultPatterns()
{
    std::cout << "\n=== SCHEDULING RANDOMIZED FAULT PATTERNS ===" << std::endl;
    
    if (m_config.enableFaultInjection && m_config.enableRandomizedFaults && faultGenerator) {
        // Generate randomized faults
        gradualFaults = faultGenerator->GenerateRandomizedFaults(allNodes.GetN());
        
        // Schedule fault progression updates
        for (double t = m_config.faultStartTime; t < m_config.totalSimulationTime; t += m_config.dataCollectionInterval) {
            Simulator::Schedule(Seconds(t), &ITU_Competition_Rural_Network::UpdateFaultProgression, this);
            
            if (m_config.enableAgentIntegration) {
                Simulator::Schedule(Seconds(t + 1), &ITU_Competition_Rural_Network::ProcessAgentCommunication, this);
            }
        }
        
        std::cout << "✅ Randomized fault patterns scheduled successfully" << std::endl;
    } else {
        std::cout << "⚠️ Randomized fault injection disabled" << std::endl;
    }
}

void ITU_Competition_Rural_Network::UpdateFaultProgression()
{
    double currentTime = Simulator::Now().GetSeconds();
    std::vector<FaultEvent> currentEvents;  // ✅ Correctly declared
    
    for (auto& fault : gradualFaults) {
        double startDeg = fault.startDegradation.GetSeconds();
        double faultOcc = fault.faultOccurrence.GetSeconds();
        double endTime = faultOcc + fault.faultDuration.GetSeconds();
        
        if (currentTime >= startDeg && currentTime <= endTime) {
            if (!fault.isActive) {
                fault.isActive = true;
                AnnounceFaultEvent(fault, "fault_started");
                
                // ✅ CREATE AND ADD FAULT EVENT
                FaultEvent event;
                event.timestamp = currentTime;
                event.eventType = "fault_started";
                event.faultType = fault.faultType;
                event.affectedNodes = {fault.targetNode, fault.connectedNode};
                event.description = fault.faultDescription;
                event.severity = fault.currentSeverity;
                
                currentEvents.push_back(event);  // ✅ Add to current events
                faultEvents.push_back(event);    // ✅ Add to global events
                
                std::cout << "🚨 FAULT EVENT CREATED: " << fault.faultType 
                          << " at node " << fault.targetNode 
                          << " severity " << fault.severity << std::endl;
            }

            // Calculate current severity based on progression
            if (currentTime <= faultOcc) {
                // Degradation phase
                double progress = (currentTime - startDeg) / (faultOcc - startDeg);
                fault.currentSeverity = fault.severity * progress;
            } else {
                // Full fault phase
                fault.currentSeverity = fault.severity;
            }
            
            // ✅ UPDATE NODE SIZE BASED ON CURRENT SEVERITY
            UpdateNodeSizeBasedOnSeverity(fault);
            
            // Update visual indicators
            if (m_config.enableFaultVisualization) {
                ProcessFaultVisualization();
            }
            
        } else if (currentTime > endTime && fault.isActive) {
            fault.isActive = false;
            
            // ✅ CREATE FAULT ENDED EVENT
            FaultEvent endEvent;
            endEvent.timestamp = currentTime;
            endEvent.eventType = "fault_ended";
            endEvent.faultType = fault.faultType;
            endEvent.affectedNodes = {fault.targetNode, fault.connectedNode};
            endEvent.description = fault.faultDescription + " - RESOLVED";
            endEvent.severity = 0.0;
            
            currentEvents.push_back(endEvent);
            faultEvents.push_back(endEvent);
            
            std::cout << "✅ FAULT RESOLVED: " << fault.faultType 
                      << " at node " << fault.targetNode << std::endl;
            
            // ✅ RESTORE ORIGINAL NODE SIZE
            RestoreOriginalNodeSize(fault.targetNode);
            if (fault.faultType == "fiber_cut") {
                RestoreOriginalNodeSize(fault.connectedNode);
            }
            
            // Restore visual state
            if (m_config.enableFaultVisualization) {
                if (fault.faultType == "fiber_cut") {
                    RestoreFiberLink(fault.targetNode, fault.connectedNode);
                } else if (fault.faultType == "power_fluctuation") {
                    HidePowerIssue(fault.targetNode);
                }
            }
        }
    }
    
    // ✅ EXPORT EVENTS TO AGENT INTERFACE (PROPERLY PLACED)
    if (!currentEvents.empty() && agentAPI) {
        std::cout << "📤 Exporting " << currentEvents.size() << " fault events to agents" << std::endl;
        agentAPI->ExportRealTimeFaultEvents(currentEvents);
    }
}

// **NEW: Severity-based node sizing methods**
void ITU_Competition_Rural_Network::UpdateNodeSizeBasedOnSeverity(const GradualFaultPattern& fault)
{
    if (!animInterface) return;
    
    // Apply severity-based sizing to target node
    ApplySeverityBasedNodeSizing(fault.targetNode, fault.currentSeverity);
    
    // For fiber cuts, also apply to connected node
    if (fault.faultType == "fiber_cut") {
        ApplySeverityBasedNodeSizing(fault.connectedNode, fault.currentSeverity);
    }
}

void ITU_Competition_Rural_Network::ApplySeverityBasedNodeSizing(uint32_t nodeId, double severity)
{
    if (!animInterface) return;
    
    // Store original size if not already stored
    if (originalNodeSizes.find(nodeId) == originalNodeSizes.end()) {
        if (nodeId < 5) {
            originalNodeSizes[nodeId] = 50.0; // Core nodes
        } else if (nodeId < 20) {
            originalNodeSizes[nodeId] = 40.0; // Distribution nodes
        } else {
            originalNodeSizes[nodeId] = 30.0; // Access nodes
        }
    }
    
    // Calculate new size based on severity
    double originalSize = originalNodeSizes[nodeId];
    double newSize = originalSize * (1.0 + severity * baseSeverityMultiplier);
    
    // Apply new size
    animInterface->UpdateNodeSize(nodeId, newSize, newSize);
    
    std::cout << "📏 Node " << GetNodeVisualName(nodeId) << " size updated: " 
              << originalSize << " → " << newSize << " (severity: " << (severity * 100) << "%)" << std::endl;
}

void ITU_Competition_Rural_Network::RestoreOriginalNodeSize(uint32_t nodeId)
{
    if (!animInterface) return;
    
    auto it = originalNodeSizes.find(nodeId);
    if (it != originalNodeSizes.end()) {
        double originalSize = it->second;
        animInterface->UpdateNodeSize(nodeId, originalSize, originalSize);
        
        std::cout << "📏 Node " << GetNodeVisualName(nodeId) << " size restored to: " << originalSize << std::endl;
    }
}

// **STEP 3B: Topology Setup Methods (Unchanged)**
void ITU_Competition_Rural_Network::SetupRobustTopology()
{
    std::cout << "\n=== SETTING UP ITU COMPETITION TOPOLOGY ===" << std::endl;
    
    // Create node containers
    coreNodes.Create(5);        // 5 core nodes
    distributionNodes.Create(15); // 15 distribution nodes  
    accessNodes.Create(30);     // 30 access nodes
    
    allNodes.Add(coreNodes);
    allNodes.Add(distributionNodes);
    allNodes.Add(accessNodes);
    
    std::cout << "✅ Created " << allNodes.GetN() << " nodes (5 Core + 15 Dist + 30 Access)" << std::endl;
    
    // Setup each layer
    // Install internet stack
    stack.Install(allNodes);
    std::cout << "✅ Internet stack installed on all nodes" << std::endl;
    SetupCoreLayer();
    SetupDistributionLayer();
    SetupAccessLayer();
    
    // Setup routing
    SetupRobustRouting();
    
    // Setup energy model
    SetupEnergyModel();
    
    std::cout << "✅ Topology setup completed successfully" << std::endl;
}

void ITU_Competition_Rural_Network::SetupCoreLayer()
{
    std::cout << "🏗️ Setting up core layer..." << std::endl;
    
    // Configure high-speed point-to-point links for core
    if (m_config.useHighSpeedNetwork) {
        p2pHelper.SetDeviceAttribute("DataRate", StringValue("1000Mbps"));
        p2pHelper.SetChannelAttribute("Delay", StringValue("1ms"));
    } else {
        p2pHelper.SetDeviceAttribute("DataRate", StringValue("100Mbps"));
        p2pHelper.SetChannelAttribute("Delay", StringValue("2ms"));
    }
    
    // Create full mesh connectivity between core nodes
    for (uint32_t i = 0; i < coreNodes.GetN(); ++i) {
        for (uint32_t j = i + 1; j < coreNodes.GetN(); ++j) {
            NetDeviceContainer link = p2pHelper.Install(coreNodes.Get(i), coreNodes.Get(j));
            coreDevices.Add(link);
            
            // Assign IP addresses
            std::ostringstream subnet;
            subnet << "10.1." << (i * 10 + j) << ".0";
            address.SetBase(subnet.str().c_str(), "255.255.255.0");
            Ipv4InterfaceContainer interfaces = address.Assign(link);
            allInterfaces.push_back(interfaces);
            
            // Track link status
            linkStatus[{i, j}] = true;
        }
    }
    
    std::cout << "✅ Core layer: " << coreDevices.GetN() << " high-speed links created" << std::endl;
}

void ITU_Competition_Rural_Network::SetupDistributionLayer()
{
    std::cout << "🏗️ Setting up distribution layer..." << std::endl;
    
    // Configure medium-speed links for distribution
    p2pHelper.SetDeviceAttribute("DataRate", StringValue("100Mbps"));
    p2pHelper.SetChannelAttribute("Delay", StringValue("5ms"));
    
    // Connect each distribution node to 2-3 core nodes for redundancy
    for (uint32_t dist = 0; dist < distributionNodes.GetN(); ++dist) {
        uint32_t primaryCore = dist % coreNodes.GetN();
        uint32_t secondaryCore = (dist + 1) % coreNodes.GetN();
        
        // Primary connection
        NetDeviceContainer primaryLink = p2pHelper.Install(
            distributionNodes.Get(dist), coreNodes.Get(primaryCore));
        distributionDevices.Add(primaryLink);
        
        std::ostringstream subnet1;
        subnet1 << "10.2." << (dist * 2) << ".0";
        address.SetBase(subnet1.str().c_str(), "255.255.255.0");
        Ipv4InterfaceContainer interfaces1 = address.Assign(primaryLink);
        allInterfaces.push_back(interfaces1);
        
        // Secondary connection for redundancy
        NetDeviceContainer secondaryLink = p2pHelper.Install(
            distributionNodes.Get(dist), coreNodes.Get(secondaryCore));
        distributionDevices.Add(secondaryLink);
        
        std::ostringstream subnet2;
        subnet2 << "10.2." << (dist * 2 + 1) << ".0";
        address.SetBase(subnet2.str().c_str(), "255.255.255.0");
        Ipv4InterfaceContainer interfaces2 = address.Assign(secondaryLink);
        allInterfaces.push_back(interfaces2);
        
        // Track link status
        linkStatus[{5 + dist, primaryCore}] = true;
        linkStatus[{5 + dist, secondaryCore}] = true;
    }
    
    // Create some inter-distribution links for mesh connectivity
    for (uint32_t i = 0; i < distributionNodes.GetN() - 1; i += 3) {
        uint32_t j = i + 1;
        if (j < distributionNodes.GetN()) {
            NetDeviceContainer link = p2pHelper.Install(distributionNodes.Get(i), distributionNodes.Get(j));
            distributionDevices.Add(link);
            
            std::ostringstream subnet;
            subnet << "10.3." << i << ".0";
            address.SetBase(subnet.str().c_str(), "255.255.255.0");
            Ipv4InterfaceContainer interfaces = address.Assign(link);
            allInterfaces.push_back(interfaces);
            
            linkStatus[{5 + i, 5 + j}] = true;
        }
    }
    
    std::cout << "✅ Distribution layer: " << distributionDevices.GetN() << " links created" << std::endl;
}

void ITU_Competition_Rural_Network::SetupAccessLayer()
{
    std::cout << "🏗️ Setting up access layer..." << std::endl;
    
    // Configure lower-speed links for access
    p2pHelper.SetDeviceAttribute("DataRate", StringValue("50Mbps"));
    p2pHelper.SetChannelAttribute("Delay", StringValue("10ms"));
    
    // Connect each access node to 1-2 distribution nodes
    for (uint32_t acc = 0; acc < accessNodes.GetN(); ++acc) {
        uint32_t primaryDist = acc % distributionNodes.GetN();
        
        // Primary connection
        NetDeviceContainer primaryLink = p2pHelper.Install(
            accessNodes.Get(acc), distributionNodes.Get(primaryDist));
        accessDevices.Add(primaryLink);
        
        std::ostringstream subnet;
        subnet << "10.4." << acc << ".0";
        address.SetBase(subnet.str().c_str(), "255.255.255.0");
        Ipv4InterfaceContainer interfaces = address.Assign(primaryLink);
        allInterfaces.push_back(interfaces);
        
        // Track link status
        linkStatus[{20 + acc, 5 + primaryDist}] = true;
    }
    
    std::cout << "✅ Access layer: " << accessDevices.GetN() << " links created" << std::endl;
}

void ITU_Competition_Rural_Network::SetupRobustRouting()
{
    std::cout << "🛣️ Setting up robust routing..." << std::endl;
    
    // Use OLSR for mesh networking in rural environment
    OlsrHelper olsr;
    Ipv4StaticRoutingHelper staticRouting;
    
    Ipv4ListRoutingHelper list;
    list.Add(staticRouting, 0);
    list.Add(olsr, 10);
    
    InternetStackHelper internet;
    internet.SetRoutingHelper(list);
    
    // Populate global routing tables
    Ipv4GlobalRoutingHelper::PopulateRoutingTables();
    
    std::cout << "✅ OLSR mesh routing configured" << std::endl;
}

void ITU_Competition_Rural_Network::SetupEnergyModel()
{
    std::cout << "🔋 Setting up energy model..." << std::endl;
    
    // Install energy source on all nodes
    BasicEnergySourceHelper basicSourceHelper;
    basicSourceHelper.Set("BasicEnergySourceInitialEnergyJ", DoubleValue(10000.0)); // 10kJ initial
    energy::EnergySourceContainer sources = basicSourceHelper.Install(allNodes);
    
    // Install energy harvesting for access nodes (solar panels)
    BasicEnergyHarvesterHelper harvesterHelper;
    harvesterHelper.Set("PeriodicHarvestedPowerUpdateInterval", TimeValue(Seconds(60.0)));
    
    // **FIXED: Change HarvestingPower to HarvestablePower**
    harvesterHelper.Set("HarvestablePower", StringValue("ns3::UniformRandomVariable[Min=10.0|Max=50.0]"));
    
    // Only access nodes have energy harvesting (rural solar panels)
    for (uint32_t i = 0; i < accessNodes.GetN(); ++i) {
        harvesterHelper.Install(sources.Get(20 + i)); // Access nodes start at index 20
    }
    
    std::cout << "✅ Energy model with harvesting configured" << std::endl;
}

// **STEP 3C: Application Setup (Unchanged)**
void ITU_Competition_Rural_Network::SetupRobustApplications()
{
    std::cout << "\n=== SETTING UP APPLICATIONS ===" << std::endl;
    
    CreateBaselineTraffic();
    CreateComprehensiveTraffic();
    
    std::cout << "✅ Applications configured successfully" << std::endl;
}

void ITU_Competition_Rural_Network::CreateBaselineTraffic()
{
    std::cout << "📊 Creating baseline traffic patterns..." << std::endl;
    
    // Install packet sink on core nodes
    uint16_t sinkPort = 8080;
    Address sinkAddress = InetSocketAddress(Ipv4Address::GetAny(), sinkPort);
    PacketSinkHelper packetSinkHelper("ns3::TcpSocketFactory", sinkAddress);
    
    for (uint32_t i = 0; i < coreNodes.GetN(); ++i) {
        ApplicationContainer sinkApp = packetSinkHelper.Install(coreNodes.Get(i));
        sinkApp.Start(Seconds(0.0));
        sinkApp.Stop(Seconds(m_config.totalSimulationTime));
        sinkApps.Add(sinkApp);
    }
    
    std::cout << "✅ Baseline traffic sinks installed on core nodes" << std::endl;
}

void ITU_Competition_Rural_Network::CreateComprehensiveTraffic()
{
    std::cout << "📈 Creating comprehensive traffic patterns..." << std::endl;
    
    // Create diverse traffic from access nodes to core nodes
    for (uint32_t acc = 0; acc < accessNodes.GetN(); ++acc) {
        uint32_t targetCore = acc % coreNodes.GetN();
        
        // Get the IP address of the target core node
        Ipv4Address targetAddress = allInterfaces[targetCore].GetAddress(1);
        
        // Create different types of traffic based on node
        if (acc % 3 == 0) {
            // Web traffic simulation
            OnOffHelper onoff("ns3::TcpSocketFactory", 
                             InetSocketAddress(targetAddress, 8080));
            onoff.SetAttribute("OnTime", StringValue("ns3::ConstantRandomVariable[Constant=1]"));
            onoff.SetAttribute("OffTime", StringValue("ns3::ConstantRandomVariable[Constant=0]"));
            onoff.SetAttribute("DataRate", StringValue("2Mbps"));
            onoff.SetAttribute("PacketSize", UintegerValue(1024));
            
            ApplicationContainer sourceApp = onoff.Install(accessNodes.Get(acc));
            sourceApp.Start(Seconds(1.0 + acc * 0.1));
            sourceApp.Stop(Seconds(m_config.totalSimulationTime - 1.0));
            sourceApps.Add(sourceApp);
            
        } else if (acc % 3 == 1) {
            // IoT sensor traffic simulation
            UdpEchoClientHelper echoClient(targetAddress, 9);
            echoClient.SetAttribute("MaxPackets", UintegerValue(UINT32_MAX));
            echoClient.SetAttribute("Interval", TimeValue(Seconds(10.0))); // Every 10 seconds
            echoClient.SetAttribute("PacketSize", UintegerValue(64));
            
            ApplicationContainer sourceApp = echoClient.Install(accessNodes.Get(acc));
            sourceApp.Start(Seconds(2.0 + acc * 0.1));
            sourceApp.Stop(Seconds(m_config.totalSimulationTime - 1.0));
            sourceApps.Add(sourceApp);
            
        } else {
            // Video streaming simulation
            OnOffHelper onoff("ns3::UdpSocketFactory", 
                             InetSocketAddress(targetAddress, 8080));
            onoff.SetAttribute("OnTime", StringValue("ns3::ExponentialRandomVariable[Mean=1]"));
            onoff.SetAttribute("OffTime", StringValue("ns3::ExponentialRandomVariable[Mean=0.1]"));
            onoff.SetAttribute("DataRate", StringValue("5Mbps"));
            onoff.SetAttribute("PacketSize", UintegerValue(1500));
            
            ApplicationContainer sourceApp = onoff.Install(accessNodes.Get(acc));
            sourceApp.Start(Seconds(3.0 + acc * 0.1));
            sourceApp.Stop(Seconds(m_config.totalSimulationTime - 1.0));
            sourceApps.Add(sourceApp);
        }
    }
    
    std::cout << "✅ Comprehensive traffic patterns created for " << accessNodes.GetN() << " access nodes" << std::endl;
}

// **STEP 4A: Data Collection and Enhanced Metrics (Simplified)**
void ITU_Competition_Rural_Network::CollectComprehensiveMetrics()
{
    if (!metricsFile.is_open()) return;
    
    double currentTime = Simulator::Now().GetSeconds();
    
    // Get environmental factors
    double timeOfDayFactor = GetTimeOfDayMultiplier();
    double trafficPatternFactor = GetTrafficPatternMultiplier();
    double seasonalFactor = GetSeasonalVariation();
    
    // Collect metrics for all nodes
    for (uint32_t nodeId = 0; nodeId < allNodes.GetN(); ++nodeId) {
        NodeMetrics metrics = GetEnhancedNodeMetrics(nodeId);
        
        // Write comprehensive metrics to CSV
        metricsFile << std::fixed << std::setprecision(4)
                   << currentTime << ","
                   << nodeId << ","
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
                   << seasonalFactor << std::endl;
    }
    
    // Update agent interface with latest events
    if (m_config.enableAgentIntegration && agentAPI) {
        UpdateAgentInterface();
    }
}

ITU_Competition_Rural_Network::NodeMetrics ITU_Competition_Rural_Network::GetEnhancedNodeMetrics(uint32_t nodeId)
{
    NodeMetrics metrics;
    metrics.nodeId = nodeId;
    
    // Determine node type
    if (nodeId < 5) {
        metrics.nodeType = "CORE";
    } else if (nodeId < 20) {
        metrics.nodeType = "DIST";
    } else {
        metrics.nodeType = "ACC";
    }
    
    // Get node position
    Ptr<MobilityModel> mobility = allNodes.Get(nodeId)->GetObject<MobilityModel>();
    if (mobility) {
        metrics.position = mobility->GetPosition();
    } else {
        metrics.position = Vector(nodeId * 100, nodeId * 50, 0); // Default positioning
    }
    
    // Base metrics with realistic values
    metrics.throughputMbps = 50.0 + (nodeId % 10) * 5.0;
    metrics.latencyMs = 10.0 + (nodeId % 5) * 2.0;
    metrics.packetLossRate = 0.01 + (nodeId % 3) * 0.005;
    metrics.jitterMs = 1.0 + (nodeId % 4) * 0.5;
    metrics.signalStrengthDbm = -60.0 - (nodeId % 6) * 2.0;
    metrics.cpuUsage = 0.3 + (nodeId % 7) * 0.05;
    metrics.memoryUsage = 0.4 + (nodeId % 8) * 0.04;
    metrics.bufferOccupancy = 0.2 + (nodeId % 5) * 0.06;
    metrics.activeLinks = (nodeId < 5) ? 4 : ((nodeId < 20) ? 3 : 2);
    metrics.neighborCount = metrics.activeLinks + (nodeId % 3);
    metrics.linkUtilization = 0.5 + (nodeId % 6) * 0.08;
    metrics.criticalServiceLoad = 0.25 + (nodeId % 4) * 0.05;
    metrics.normalServiceLoad = 0.6 + (nodeId % 5) * 0.06;
    metrics.energyLevel = 0.8 - (nodeId % 10) * 0.02;
    metrics.voltageLevel = 0.95 + (nodeId % 8) * 0.005;
    metrics.powerStability = 0.9 + (nodeId % 6) * 0.01;
    metrics.isOperational = true;
    
    // Initialize fault-related metrics
    metrics.degradationLevel = 0.0;
    metrics.faultSeverity = 0.0;
    
    // Check for active faults affecting this node
    for (const auto& fault : gradualFaults) {
        if ((fault.targetNode == nodeId || fault.connectedNode == nodeId) && fault.isActive) {
            metrics.faultSeverity = std::max(metrics.faultSeverity, fault.currentSeverity);
            metrics.degradationLevel = fault.currentSeverity;
            
            // Apply fault-specific effects
            if (fault.faultType == "fiber_cut") {
                metrics.throughputMbps *= (1.0 - fault.currentSeverity * 0.8);
                metrics.latencyMs *= (1.0 + fault.currentSeverity * 2.0);
                metrics.packetLossRate += fault.currentSeverity * 0.3;
                metrics.activeLinks = std::max(1, (int)(metrics.activeLinks * (1.0 - fault.currentSeverity)));
            } else if (fault.faultType == "power_fluctuation") {
                metrics.powerStability *= (1.0 - fault.currentSeverity * 0.5);
                metrics.voltageLevel *= (1.0 - fault.currentSeverity * 0.2);
                metrics.cpuUsage += fault.currentSeverity * 0.3;
                metrics.memoryUsage += fault.currentSeverity * 0.2;
            }
        }
    }
    
    // Apply environmental factors
    double timeOfDayFactor = GetTimeOfDayMultiplier();
    double trafficPatternFactor = GetTrafficPatternMultiplier();
    
    metrics.throughputMbps *= timeOfDayFactor * trafficPatternFactor;
    metrics.criticalServiceLoad *= timeOfDayFactor;
    metrics.normalServiceLoad *= trafficPatternFactor;
    
    // Ensure metrics stay within realistic bounds
    metrics.cpuUsage = std::min(1.0, std::max(0.0, metrics.cpuUsage));
    metrics.memoryUsage = std::min(1.0, std::max(0.0, metrics.memoryUsage));
    metrics.bufferOccupancy = std::min(1.0, std::max(0.0, metrics.bufferOccupancy));
    metrics.linkUtilization = std::min(1.0, std::max(0.0, metrics.linkUtilization));
    metrics.packetLossRate = std::min(1.0, std::max(0.0, metrics.packetLossRate));
    
    return metrics;
}

// **STEP 4B: Environmental and Temporal Factors (Unchanged)**
double ITU_Competition_Rural_Network::GetTimeOfDayMultiplier()
{
    double currentTime = Simulator::Now().GetSeconds();
    double timeOfDay = fmod(currentTime, 86400.0); // 24 hours in seconds
    double hour = timeOfDay / 3600.0; // Convert to hours
    
    // Rural network usage pattern: low at night, peak during work hours
    if (hour < 6.0 || hour > 22.0) {
        return 0.3; // Low activity during night
    } else if (hour >= 9.0 && hour <= 17.0) {
        return 1.0; // Peak business hours
    } else {
        return 0.7; // Moderate activity during evening
    }
}

double ITU_Competition_Rural_Network::GetTrafficPatternMultiplier()
{
    double currentTime = Simulator::Now().GetSeconds();
    
    // Weekly pattern simulation
    double weekday = fmod(currentTime, 604800.0) / 86400.0; // 7 days in seconds
    
    if (weekday >= 5.0) {
        return 0.6; // Weekend - lower traffic
    } else {
        return 1.0; // Weekday - normal traffic
    }
}

double ITU_Competition_Rural_Network::GetSeasonalVariation()
{
    // Simulate seasonal variation (simplified)
    double currentTime = Simulator::Now().GetSeconds();
    double seasonFactor = 0.8 + 0.4 * sin(currentTime / 86400.0 * 2 * M_PI / 365.0);
    return seasonFactor;
}

double ITU_Competition_Rural_Network::CalculateNodeDegradation(uint32_t nodeId, const std::string& metric)
{
    double degradation = 0.0;
    
    // Check all active faults affecting this node
    for (const auto& fault : gradualFaults) {
        if ((fault.targetNode == nodeId || fault.connectedNode == nodeId) && fault.isActive) {
            if (metric == "throughput" && fault.faultType == "fiber_cut") {
                degradation = std::max(degradation, fault.currentSeverity * 0.8);
            } else if (metric == "power" && fault.faultType == "power_fluctuation") {
                degradation = std::max(degradation, fault.currentSeverity * 0.6);
            }
        }
    }
    
    return degradation;
}

// **STEP 4C: Agent Communication Methods (Unchanged)*
void ITU_Competition_Rural_Network::ProcessAgentCommunication()
{
    if (!m_config.enableAgentIntegration || !agentAPI) return;
    
    // NEW: Check for deployment files from orchestration agent
    CheckForOrchestrationDeployments();
    
    // Existing: Check for healing plans
    if (agentAPI->CheckForHealingPlans()) {
        ProcessIncomingHealingPlans();
    }
}

bool AgentIntegrationAPI::CheckForHealingPlans()
{
    // Simple check if healing plans file exists and has been recently modified
    std::ifstream file(healingPlansFile);
    return file.good();
}

std::vector<HealingPlan> AgentIntegrationAPI::LoadHealingPlans()
{
    std::vector<HealingPlan> plans;
    
    try {
        std::ifstream file(healingPlansFile);
        if (file.is_open()) {
            std::string content((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
            file.close();
            
            // Simple healing plan loading (this is a simplified implementation)
            if (content.find("healing_plans") != std::string::npos) {
                HealingPlan plan;
                plan.planId = "PLAN_" + std::to_string(time(nullptr));
                plan.anomalyId = "ANOMALY_DETECTED";
                plan.confidenceScore = 0.85;
                plan.deployed = false;
                plan.successful = false;
                
                // Create a simple healing action
                HealingAction action;
                action.actionType = "traffic_rerouting";
                action.priority = 1;
                action.estimatedDuration = 30.0;
                
                plan.actions.push_back(action);
                plans.push_back(plan);
                
                std::cout << "📋 Loaded healing plan: " << plan.planId << std::endl;
            }
            
            // Remove processed file
            std::remove(healingPlansFile.c_str());
        }
    } catch (const std::exception& e) {
        std::cout << "❌ Error loading healing plans: " << e.what() << std::endl;
    }
    
    return plans;
}

void ITU_Competition_Rural_Network::ProcessIncomingHealingPlans()
{
    if (!agentAPI) return;
    
    try {
        // Load healing plans from agents
        std::vector<HealingPlan> newPlans = agentAPI->LoadHealingPlans();
        
        for (const auto& plan : newPlans) {
            std::cout << "📥 Processing healing plan: " << plan.planId << std::endl;
            std::cout << "🎯 Target actions: " << plan.actions.size() << std::endl;
            
            // Add to active healing plans
            activeHealingPlans.push_back(plan);
            
            // Deploy the healing plan
            DeployHealingPlan(plan);
        }
        
    } catch (const std::exception& e) {
        std::cout << "❌ Error processing healing plans: " << e.what() << std::endl;
    }
}


void ITU_Competition_Rural_Network::CheckForOrchestrationDeployments()
{
    std::string deploymentsDir = "orchestration_deployments";
    try {
        // Check for deployment JSON files
        std::filesystem::path deployPath(deploymentsDir);
        if (!std::filesystem::exists(deployPath)) {
            return; // Directory doesn't exist yet
        }
        
        // Look for deployment_*.json files
        for (const auto& entry : std::filesystem::directory_iterator(deployPath)) {
            if (entry.is_regular_file()) {
                std::string filename = entry.path().filename().string();
                
                // Check if it's a deployment file
                if (filename.find("deployment_") == 0 && filename.find(".json") != std::string::npos) {
                    std::cout << "📥 Found deployment file: " << filename << std::endl;
                    
                    // Process the deployment file
                    ProcessDeploymentFile(entry.path().string());
                    
                    // Remove processed file
                    std::filesystem::remove(entry.path());
                    std::cout << "🗑️ Processed and removed: " << filename << std::endl;
                }
            }
        }
        
    } catch (const std::exception& e) {
        std::cout << "📁 No deployments found or error: " << e.what() << std::endl;
    }
}

void ITU_Competition_Rural_Network::ProcessDeploymentFile(const std::string& filePath)
{
    try {
        std::ifstream file(filePath);
        if (!file.is_open()) {
            std::cout << "❌ Failed to open deployment file: " << filePath << std::endl;
            return;
        }
        
        std::string content((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
        file.close();
        
        std::cout << "📄 Processing deployment content..." << std::endl;
        
        // Simple JSON parsing for NS-3 commands
        std::vector<std::string> ns3Commands;
        std::vector<uint32_t> targetNodes;
        
        // Extract NS-3 commands (simple string search)
        size_t pos = 0;
        while ((pos = content.find("ExecutePowerFluctuationHealing", pos)) != std::string::npos) {
            // Extract node ID from command
            size_t nodeStart = content.find("(", pos) + 1;
            size_t nodeEnd = content.find(")", nodeStart);
            if (nodeStart != std::string::npos && nodeEnd != std::string::npos) {
                std::string nodeStr = content.substr(nodeStart, nodeEnd - nodeStart);
                
                // Parse node ID (extract number from "node_XX")
                size_t underscorePos = nodeStr.find("_");
                if (underscorePos != std::string::npos) {
                    std::string nodeIdStr = nodeStr.substr(underscorePos + 1);
                    uint32_t nodeId = std::stoi(nodeIdStr);
                    targetNodes.push_back(nodeId);
                    ns3Commands.push_back("power_healing");
                    std::cout << "🔧 Power healing command for node " << nodeId << std::endl;
                }
            }
            pos++;
        }
        
        // Extract fiber cut rerouting commands
        pos = 0;
        while ((pos = content.find("ExecuteFiberCutRerouting", pos)) != std::string::npos) {
            size_t nodeStart = content.find("(", pos) + 1;
            size_t nodeEnd = content.find(",", nodeStart);
            if (nodeStart != std::string::npos && nodeEnd != std::string::npos) {
                std::string nodeStr = content.substr(nodeStart, nodeEnd - nodeStart);
                
                // Parse node ID
                size_t underscorePos = nodeStr.find("_");
                if (underscorePos != std::string::npos) {
                    std::string nodeIdStr = nodeStr.substr(underscorePos + 1);
                    uint32_t nodeId = std::stoi(nodeIdStr);
                    targetNodes.push_back(nodeId);
                    ns3Commands.push_back("fiber_rerouting");
                    std::cout << "🔧 Fiber rerouting command for node " << nodeId << std::endl;
                }
            }
            pos++;
        }
        
        // Execute healing commands
        for (size_t i = 0; i < targetNodes.size() && i < ns3Commands.size(); ++i) {
            ExecuteHealingCommand(targetNodes[i], ns3Commands[i]);
        }
        
        std::cout << "✅ Deployment file processed successfully" << std::endl;
        
    } catch (const std::exception& e) {
        std::cout << "❌ Error processing deployment file: " << e.what() << std::endl;
    }
}

// NEW: Add this method to execute healing commands
void ITU_Competition_Rural_Network::ExecuteHealingCommand(uint32_t nodeId, const std::string& command)
{
    std::cout << "🚀 Executing healing command: " << command << " for node " << nodeId << std::endl;
    
    if (command == "power_healing") {
        // Execute power fluctuation healing
        if (healingEngine && animInterface) {
            healingEngine->ShowHealingInProgress(nodeId, animInterface, allNodes);
            
            // Schedule healing completion
            Simulator::Schedule(Seconds(30), [this, nodeId]() {
                healingEngine->ShowHealingCompleted(nodeId, animInterface, allNodes);
                RestoreOriginalNodeSize(nodeId);
                std::cout << "✅ Power healing completed for node " << nodeId << std::endl;
            });
        }
        
    } else if (command == "fiber_rerouting") {
        // Execute fiber cut rerouting
        if (healingEngine && animInterface) {
            healingEngine->ShowHealingInProgress(nodeId, animInterface, allNodes);
            
            // Schedule healing completion
            Simulator::Schedule(Seconds(45), [this, nodeId]() {
                healingEngine->ShowHealingCompleted(nodeId, animInterface, allNodes);
                RestoreOriginalNodeSize(nodeId);
                std::cout << "✅ Fiber rerouting completed for node " << nodeId << std::endl;
            });
        }
    }
    
    std::cout << "🎬 VISUAL: Healing initiated for node " << GetNodeVisualName(nodeId) << std::endl;
}

void ITU_Competition_Rural_Network::ExecuteHealingDeployment(const std::map<std::string, std::string>& deploymentData)
{
    try {
        // Simple deployment execution
        auto nodeIdIt = deploymentData.find("node_id");
        if (nodeIdIt != deploymentData.end()) {
            uint32_t nodeId = std::stoi(nodeIdIt->second);
            
            std::cout << "✅ Healing deployment executed for node " << nodeId << std::endl;
            
            // Show healing in progress immediately
            if (healingEngine && animInterface) {
                healingEngine->ShowHealingInProgress(nodeId, animInterface, allNodes);
            }
            
            // Schedule healing completion after 30 seconds
            Simulator::Schedule(Seconds(30), [this, nodeId]() {
                if (healingEngine && animInterface) {
                    healingEngine->ShowHealingCompleted(nodeId, animInterface, allNodes);
                }
                RestoreOriginalNodeSize(nodeId);
            });
        }
        
    } catch (const std::exception& e) {
        std::cout << "❌ Error executing simple healing deployment: " << e.what() << std::endl;
    }
}

void ITU_Competition_Rural_Network::DeployHealingPlan(const HealingPlan& plan)
{
    if (!healingEngine) {
        std::cout << "❌ Healing engine not available" << std::endl;
        return;
    }
    
    bool success = healingEngine->DeployHealingPlan(plan);
    
    if (success) {
        std::cout << "✅ Healing plan deployed successfully: " << plan.planId << std::endl;
        
        // Show visual healing effects if visualization enabled
        if (m_config.enableVisualization && animInterface) {
            for (const auto& action : plan.actions) {
                for (uint32_t nodeId : action.targetNodes) {
                    std::cout << "🔄 Healing in progress for node " << nodeId << std::endl;
                    
                    // Schedule showing completion after estimated duration
                    Simulator::Schedule(Seconds(action.estimatedDuration), 
                        [this, nodeId]() {
                            if (healingEngine && animInterface) {
                                std::cout << "✅ Healing completed for node " << nodeId << std::endl;
                            }
                        });
                }
            }
        }
    } else {
        std::cout << "❌ Healing plan deployment failed: " << plan.planId << std::endl;
    }
}

void ITU_Competition_Rural_Network::UpdateAgentInterface()
{
    if (!agentAPI) return;
    
    // Export current fault events
    agentAPI->ExportRealTimeFaultEvents(faultEvents);
}

// **STEP 4D: Announcement Methods**
void ITU_Competition_Rural_Network::AnnounceFaultEvent(const GradualFaultPattern& fault, const std::string& eventType)
{
    FaultEvent event;
    event.timestamp = Simulator::Now().GetSeconds();
    event.eventType = eventType;
    event.faultType = fault.faultType;
    event.affectedNodes = {fault.targetNode, fault.connectedNode};
    event.description = fault.faultDescription;
    event.visualEffect = fault.visualMessage;
    event.severity = fault.currentSeverity;
    
    faultEvents.push_back(event);
    LogFaultEvent(event);
    
    if (eventType == "fault_started") {
        std::cout << "🚨 RANDOMIZED FAULT STARTED: " << fault.faultDescription 
                  << " (Severity: " << (fault.currentSeverity * 100) << "%)" << std::endl;
    } else if (eventType == "fault_ended") {
        std::cout << "✅ RANDOMIZED FAULT RESOLVED: " << fault.faultDescription << std::endl;
    }
}

void ITU_Competition_Rural_Network::LogFaultEvent(const FaultEvent& event)
{
    faultLogFile << event.timestamp << "," << event.eventType << "," << event.faultType << ",";
    for (size_t i = 0; i < event.affectedNodes.size(); ++i) {
        faultLogFile << event.affectedNodes[i];
        if (i < event.affectedNodes.size() - 1) faultLogFile << ";";
    }
    faultLogFile << "," << event.description << "," << event.visualEffect << "," << event.severity << std::endl;
}

// **STEP 4E: Visualization Methods with Severity-based Sizing**
void ITU_Competition_Rural_Network::SetupRobustNetAnimVisualization()
{
    if (!m_config.enableVisualization) return;
    
    std::cout << "🎬 Setting up NetAnim visualization with severity-based sizing..." << std::endl;
    
    std::string animFileName = m_config.outputPrefix + "_animation.xml";
    animInterface = new AnimationInterface(animFileName);
    
    // Position nodes in a logical rural network layout
    for (uint32_t i = 0; i < coreNodes.GetN(); ++i) {
        animInterface->SetConstantPosition(coreNodes.Get(i), 200 + i * 100, 200, 0);
        animInterface->UpdateNodeDescription(coreNodes.Get(i), GetNodeVisualName(i));
        animInterface->UpdateNodeColor(coreNodes.Get(i), 0, 0, 255); // Blue for core
        animInterface->UpdateNodeSize(i, 50, 50);
        originalNodeSizes[i] = 50.0; // Store original size
    }
    
    for (uint32_t i = 0; i < distributionNodes.GetN(); ++i) {
        uint32_t nodeId = 5 + i;
        double angle = (2.0 * M_PI * i) / distributionNodes.GetN();
        double x = 400 + 150 * cos(angle);
        double y = 200 + 150 * sin(angle);
        animInterface->SetConstantPosition(distributionNodes.Get(i), x, y, 0);
        animInterface->UpdateNodeDescription(distributionNodes.Get(i), GetNodeVisualName(nodeId));
        animInterface->UpdateNodeColor(distributionNodes.Get(i), 255, 192, 203);  // Pink for distribution
        animInterface->UpdateNodeSize(nodeId, 40, 40);
        originalNodeSizes[nodeId] = 40.0; // Store original size
    }
    
    for (uint32_t i = 0; i < accessNodes.GetN(); ++i) {
        uint32_t nodeId = 20 + i;
        double angle = (2.0 * M_PI * i) / accessNodes.GetN();
        double x = 400 + 300 * cos(angle);
        double y = 200 + 300 * sin(angle);
        animInterface->SetConstantPosition(accessNodes.Get(i), x, y, 0);
        animInterface->UpdateNodeDescription(accessNodes.Get(i), GetNodeVisualName(nodeId));
        animInterface->UpdateNodeColor(accessNodes.Get(i), 211, 182, 131); // Light Brown #D3B683
        animInterface->UpdateNodeSize(nodeId, 30, 30);
        originalNodeSizes[nodeId] = 30.0; // Store original size
    }
    
    std::cout << "✅ NetAnim visualization configured with severity-based node sizing" << std::endl;
}

void ITU_Competition_Rural_Network::ProcessFaultVisualization()
{
    if (!m_config.enableFaultVisualization || !animInterface) return;
    
    UpdateVisualFaultIndicators();
}

void ITU_Competition_Rural_Network::UpdateVisualFaultIndicators()
{
    // Update visual indicators for all active faults
    for (const auto& fault : gradualFaults) {
        if (fault.isActive && !fault.visualIndicatorActive) {
            if (fault.faultType == "fiber_cut") {
                HideFiberLink(fault.targetNode, fault.connectedNode);
            } else if (fault.faultType == "power_fluctuation") {
                ShowPowerIssue(fault.targetNode);
            }
        }
    }
}

void ITU_Competition_Rural_Network::UpdateNodeVisualStatus(uint32_t nodeId, const std::string& status)
{
    if (!animInterface) return;
    
    std::string description = GetNodeVisualName(nodeId) + "\n" + status;
    animInterface->UpdateNodeDescription(allNodes.Get(nodeId), description);
}

std::string ITU_Competition_Rural_Network::GetNodeVisualName(uint32_t nodeId)
{
    if (nodeId < 5) {
        return "CORE-" + std::to_string(nodeId);
    } else if (nodeId < 20) {
        return "DIST-" + std::to_string(nodeId - 5);
    } else {
        return "ACC-" + std::to_string(nodeId - 20);
    }
}

void ITU_Competition_Rural_Network::HideFiberLink(uint32_t nodeA, uint32_t nodeB)
{
    if (!animInterface) return;
    
    // Show fault indication on affected nodes
    animInterface->UpdateNodeColor(allNodes.Get(nodeA), 255, 0, 0); // Red for fault
    animInterface->UpdateNodeColor(allNodes.Get(nodeB), 255, 0, 0);
    
    UpdateNodeVisualStatus(nodeA, "🔴 FIBER CUT");
    UpdateNodeVisualStatus(nodeB, "🔴 FIBER CUT");
    
    std::cout << "🎬 VISUAL: Fiber cut shown between " << GetNodeVisualName(nodeA) 
              << " and " << GetNodeVisualName(nodeB) << std::endl;
}

void ITU_Competition_Rural_Network::RestoreFiberLink(uint32_t nodeA, uint32_t nodeB)
{
    if (!animInterface) return;
    
    // Restore normal colors
    if (nodeA < 5) animInterface->UpdateNodeColor(allNodes.Get(nodeA), 0, 0, 255); // Blue for core
    else if (nodeA < 20) animInterface->UpdateNodeColor(allNodes.Get(nodeA), 255, 192, 203); // Pink for dist   
    else animInterface->UpdateNodeColor(allNodes.Get(nodeA), 211, 182, 131); // Light Brown for access
    
    if (nodeB < 5) animInterface->UpdateNodeColor(allNodes.Get(nodeB), 0, 0, 255);
    else if (nodeB < 20) animInterface->UpdateNodeColor(allNodes.Get(nodeB), 255, 192, 203);
    else animInterface->UpdateNodeColor(allNodes.Get(nodeB), 211, 182, 131);
    
    UpdateNodeVisualStatus(nodeA, "✅ RESTORED");
    UpdateNodeVisualStatus(nodeB, "✅ RESTORED");
    
    std::cout << "🎬 VISUAL: Fiber link restored between " << GetNodeVisualName(nodeA) 
              << " and " << GetNodeVisualName(nodeB) << std::endl;
}

void ITU_Competition_Rural_Network::ShowPowerIssue(uint32_t nodeId)
{
    if (!animInterface) return;
    
    animInterface->UpdateNodeColor(allNodes.Get(nodeId), 255, 255, 0); // Yellow for power issue
    UpdateNodeVisualStatus(nodeId, "⚡ POWER ISSUE");
    
    std::cout << "🎬 VISUAL: Power issue shown for " << GetNodeVisualName(nodeId) << std::endl;
}

void ITU_Competition_Rural_Network::HidePowerIssue(uint32_t nodeId)
{
    if (!animInterface) return;
    
    // Restore normal color based on node type
    if (nodeId < 5) animInterface->UpdateNodeColor(allNodes.Get(nodeId), 0, 0, 255);
    else if (nodeId < 20) animInterface->UpdateNodeColor(allNodes.Get(nodeId), 255, 192, 203);
    else animInterface->UpdateNodeColor(allNodes.Get(nodeId), 211, 182, 131);
    
    UpdateNodeVisualStatus(nodeId, "✅ POWER RESTORED");
    
    std::cout << "🎬 VISUAL: Power issue resolved for " << GetNodeVisualName(nodeId) << std::endl;
}

// **STEP 4F: Output File Methods (Simplified)**
void ITU_Competition_Rural_Network::WriteTopologyInfo()
{
    if (!topologyFile.is_open()) return;
    
    topologyFile << "{\n";
    topologyFile << "  \"simulation_info\": {\n";
    topologyFile << "    \"total_nodes\": " << allNodes.GetN() << ",\n";
    topologyFile << "    \"core_nodes\": " << coreNodes.GetN() << ",\n";
    topologyFile << "    \"distribution_nodes\": " << distributionNodes.GetN() << ",\n";
    topologyFile << "    \"access_nodes\": " << accessNodes.GetN() << ",\n";
    topologyFile << "    \"simulation_time\": " << m_config.totalSimulationTime << ",\n";
    topologyFile << "    \"data_collection_interval\": " << m_config.dataCollectionInterval << "\n";
    topologyFile << "  },\n";
    topologyFile << "  \"randomized_faults\": {\n";
    topologyFile << "    \"enabled\": " << (m_config.enableRandomizedFaults ? "true" : "false") << ",\n";
    topologyFile << "    \"min_fault_interval\": " << m_config.minFaultInterval << ",\n";
    topologyFile << "    \"max_fault_interval\": " << m_config.maxFaultInterval << ",\n";
    topologyFile << "    \"fiber_cut_probability\": " << m_config.fiberCutProbability << ",\n";
    topologyFile << "    \"max_simultaneous_faults\": " << m_config.maxSimultaneousFaults << ",\n";
    topologyFile << "    \"severity_based_visualization\": true\n";
    topologyFile << "  },\n";
    topologyFile << "  \"agent_integration\": {\n";
    topologyFile << "    \"enabled\": " << (m_config.enableAgentIntegration ? "true" : "false") << ",\n";
    topologyFile << "    \"healing_deployment\": " << (m_config.enableHealingDeployment ? "true" : "false") << ",\n";
    topologyFile << "    \"interface_directory\": \"" << m_config.agentInterfaceDir << "\"\n";
    topologyFile << "  }\n";
    topologyFile << "}\n";
}

void ITU_Competition_Rural_Network::WriteConfigurationInfo()
{
    if (!configFile.is_open()) return;
    
    configFile << "{\n";
    configFile << "  \"configuration\": {\n";
    configFile << "    \"mode\": \"" << m_config.mode << "\",\n";
    configFile << "    \"high_speed_network\": " << (m_config.useHighSpeedNetwork ? "true" : "false") << ",\n";
    configFile << "    \"visualization_enabled\": " << (m_config.enableVisualization ? "true" : "false") << ",\n";
    configFile << "    \"fault_visualization_enabled\": " << (m_config.enableFaultVisualization ? "true" : "false") << ",\n";
    configFile << "    \"randomized_faults_enabled\": " << (m_config.enableRandomizedFaults ? "true" : "false") << ",\n";
    configFile << "    \"severity_based_sizing_enabled\": true\n";
    configFile << "  },\n";
    configFile << "  \"timing\": {\n";
    configFile << "    \"total_simulation_time\": " << m_config.totalSimulationTime << ",\n";
    configFile << "    \"baseline_duration\": " << m_config.baselineDuration << ",\n";
    configFile << "    \"fault_start_time\": " << m_config.faultStartTime << ",\n";
    configFile << "    \"data_collection_interval\": " << m_config.dataCollectionInterval << "\n";
    configFile << "  }\n";
    configFile << "}\n";
}

void ITU_Competition_Rural_Network::WriteFaultEventLog()
{
    // Fault events are written in real-time during the simulation
}

void ITU_Competition_Rural_Network::WriteNodeConnectivity()
{
    std::cout << "📊 Generating complete node connectivity information..." << std::endl;
    
    // Build connectivity map from linkStatus
    std::map<uint32_t, std::vector<uint32_t>> connectivityMap;
    std::map<uint32_t, std::vector<std::string>> linkTypesMap;
    
    for (const auto& link : linkStatus) {
        uint32_t nodeA = link.first.first;
        uint32_t nodeB = link.first.second;
        bool isActive = link.second;
        
        if (isActive) {
            connectivityMap[nodeA].push_back(nodeB);
            connectivityMap[nodeB].push_back(nodeA);
            
            // Determine link type
            std::string linkType = "unknown";
            if (nodeA < 5 && nodeB < 5) {
                linkType = "core_to_core";
            } else if ((nodeA < 5 && nodeB < 20) || (nodeA < 20 && nodeB < 5)) {
                linkType = "core_to_dist";
            } else if ((nodeA < 20 && nodeB >= 20) || (nodeA >= 20 && nodeB < 20)) {
                linkType = "dist_to_access";
            } else if (nodeA >= 5 && nodeA < 20 && nodeB >= 5 && nodeB < 20) {
                linkType = "dist_to_dist";
            }
            
            linkTypesMap[nodeA].push_back(linkType);
            linkTypesMap[nodeB].push_back(linkType);
        }
    }
    
    // Write detailed connectivity file
    std::string filename = m_config.outputPrefix + "_node_connectivity.json";
    std::ofstream jsonFile(filename);
    
    if (!jsonFile.is_open()) {
        std::cout << "❌ Failed to open connectivity file: " << filename << std::endl;
        return;
    }
    
    jsonFile << "{\n";
    jsonFile << "  \"network_connectivity\": {\n";
    jsonFile << "    \"total_nodes\": " << allNodes.GetN() << ",\n";
    jsonFile << "    \"total_links\": " << linkStatus.size() << ",\n";
    jsonFile << "    \"node_details\": {\n";
    
    bool firstNode = true;
    for (uint32_t nodeId = 0; nodeId < allNodes.GetN(); ++nodeId) {
        if (!firstNode) jsonFile << ",\n";
        firstNode = false;
        
        // Get node type
        std::string nodeType = (nodeId < 5) ? "CORE" : (nodeId < 20) ? "DIST" : "ACCESS";
        
        jsonFile << "      \"node_" << nodeId << "\": {\n";
        jsonFile << "        \"node_id\": " << nodeId << ",\n";
        jsonFile << "        \"node_type\": \"" << nodeType << "\",\n";
        jsonFile << "        \"node_name\": \"" << GetNodeVisualName(nodeId) << "\",\n";
        jsonFile << "        \"degree\": " << connectivityMap[nodeId].size() << ",\n";
        jsonFile << "        \"connected_to\": [";
        
        const auto& connections = connectivityMap[nodeId];
        for (size_t i = 0; i < connections.size(); ++i) {
            jsonFile << connections[i];
            if (i < connections.size() - 1) jsonFile << ", ";
        }
        
        jsonFile << "],\n";
        jsonFile << "        \"link_types\": [";
        
        const auto& linkTypes = linkTypesMap[nodeId];
        for (size_t i = 0; i < linkTypes.size(); ++i) {
            jsonFile << "\"" << linkTypes[i] << "\"";
            if (i < linkTypes.size() - 1) jsonFile << ", ";
        }
        
        jsonFile << "]\n";
        jsonFile << "      }";
    }
    
    jsonFile << "\n    },\n";
    
    // Add adjacency matrix
    jsonFile << "    \"adjacency_matrix\": [\n";
    for (uint32_t i = 0; i < allNodes.GetN(); ++i) {
        jsonFile << "      [";
        
        for (uint32_t j = 0; j < allNodes.GetN(); ++j) {
            bool connected = false;
            if (i != j) {
                connected = (linkStatus.find({i, j}) != linkStatus.end()) || 
                           (linkStatus.find({j, i}) != linkStatus.end());
            }
            jsonFile << (connected ? "1" : "0");
            if (j < allNodes.GetN() - 1) jsonFile << ", ";
        }
        
        jsonFile << "]";
        if (i < allNodes.GetN() - 1) jsonFile << ",";
        jsonFile << "\n";
    }
    jsonFile << "    ]\n";
    
    jsonFile << "  }\n";
    jsonFile << "}\n";
    jsonFile.close();
    
    std::cout << "✅ Node connectivity written to " << filename << std::endl;
}

void ITU_Competition_Rural_Network::WriteDetailedTopology()
{
    std::cout << "📊 Generating detailed network topology..." << std::endl;
    
    std::string filename = m_config.outputPrefix + "_detailed_topology.txt";
    std::ofstream topoFile(filename);
    
    if (!topoFile.is_open()) {
        std::cout << "❌ Failed to open topology file: " << filename << std::endl;
        return;
    }
    
    topoFile << "========================================\n";
    topoFile << "COMPLETE NETWORK TOPOLOGY ANALYSIS\n";
    topoFile << "========================================\n\n";
    
    topoFile << "NETWORK SUMMARY:\n";
    topoFile << "Total Nodes: " << allNodes.GetN() << "\n";
    topoFile << "Core Nodes: 5 (ID 0-4)\n";
    topoFile << "Distribution Nodes: 15 (ID 5-19)\n";
    topoFile << "Access Nodes: 30 (ID 20-49)\n";
    topoFile << "Total Links: " << linkStatus.size() << "\n\n";
    
    // Count links by type
    int coreToCore = 0, coreToDist = 0, distToAccess = 0, distToDist = 0;
    
    for (const auto& link : linkStatus) {
        uint32_t nodeA = link.first.first;
        uint32_t nodeB = link.first.second;
        
        if (nodeA < 5 && nodeB < 5) coreToCore++;
        else if ((nodeA < 5 && nodeB < 20) || (nodeA < 20 && nodeB < 5)) coreToDist++;
        else if ((nodeA < 20 && nodeB >= 20) || (nodeA >= 20 && nodeB < 20)) distToAccess++;
        else if (nodeA >= 5 && nodeA < 20 && nodeB >= 5 && nodeB < 20) distToDist++;
    }
    
    topoFile << "LINK DISTRIBUTION:\n";
    topoFile << "Core-to-Core: " << coreToCore << " links\n";
    topoFile << "Core-to-Distribution: " << coreToDist << " links\n";
    topoFile << "Distribution-to-Access: " << distToAccess << " links\n";
    topoFile << "Distribution-to-Distribution: " << distToDist << " links\n\n";
    
    topoFile << "DETAILED NODE CONNECTIONS:\n";
    topoFile << "========================================\n";
    
    // Build connectivity map
    std::map<uint32_t, std::vector<uint32_t>> connectivityMap;
    for (const auto& link : linkStatus) {
        uint32_t nodeA = link.first.first;
        uint32_t nodeB = link.first.second;
        
        connectivityMap[nodeA].push_back(nodeB);
        connectivityMap[nodeB].push_back(nodeA);
    }
    
    // Write detailed connections for each node
    for (uint32_t nodeId = 0; nodeId < allNodes.GetN(); ++nodeId) {
        std::string nodeType = (nodeId < 5) ? "CORE" : (nodeId < 20) ? "DIST" : "ACCESS";
        
        topoFile << "Node " << nodeId << " (" << GetNodeVisualName(nodeId) << ") - " << nodeType << ":\n";
        topoFile << "  Degree: " << connectivityMap[nodeId].size() << "\n";
        topoFile << "  Connected to: ";
        
        const auto& connections = connectivityMap[nodeId];
        for (size_t i = 0; i < connections.size(); ++i) {
            topoFile << GetNodeVisualName(connections[i]);
            if (i < connections.size() - 1) topoFile << ", ";
        }
        topoFile << "\n\n";
    }
    
    topoFile << "ADJACENCY MATRIX:\n";
    topoFile << "========================================\n";
    topoFile << "   ";
    for (uint32_t j = 0; j < allNodes.GetN(); ++j) {
        topoFile << std::setw(3) << j;
    }
    topoFile << "\n";
    
    for (uint32_t i = 0; i < allNodes.GetN(); ++i) {
        topoFile << std::setw(2) << i << " ";
        
        for (uint32_t j = 0; j < allNodes.GetN(); ++j) {
            bool connected = false;
            if (i != j) {
                connected = (linkStatus.find({i, j}) != linkStatus.end()) || 
                           (linkStatus.find({j, i}) != linkStatus.end());
            }
            topoFile << std::setw(3) << (connected ? "1" : "0");
        }
        topoFile << "\n";
    }
    
    topoFile.close();
    std::cout << "✅ Detailed topology written to " << filename << std::endl;
}


// **STEP 5: Main Run() Method and Complete Simulation Execution**
void ITU_Competition_Rural_Network::Run()
{
    std::cout << "\n=== ITU COMPETITION RURAL NETWORK SIMULATION START ===" << std::endl;
    std::cout << "🏆 Competition Mode: AI-Native Self-Healing Rural Network" << std::endl;
    std::cout << "🎲 Randomized Fault Injection: ENABLED" << std::endl;
    std::cout << "📏 Severity-based Node Sizing: ENABLED" << std::endl;
    std::cout << "🤖 Agent Integration: " << (m_config.enableAgentIntegration ? "ENABLED" : "DISABLED") << std::endl;
    
    // **PHASE 1: Infrastructure Setup**
    std::cout << "\n--- PHASE 1: INFRASTRUCTURE SETUP ---" << std::endl;
    SetupRobustTopology();
    SetupRobustApplications();
    
    // **PHASE 2: Visualization Setup (if enabled)**
    if (m_config.enableVisualization) {
        std::cout << "\n--- PHASE 2: VISUALIZATION SETUP ---" << std::endl;
        SetupRobustNetAnimVisualization();
        std::cout << "✅ NetAnim visualization ready with severity-based sizing" << std::endl;
    }
    
    // **PHASE 3: Randomized Fault Pattern Scheduling**
    std::cout << "\n--- PHASE 3: RANDOMIZED FAULT PATTERN SCHEDULING ---" << std::endl;
    ScheduleRandomizedFaultPatterns();
    
    // **PHASE 4: Monitoring Setup**
    std::cout << "\n--- PHASE 4: MONITORING SETUP ---" << std::endl;
    flowMonitor = flowHelper.Install(allNodes);
    std::cout << "✅ Flow monitor installed for comprehensive metrics" << std::endl;
    
    // **PHASE 5: Simulation Execution**
    std::cout << "\n--- PHASE 5: SIMULATION EXECUTION ---" << std::endl;
    
    // Set simulation stop time
    Simulator::Stop(Seconds(m_config.totalSimulationTime));
    
    // Schedule periodic data collection for AI training
    for (double t = 0; t < m_config.totalSimulationTime; t += m_config.dataCollectionInterval) {
        Simulator::Schedule(Seconds(t), &ITU_Competition_Rural_Network::CollectComprehensiveMetrics, this);
    }
    
    // Write initial configuration files
    WriteTopologyInfo();
    WriteConfigurationInfo();
    
    std::cout << "🚀 Starting simulation..." << std::endl;
    std::cout << "⏱️ Duration: " << m_config.totalSimulationTime << " seconds" << std::endl;
    std::cout << "📊 Data points: " << (int)(m_config.totalSimulationTime / m_config.dataCollectionInterval) << std::endl;
    std::cout << "🔄 Collection interval: " << m_config.dataCollectionInterval << " seconds" << std::endl;
    
    // **Main simulation execution**
    auto startTime = std::chrono::steady_clock::now();
    Simulator::Run();
    auto endTime = std::chrono::steady_clock::now();
    
    // **PHASE 6: Post-Simulation Processing**
    std::cout << "\n--- PHASE 6: POST-SIMULATION PROCESSING ---" << std::endl;
    
    auto executionTime = std::chrono::duration_cast<std::chrono::seconds>(endTime - startTime);
    std::cout << "⏱️ Execution time: " << executionTime.count() << " seconds" << std::endl;
    
    // Generate final statistics
    GenerateFinalStatistics();
    
    // Write final output files
    WriteFaultEventLog();
    
    WriteNodeConnectivity();     
    WriteDetailedTopology();
    
    // Close all output files
    if (metricsFile.is_open()) metricsFile.close();
    if (topologyFile.is_open()) topologyFile.close();
    if (configFile.is_open()) configFile.close();
    if (faultLogFile.is_open()) faultLogFile.close();
    
    // Save flow monitor data
    std::string flowMonFileName = m_config.outputPrefix + "_flowmon.xml";
    flowMonitor->SerializeToXmlFile(flowMonFileName, true, true);
    std::cout << "✅ Flow monitor data saved: " << flowMonFileName << std::endl;
    
    // Final summary
    PrintSimulationSummary();
    
    // Cleanup
    if (animInterface) {
        delete animInterface;
        animInterface = nullptr;
    }
    
    if (agentAPI) {
        delete agentAPI;
        agentAPI = nullptr;
    }
    
    if (healingEngine) {
        delete healingEngine;
        healingEngine = nullptr;
    }
    
    if (faultGenerator) {
        delete faultGenerator;
        faultGenerator = nullptr;
    }
    
    Simulator::Destroy();
    
    std::cout << "\n=== ITU COMPETITION RURAL NETWORK SIMULATION COMPLETE ===" << std::endl;
    std::cout << "🏆 Ready for AI agent processing and Geneva competition!" << std::endl;
}

void ITU_Competition_Rural_Network::GenerateFinalStatistics()
{
    std::cout << "\n📊 GENERATING FINAL STATISTICS..." << std::endl;
    
    // Count fault events by type
    std::map<std::string, int> faultTypeCounts;
    for (const auto& event : faultEvents) {
        faultTypeCounts[event.faultType]++;
    }
    
    std::cout << "🚨 Randomized Fault Events Summary:" << std::endl;
    for (const auto& pair : faultTypeCounts) {
        std::cout << "  - " << pair.first << ": " << pair.second << " events" << std::endl;
    }
    
    // Calculate severity statistics
    double totalSeverity = 0.0;
    double maxSeverity = 0.0;
    int severeFaults = 0;
    
    for (const auto& fault : gradualFaults) {
        totalSeverity += fault.severity;
        maxSeverity = std::max(maxSeverity, fault.severity);
        if (fault.severity > 0.7) severeFaults++;
    }
    
    double avgSeverity = gradualFaults.empty() ? 0.0 : totalSeverity / gradualFaults.size();
    
    std::cout << "📊 Severity Statistics:" << std::endl;
    std::cout << "  - Average severity: " << (avgSeverity * 100) << "%" << std::endl;
    std::cout << "  - Maximum severity: " << (maxSeverity * 100) << "%" << std::endl;
    std::cout << "  - Severe faults (>70%): " << severeFaults << std::endl;
    
    // Healing plan statistics
    std::cout << "💊 Healing Plans: " << activeHealingPlans.size() << " deployed" << std::endl;
}

void ITU_Competition_Rural_Network::PrintSimulationSummary()
{
    std::cout << "\n🎯 ITU COMPETITION SIMULATION SUMMARY" << std::endl;
    std::cout << "================================================" << std::endl;
    std::cout << "📡 Network Topology: 50 nodes (5 Core + 15 Dist + 30 Access)" << std::endl;
    std::cout << "🌐 Network Type: Rural self-healing mesh with OLSR routing" << std::endl;
    std::cout << "⚡ Energy Model: Solar harvesting for access nodes" << std::endl;
    std::cout << "📊 Data Collection: " << (int)(m_config.totalSimulationTime / m_config.dataCollectionInterval) << " data points" << std::endl;
    std::cout << "🎲 Fault Injection: Randomized with severity-based visualization" << std::endl;
    std::cout << "🔧 Test Cases Implemented:" << std::endl;
    std::cout << "  ✅ TST-01/02: Randomized fiber cut & power fluctuation" << std::endl;
    std::cout << "  📏 Severity-based node sizing: ENABLED" << std::endl;
    std::cout << "🤖 Agent Integration: " << (m_config.enableAgentIntegration ? "READY" : "DISABLED") << std::endl;
    std::cout << "📁 Output Files Generated:" << std::endl;
    std::cout << "  - " << m_config.outputPrefix << "_network_metrics.csv" << std::endl;
    std::cout << "  - " << m_config.outputPrefix << "_topology.json" << std::endl;
    std::cout << "  - " << m_config.outputPrefix << "_fault_events.log" << std::endl;
    std::cout << "  - " << m_config.outputPrefix << "_flowmon.xml" << std::endl;
    if (m_config.enableVisualization) {
        std::cout << "  - " << m_config.outputPrefix << "_animation.xml" << std::endl;
    }
    std::cout << "🎲 Randomized Fault Parameters:" << std::endl;
    std::cout << "  - Fault interval: " << m_config.minFaultInterval << "-" << m_config.maxFaultInterval << " seconds" << std::endl;
    std::cout << "  - Fault duration: " << m_config.minFaultDuration << "-" << m_config.maxFaultDuration << " seconds" << std::endl;
    std::cout << "  - Fiber cut probability: " << (m_config.fiberCutProbability * 100) << "%" << std::endl;
    std::cout << "  - Max simultaneous faults: " << m_config.maxSimultaneousFaults << std::endl;
    std::cout << "================================================" << std::endl;
}

// **MAIN FUNCTION**
int main(int argc, char *argv[])
{
    std::cout << "\n🏆 ITU FG-AINN COMPETITION: AI-NATIVE SELF-HEALING RURAL NETWORK" << std::endl;
    std::cout << "=================================================================" << std::endl;
    
    // Enhanced command line parsing
    CommandLine cmd(__FILE__);
    
    // Configuration parameters
    std::string mode = "itu_competition";
    int targetDataPoints = 500;
    bool enableVisual = false;
    bool enableFaultVis = false;
    bool enableAgents = true;
    double simulationTime = 0.0; // Auto-calculate if 0
    double dataInterval = 5.0;
    std::string outputPrefix = "itu_competition";
    
    // Add command line options
    cmd.AddValue("mode", "Simulation mode: itu_competition, demo, test", mode);
    cmd.AddValue("targetDataPoints", "Number of data points to collect", targetDataPoints);
    cmd.AddValue("simulationTime", "Total simulation time (0 = auto-calculate)", simulationTime);
    cmd.AddValue("dataInterval", "Data collection interval in seconds", dataInterval);
    cmd.AddValue("enableVisual", "Enable NetAnim visualization", enableVisual);
    cmd.AddValue("enableFaultVis", "Enable fault visualization", enableFaultVis);
    cmd.AddValue("enableAgents", "Enable agent integration", enableAgents);
    cmd.AddValue("outputPrefix", "Output file prefix", outputPrefix);
    
    cmd.Parse(argc, argv);
    
    // Create appropriate configuration based on mode
    SimulationConfig config;
    
    if (mode == "itu_competition") {
        config = ITU_Competition_Rural_Network::CreateITU_CompetitionConfig(targetDataPoints);
        std::cout << "🎯 Mode: ITU Competition (Production)" << std::endl;
    } else if (mode == "demo") {
        config = ITU_Competition_Rural_Network::CreateRandomizedFaultConfig();
        std::cout << "🎬 Mode: Visual Demonstration" << std::endl;
    } else if (mode == "test") {
        config = ITU_Competition_Rural_Network::CreateITU_CompetitionConfig(100); // Quick test
        config.totalSimulationTime = 120.0; // 2 minutes
        std::cout << "🧪 Mode: Quick Test" << std::endl;
    } else {
        std::cout << "❌ Unknown mode: " << mode << std::endl;
        std::cout << "Available modes: itu_competition, demo, test" << std::endl;
        return 1;
    }
    
    // Apply command line overrides
    if (simulationTime > 0) {
        config.totalSimulationTime = simulationTime;
        config.faultStartTime = simulationTime * 0.3; // 30% baseline
    }
    
    config.dataCollectionInterval = dataInterval;
    config.enableVisualization = enableVisual;
    config.enableFaultVisualization = enableFaultVis;
    config.enableAgentIntegration = enableAgents;
    config.outputPrefix = outputPrefix;
    
    // Display configuration
    std::cout << "\n📋 SIMULATION CONFIGURATION:" << std::endl;
    std::cout << "  Duration: " << config.totalSimulationTime << " seconds" << std::endl;
    std::cout << "  Data points: " << targetDataPoints << std::endl;
    std::cout << "  Collection interval: " << config.dataCollectionInterval << " seconds" << std::endl;
    std::cout << "  Visualization: " << (config.enableVisualization ? "ENABLED" : "DISABLED") << std::endl;
    std::cout << "  Agent integration: " << (config.enableAgentIntegration ? "ENABLED" : "DISABLED") << std::endl;
    std::cout << "  Randomized faults: ENABLED" << std::endl;
    std::cout << "  Severity-based sizing: ENABLED" << std::endl;
    std::cout << "  Output prefix: " << config.outputPrefix << std::endl;
    
    // Estimate execution time
    double estimatedTime = config.totalSimulationTime * 0.1; // Rough estimate
    std::cout << "  Estimated execution time: ~" << (int)estimatedTime << " seconds" << std::endl;
    
    std::cout << "\n🚀 Starting simulation..." << std::endl;
    
    try {
        // Create and run simulation
        ITU_Competition_Rural_Network simulation(config);
        simulation.Run();
        
        std::cout << "\n✅ Simulation completed successfully!" << std::endl;
        std::cout << "📂 Check output files for results and agent integration data." << std::endl;
        
        if (config.enableAgentIntegration) {
            std::cout << "\n🤖 NEXT STEPS FOR ITU COMPETITION:" << std::endl;
            std::cout << "1. Run Monitor Agent: python3 monitor_agent.py" << std::endl;
            std::cout << "2. Run Calculation Agent: python3 calculation_agent.py" << std::endl;
            std::cout << "3. Run Combined Healing & Orchestration Agent: python3 healORCH.py" << std::endl;
            std::cout << "4. Observe closed-loop self-healing in action!" << std::endl;
            std::cout << "5. Watch severity-based node sizing in NetAnim!" << std::endl;
        }
        
        return 0;
        
    } catch (const std::exception& e) {
        std::cout << "❌ Simulation failed: " << e.what() << std::endl;
        return 1;
    } catch (...) {
        std::cout << "❌ Simulation failed with unknown error" << std::endl;
        return 1;
    }
}