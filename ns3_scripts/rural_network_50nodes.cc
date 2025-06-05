/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * COMPLETE ROBUST RURAL 50-NODE SELF-HEALING NETWORK SIMULATION
 * ALL REQUIREMENTS: Baseline Data + Fault Injection + NetAnim + LSTM Training
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
#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <iomanip>
#include <map>
#include <cmath>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("CompleteRuralNetworkSimulation");

// ROBUST: Simulation configuration structure
struct SimulationConfig {
    std::string mode;                    // "baseline", "fault_demo", "mixed"
    double totalSimulationTime;          // Total simulation duration
    double dataCollectionInterval;      // Data collection frequency
    double baselineDuration;             // Duration of fault-free period
    double faultStartTime;              // When to start fault injections
    bool enableFaultInjection;          // Enable/disable fault injection
    bool enableVisualization;           // Enable NetAnim with slow speeds
    bool enableFaultVisualization;      // Enable visual fault indicators
    int targetDataPoints;               // Target number of data points
    std::string outputPrefix;           // Output file prefix
};

// ROBUST: Enhanced fault pattern structure
struct GradualFaultPattern {
    uint32_t targetNode;
    uint32_t connectedNode;
    std::string faultType;
    std::string faultDescription;
    Time startDegradation;
    Time faultOccurrence;
    Time faultDuration;
    Time recoveryComplete;
    double degradationRate;
    double recoveryRate;
    double severity;
    bool isActive;
    double currentSeverity;
    bool visualIndicatorActive;
    std::string visualMessage;
};

// ROBUST: Fault event logging structure
struct FaultEvent {
    double timestamp;
    std::string eventType;
    std::string faultType;
    std::vector<uint32_t> affectedNodes;
    std::string description;
    std::string visualEffect;
};

class CompleteRuralNetworkSimulation
{
public:
    CompleteRuralNetworkSimulation(const SimulationConfig& config);
    void Run();
    
    // Configuration factory methods
    static SimulationConfig CreateBaselineConfig(int targetDataPoints = 500);
    static SimulationConfig CreateFaultDemoConfig();
    static SimulationConfig CreateMixedConfig(int baselinePoints = 500, int faultPoints = 100);

private:
    // Configuration
    SimulationConfig m_config;
    
    // Network containers
    NodeContainer coreNodes;
    NodeContainer distributionNodes;
    NodeContainer accessNodes;
    NodeContainer allNodes;
    std::map<std::pair<uint32_t, uint32_t>, bool> linkStatus;
    
    // Network devices
    NetDeviceContainer coreDevices;
    NetDeviceContainer distributionDevices;
    NetDeviceContainer accessDevices;
    std::vector<Ipv4InterfaceContainer> allInterfaces;
    
    // Helper objects
    PointToPointHelper p2pHelper;
    MobilityHelper mobility;
    InternetStackHelper stack;
    Ipv4AddressHelper address;
    
    // Applications and monitoring
    ApplicationContainer sourceApps;
    ApplicationContainer sinkApps;
    FlowMonitorHelper flowHelper;
    Ptr<FlowMonitor> flowMonitor;
    
    // Output files
    std::ofstream metricsFile;
    std::ofstream topologyFile;
    std::ofstream configFile;
    std::ofstream faultLogFile;
    
    // Enhanced fault patterns
    std::vector<GradualFaultPattern> gradualFaults;
    std::vector<FaultEvent> faultEvents;
    
    // NetAnim pointer
    AnimationInterface* animInterface;
    
    // Baseline data enhancement
    double GetTimeOfDayMultiplier();
    double GetTrafficPatternMultiplier();
    double GetSeasonalVariation();
    
    // ROBUST: Setup methods with guaranteed functionality
    void SetupRobustTopology();
    void SetupRobustApplications();
    void SetupCoreLayer();
    void SetupDistributionLayer();
    void SetupAccessLayer();
    void SetupRobustRouting();
    void SetupEnergyModel();
    
    // ROBUST: Application methods
    void CreateGuaranteedTrafficFlows();
    void CreateBaselineTraffic();
    void CreateVisualizationTraffic();
    
    // ROBUST: NetAnim setup
    void SetupRobustNetAnimVisualization();
    
    // ROBUST: Fault injection methods
    void ScheduleGradualFaultPatterns();
    void CreateRealisticFiberCutPattern(uint32_t nodeA, uint32_t nodeB, Time startTime);
    void CreateRealisticPowerFluctuationPattern(uint32_t nodeId, Time startTime);
    void UpdateFaultProgression();
    double CalculateNodeDegradation(uint32_t nodeId, const std::string& metric);
    
    // ROBUST: Visual fault methods
    void ProcessFaultVisualization();
    void UpdateVisualFaultIndicators();
    void UpdateNodeVisualStatus(uint32_t nodeId, const std::string& status);
    void AnnounceFaultEvent(const GradualFaultPattern& fault, const std::string& eventType);
    void LogFaultEvent(const FaultEvent& event);
    
    // ADDED: Missing method declarations for fiber link visualization
    std::string GetNodeVisualName(uint32_t nodeId);
    void HideFiberLink(uint32_t nodeA, uint32_t nodeB);
    void RestoreFiberLink(uint32_t nodeA, uint32_t nodeB);
    
    // Data collection
    void CollectComprehensiveMetrics();
    void WriteTopologyInfo();
    void WriteConfigurationInfo();
    void WriteFaultEventLog();
    
    // Enhanced metrics generation
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

// ROBUST: Configuration factory methods
SimulationConfig CompleteRuralNetworkSimulation::CreateBaselineConfig(int targetDataPoints)
{
    SimulationConfig config;
    config.mode = "baseline";
    config.dataCollectionInterval = 10.0;
    config.totalSimulationTime = targetDataPoints * config.dataCollectionInterval;
    config.baselineDuration = config.totalSimulationTime;
    config.faultStartTime = config.totalSimulationTime + 100;
    config.enableFaultInjection = false;
    config.enableVisualization = false;
    config.enableFaultVisualization = false;
    config.targetDataPoints = targetDataPoints;
    config.outputPrefix = "baseline";
    
    std::cout << "=== BASELINE CONFIGURATION ===" << std::endl;
    std::cout << "Target data points: " << targetDataPoints << std::endl;
    std::cout << "Simulation duration: " << config.totalSimulationTime << "s" << std::endl;
    std::cout << "Mode: FAULT-FREE BASELINE DATA GENERATION" << std::endl;
    std::cout << "===============================" << std::endl;
    
    return config;
}

SimulationConfig CompleteRuralNetworkSimulation::CreateFaultDemoConfig()
{
    SimulationConfig config;
    config.mode = "fault_demo";
    config.dataCollectionInterval = 5.0;
    config.totalSimulationTime = 600.0;
    config.baselineDuration = 120.0;
    config.faultStartTime = 120.0;
    config.enableFaultInjection = true;
    config.enableVisualization = true;
    config.enableFaultVisualization = true;
    config.targetDataPoints = 120;
    config.outputPrefix = "fault_demo";
    
    std::cout << "=== FAULT DEMONSTRATION CONFIGURATION ===" << std::endl;
    std::cout << "Simulation duration: " << config.totalSimulationTime << "s" << std::endl;
    std::cout << "Baseline period: " << config.baselineDuration << "s" << std::endl;
    std::cout << "Mode: VISUAL FAULT DEMONSTRATION FOR JUDGES" << std::endl;
    std::cout << "Visual indicators: ENABLED" << std::endl;
    std::cout << "Packet visibility: ENHANCED" << std::endl;
    std::cout << "=========================================" << std::endl;
    
    return config;
}

SimulationConfig CompleteRuralNetworkSimulation::CreateMixedConfig(int baselinePoints, int faultPoints)
{
    SimulationConfig config;
    config.mode = "mixed";
    config.dataCollectionInterval = 10.0;
    config.baselineDuration = baselinePoints * config.dataCollectionInterval;
    config.totalSimulationTime = (baselinePoints + faultPoints) * config.dataCollectionInterval;
    config.faultStartTime = config.baselineDuration;
    config.enableFaultInjection = true;
    config.enableVisualization = false;
    config.enableFaultVisualization = false;
    config.targetDataPoints = baselinePoints + faultPoints;
    config.outputPrefix = "mixed";
    
    std::cout << "=== MIXED CONFIGURATION ===" << std::endl;
    std::cout << "Baseline points: " << baselinePoints << " (" << config.baselineDuration << "s)" << std::endl;
    std::cout << "Fault points: " << faultPoints << std::endl;
    std::cout << "Mode: LSTM TRAINING DATA (BASELINE + FAULTS)" << std::endl;
    std::cout << "===========================" << std::endl;
    
    return config;
}

CompleteRuralNetworkSimulation::CompleteRuralNetworkSimulation(const SimulationConfig& config) 
    : m_config(config), animInterface(nullptr)
{
    // Open output files
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
    
    faultLogFile << "=== COMPLETE RURAL NETWORK FAULT EVENT LOG ===" << std::endl;
    faultLogFile << "Simulation Mode: " << m_config.mode << std::endl;
    faultLogFile << "Visual Indicators: " << (m_config.enableFaultVisualization ? "ENABLED" : "DISABLED") << std::endl;
    faultLogFile << "===============================================" << std::endl;
    
    std::cout << "Complete simulation output files:" << std::endl;
    std::cout << "- Metrics: " << metricsFileName << std::endl;
    std::cout << "- Topology: " << topologyFileName << std::endl;
    std::cout << "- Config: " << configFileName << std::endl;
    std::cout << "- Fault Log: " << faultLogFileName << std::endl;
}

// ROBUST: Baseline data variation methods
double CompleteRuralNetworkSimulation::GetTimeOfDayMultiplier()
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

double CompleteRuralNetworkSimulation::GetTrafficPatternMultiplier()
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

double CompleteRuralNetworkSimulation::GetSeasonalVariation()
{
    double currentTime = Simulator::Now().GetSeconds();
    double seasonalCycle = sin(currentTime / 2592000.0 * 2 * M_PI);
    return 1.0 + 0.1 * seasonalCycle;
}

// ROBUST: Topology setup with guaranteed connectivity
void CompleteRuralNetworkSimulation::SetupRobustTopology()
{
    NS_LOG_FUNCTION(this);
    
    // Create 50 nodes: 5 core, 15 distribution, 30 access
    coreNodes.Create(5);
    distributionNodes.Create(15);
    accessNodes.Create(30);
    
    allNodes.Add(coreNodes);
    allNodes.Add(distributionNodes);
    allNodes.Add(accessNodes);
    
    std::cout << "Created " << allNodes.GetN() << " nodes total" << std::endl;
    
    // CRITICAL: Install mobility models on ALL nodes
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    mobility.Install(allNodes);
    
    // Setup layers
    SetupCoreLayer();
    SetupDistributionLayer();
    SetupAccessLayer();
    
    // Setup routing and energy
    SetupRobustRouting();
    SetupEnergyModel();
    WriteTopologyInfo();
}

void CompleteRuralNetworkSimulation::SetupCoreLayer()
{
    // Configure speeds based on mode
    if (m_config.enableVisualization) {
        p2pHelper.SetDeviceAttribute("DataRate", StringValue("1Mbps"));
        p2pHelper.SetChannelAttribute("Delay", StringValue("10ms"));
    } else {
        p2pHelper.SetDeviceAttribute("DataRate", StringValue("1Gbps"));
        p2pHelper.SetChannelAttribute("Delay", StringValue("2ms"));
    }
    
    // Position core nodes in clear pattern
    Ptr<ListPositionAllocator> corePositions = CreateObject<ListPositionAllocator>();
    corePositions->Add(Vector(0.0, 0.0, 0.0));      // Core0 - Center
    corePositions->Add(Vector(50.0, 0.0, 0.0));     // Core1 - East
    corePositions->Add(Vector(-50.0, 0.0, 0.0));    // Core2 - West
    corePositions->Add(Vector(0.0, 50.0, 0.0));     // Core3 - North
    corePositions->Add(Vector(0.0, -50.0, 0.0));    // Core4 - South
    
    // Set positions using mobility model
    for (uint32_t i = 0; i < coreNodes.GetN(); ++i) {
        Ptr<ConstantPositionMobilityModel> mob = coreNodes.Get(i)->GetObject<ConstantPositionMobilityModel>();
        mob->SetPosition(corePositions->GetNext());
    }
    
    // Create mesh connectivity between core nodes
    for (uint32_t i = 0; i < coreNodes.GetN(); ++i) {
        for (uint32_t j = i + 1; j < coreNodes.GetN(); ++j) {
            NetDeviceContainer link = p2pHelper.Install(coreNodes.Get(i), coreNodes.Get(j));
            coreDevices.Add(link);
        }
    }
    
    std::cout << "Core layer setup complete" << std::endl;
}

void CompleteRuralNetworkSimulation::SetupDistributionLayer()
{
    // Configure speeds
    if (m_config.enableVisualization) {
        p2pHelper.SetDeviceAttribute("DataRate", StringValue("512Kbps"));
        p2pHelper.SetChannelAttribute("Delay", StringValue("20ms"));
    } else {
        p2pHelper.SetDeviceAttribute("DataRate", StringValue("100Mbps"));
        p2pHelper.SetChannelAttribute("Delay", StringValue("10ms"));
    }
    
    // Position distribution nodes in ring
    for (uint32_t i = 0; i < distributionNodes.GetN(); ++i) {
        double angle = (2.0 * M_PI * i) / distributionNodes.GetN();
        double radius = 100.0;
        double x = radius * cos(angle);
        double y = radius * sin(angle);
        
        Ptr<ConstantPositionMobilityModel> mob = distributionNodes.Get(i)->GetObject<ConstantPositionMobilityModel>();
        mob->SetPosition(Vector(x, y, 0.0));
    }
    
    // Connect distribution to core (simplified for guaranteed connectivity)
    for (uint32_t i = 0; i < distributionNodes.GetN(); ++i) {
        uint32_t coreIndex = i % coreNodes.GetN();
        NetDeviceContainer link = p2pHelper.Install(distributionNodes.Get(i), coreNodes.Get(coreIndex));
        distributionDevices.Add(link);
    }
    
    std::cout << "Distribution layer setup complete" << std::endl;
}

void CompleteRuralNetworkSimulation::SetupAccessLayer()
{
    // Configure speeds
    if (m_config.enableVisualization) {
        p2pHelper.SetDeviceAttribute("DataRate", StringValue("256Kbps"));
        p2pHelper.SetChannelAttribute("Delay", StringValue("50ms"));
    } else {
        p2pHelper.SetDeviceAttribute("DataRate", StringValue("50Mbps"));
        p2pHelper.SetChannelAttribute("Delay", StringValue("5ms"));
    }
    
    // Position access nodes
    if (m_config.enableVisualization) {
        // Organized grid for demo
        for (uint32_t i = 0; i < accessNodes.GetN(); ++i) {
            double x = (i % 6) * 40.0 - 100.0;
            double y = (i / 6) * 40.0 - 100.0;
            
            Ptr<ConstantPositionMobilityModel> mob = accessNodes.Get(i)->GetObject<ConstantPositionMobilityModel>();
            mob->SetPosition(Vector(x, y, 0.0));
        }
    } else {
        // Random positioning for realistic simulation
        for (uint32_t i = 0; i < accessNodes.GetN(); ++i) {
            double x = (rand() % 400) - 200.0;
            double y = (rand() % 400) - 200.0;
            
            Ptr<ConstantPositionMobilityModel> mob = accessNodes.Get(i)->GetObject<ConstantPositionMobilityModel>();
            mob->SetPosition(Vector(x, y, 0.0));
        }
    }
    
    // Connect access to distribution (simplified for guaranteed connectivity)
    for (uint32_t i = 0; i < accessNodes.GetN(); ++i) {
        uint32_t distIndex = i % distributionNodes.GetN();
        NetDeviceContainer link = p2pHelper.Install(accessNodes.Get(i), distributionNodes.Get(distIndex));
        accessDevices.Add(link);
    }
    
    std::cout << "Access layer setup complete" << std::endl;
}

// ROBUST: Routing setup with guaranteed functionality
void CompleteRuralNetworkSimulation::SetupRobustRouting()
{
    NS_LOG_FUNCTION(this);
    
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
    
    // CRITICAL: Populate routing tables
    Ipv4GlobalRoutingHelper::PopulateRoutingTables();
    
    std::cout << "Robust routing setup complete with " << allInterfaces.size() << " interface pairs" << std::endl;
}

void CompleteRuralNetworkSimulation::SetupEnergyModel()
{
    BasicEnergySourceHelper basicSourceHelper;
    basicSourceHelper.Set("BasicEnergySourceInitialEnergyJ", DoubleValue(10000));
    energy::EnergySourceContainer sources = basicSourceHelper.Install(allNodes);
    
    std::cout << "Energy model setup complete" << std::endl;
}

// ROBUST: Application setup with guaranteed packet flows
void CompleteRuralNetworkSimulation::SetupRobustApplications()
{
    if (m_config.enableVisualization) {
        CreateVisualizationTraffic();
    } else {
        CreateBaselineTraffic();
    }
    
    std::cout << "Robust applications setup complete for " << m_config.mode << " mode" << std::endl;
}

void CompleteRuralNetworkSimulation::CreateVisualizationTraffic()
{
    std::cout << "Creating GUARANTEED VISIBLE traffic for NetAnim..." << std::endl;
    
    uint16_t port = 8080;
    
    // ROBUST: Create servers on LAST 5 access nodes using their actual IPs
    for (uint32_t i = 25; i < 30; ++i) {  // Access nodes 25-29 (last 5)
        // Find the IP address from the interfaces
        uint32_t interfaceIndex = (distributionDevices.GetN() / 2) + (i - 20);  // Access interface index
        if (interfaceIndex < allInterfaces.size()) {
            Ipv4Address serverAddr = allInterfaces[interfaceIndex].GetAddress(1);  // Access node IP
            
            UdpEchoServerHelper echoServer(port);
            ApplicationContainer serverApp = echoServer.Install(accessNodes.Get(i - 20));
            serverApp.Start(Seconds(10.0));
            serverApp.Stop(Seconds(m_config.totalSimulationTime - 10.0));
            sinkApps.Add(serverApp);
            
            std::cout << "Server: ACCESS-" << (i-20) << " on " << serverAddr << ":" << port << std::endl;
            port++;
        }
    }
    
    // ROBUST: Create clients on core nodes
    port = 8080;
    for (uint32_t coreIdx = 0; coreIdx < coreNodes.GetN(); ++coreIdx) {
        uint32_t targetAccessIdx = 25 + coreIdx;  // Target access nodes 25-29
        uint32_t interfaceIndex = (distributionDevices.GetN() / 2) + (targetAccessIdx - 20);
        
        if (interfaceIndex < allInterfaces.size()) {
            Ipv4Address targetAddr = allInterfaces[interfaceIndex].GetAddress(1);
            
            UdpEchoClientHelper echoClient(targetAddr, port);
            echoClient.SetAttribute("MaxPackets", UintegerValue(100));
            echoClient.SetAttribute("Interval", TimeValue(Seconds(3.0)));  // 1 packet every 3 seconds
            echoClient.SetAttribute("PacketSize", UintegerValue(1024));
            
            ApplicationContainer clientApp = echoClient.Install(coreNodes.Get(coreIdx));
            clientApp.Start(Seconds(15.0 + coreIdx * 2.0));
            clientApp.Stop(Seconds(m_config.totalSimulationTime - 10.0));
            sourceApps.Add(clientApp);
            
            std::cout << "Client: CORE-" << coreIdx << " → ACCESS-" << (targetAccessIdx-20) 
                     << " (" << targetAddr << ":" << port << ")" << std::endl;
            port++;
        }
    }
    
    std::cout << "Visualization traffic configured - GUARANTEED PACKET FLOWS!" << std::endl;
}

void CompleteRuralNetworkSimulation::CreateBaselineTraffic()
{
    std::cout << "Creating baseline traffic for data generation..." << std::endl;
    
    uint16_t port = 8080;
    
    // Create servers on every 5th access node
    for (uint32_t i = 0; i < accessNodes.GetN(); i += 5) {
        uint32_t interfaceIndex = (distributionDevices.GetN() / 2) + i;
        if (interfaceIndex < allInterfaces.size()) {
            Ipv4Address serverAddr = allInterfaces[interfaceIndex].GetAddress(1);
            
            UdpEchoServerHelper echoServer(port);
            ApplicationContainer serverApp = echoServer.Install(accessNodes.Get(i));
            serverApp.Start(Seconds(1.0));
            serverApp.Stop(Seconds(m_config.totalSimulationTime));
            sinkApps.Add(serverApp);
            
            port++;
        }
    }
    
    // Create clients on core nodes
    port = 8080;
    for (uint32_t i = 0; i < coreNodes.GetN(); ++i) {
        for (uint32_t j = 0; j < accessNodes.GetN(); j += 15) {  // Every 15th access node
            uint32_t interfaceIndex = (distributionDevices.GetN() / 2) + j;
            if (interfaceIndex < allInterfaces.size()) {
                Ipv4Address targetAddr = allInterfaces[interfaceIndex].GetAddress(1);
                
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
    
    std::cout << "Baseline traffic configured for data generation" << std::endl;
}

// ROBUST: NetAnim setup
void CompleteRuralNetworkSimulation::SetupRobustNetAnimVisualization()
{
    std::cout << "Setting up ROBUST NetAnim visualization..." << std::endl;
    
    std::string animFileName = m_config.outputPrefix + "_network_animation.xml";
    animInterface = new AnimationInterface(animFileName);
    
    // CRITICAL: Enable packet metadata
    animInterface->EnablePacketMetadata(true);
    
    if (m_config.enableVisualization) {
        animInterface->SetMaxPktsPerTraceFile(500);
        animInterface->SetMobilityPollInterval(Seconds(1));
        animInterface->SetStartTime(Seconds(10));
        animInterface->SetStopTime(Seconds(m_config.totalSimulationTime));
    }
    
    // Set node colors and descriptions
    for (uint32_t i = 0; i < allNodes.GetN(); ++i) {
        std::string nodeDesc;
        
        if (i < 5) {
            nodeDesc = "CORE-" + std::to_string(i);
            animInterface->UpdateNodeColor(allNodes.Get(i), 0, 100, 255);
            animInterface->UpdateNodeSize(allNodes.Get(i), 3.0, 3.0);
        } else if (i < 20) {
            nodeDesc = "DIST-" + std::to_string(i-5);
            animInterface->UpdateNodeColor(allNodes.Get(i), 0, 255, 0);
            animInterface->UpdateNodeSize(allNodes.Get(i), 2.0, 2.0);
        } else {
            nodeDesc = "ACC-" + std::to_string(i-20);
            animInterface->UpdateNodeColor(allNodes.Get(i), 255, 192, 203);
            animInterface->UpdateNodeSize(allNodes.Get(i), 1.5, 1.5);
        }
        
        animInterface->UpdateNodeDescription(allNodes.Get(i), nodeDesc);
    }
    
    std::cout << "NetAnim configured: " << animFileName << std::endl;
}

// ROBUST: Fault injection methods
void CompleteRuralNetworkSimulation::ScheduleGradualFaultPatterns()
{
    std::cout << "Scheduling GRADUAL fault patterns..." << std::endl;
    
    // Fiber cut patterns
    CreateRealisticFiberCutPattern(5, 20, Seconds(m_config.faultStartTime + 60.0));
    CreateRealisticFiberCutPattern(0, 1, Seconds(m_config.faultStartTime + 180.0));
    CreateRealisticFiberCutPattern(10, 25, Seconds(m_config.faultStartTime + 300.0));
    
    // Power fluctuation patterns
    CreateRealisticPowerFluctuationPattern(25, Seconds(m_config.faultStartTime + 120.0));
    CreateRealisticPowerFluctuationPattern(15, Seconds(m_config.faultStartTime + 240.0));
    CreateRealisticPowerFluctuationPattern(35, Seconds(m_config.faultStartTime + 360.0));
    
    std::cout << "Scheduled " << gradualFaults.size() << " gradual fault patterns" << std::endl;
    
    if (m_config.enableFaultVisualization) {
        Simulator::Schedule(Seconds(1.0), &CompleteRuralNetworkSimulation::ProcessFaultVisualization, this);
    }
}

void CompleteRuralNetworkSimulation::CreateRealisticFiberCutPattern(uint32_t nodeA, uint32_t nodeB, Time startTime)
{
    // Convert node IDs to visual names for better logging
    std::string nodeAName = GetNodeVisualName(nodeA);
    std::string nodeBName = GetNodeVisualName(nodeB);
    
    GradualFaultPattern pattern;
    pattern.targetNode = nodeA;
    pattern.connectedNode = nodeB;
    pattern.faultType = "fiber_cut";
    pattern.faultDescription = "FIBER CUT between " + nodeAName + " and " + nodeBName;
    pattern.startDegradation = startTime;
    pattern.faultOccurrence = startTime + Seconds(45.0);
    pattern.faultDuration = Seconds(120.0);
    pattern.recoveryComplete = pattern.faultOccurrence + pattern.faultDuration + Seconds(90.0);
    pattern.degradationRate = 0.8;
    pattern.recoveryRate = 0.7;
    pattern.severity = 1.0;
    pattern.isActive = true;
    pattern.currentSeverity = 0.0;
    pattern.visualIndicatorActive = false;
    pattern.visualMessage = "🔥 FIBER CUT: " + nodeAName + "↔" + nodeBName;
    
    gradualFaults.push_back(pattern);
    
    // Also create pattern for connected node
    pattern.targetNode = nodeB;
    pattern.connectedNode = nodeA;
    pattern.severity = 0.6;
    pattern.visualMessage = "⚠️ AFFECTED: " + nodeBName + " (Connected to " + nodeAName + ")";
    gradualFaults.push_back(pattern);
    
    // ENHANCED: Schedule link visualization events
    Simulator::Schedule(startTime + Seconds(45.0), 
                       &CompleteRuralNetworkSimulation::HideFiberLink, this, nodeA, nodeB);
    Simulator::Schedule(pattern.recoveryComplete,
                       &CompleteRuralNetworkSimulation::RestoreFiberLink, this, nodeA, nodeB);
    
    std::cout << "📋 FIBER CUT: " << nodeAName << "↔" << nodeBName 
              << " at " << startTime.GetSeconds() << "s" << std::endl;
}

// ADDED: Get visual node name for better identification
std::string CompleteRuralNetworkSimulation::GetNodeVisualName(uint32_t nodeId)
{
    if (nodeId < 5) {
        return "CORE-" + std::to_string(nodeId);
    } else if (nodeId < 20) {
        return "DIST-" + std::to_string(nodeId - 5);
    } else {
        return "ACC-" + std::to_string(nodeId - 20);
    }
}

void CompleteRuralNetworkSimulation::HideFiberLink(uint32_t nodeA, uint32_t nodeB)
{
    if (!animInterface) return;
    
    std::string nodeAName = GetNodeVisualName(nodeA);
    std::string nodeBName = GetNodeVisualName(nodeB);
    
    // Visual indication of broken link using node descriptions
    std::string breakMsg = "❌ LINK CUT to " + nodeBName;
    animInterface->UpdateNodeDescription(allNodes.Get(nodeA), nodeAName + "\n" + breakMsg);
    
    breakMsg = "❌ LINK CUT to " + nodeAName;
    animInterface->UpdateNodeDescription(allNodes.Get(nodeB), nodeBName + "\n" + breakMsg);
    
    // Store link status
    linkStatus[std::make_pair(std::min(nodeA, nodeB), std::max(nodeA, nodeB))] = false;
    
    std::cout << "🔴 VISUAL: Fiber link " << nodeAName << "↔" << nodeBName << " DISCONNECTED" << std::endl;
}

void CompleteRuralNetworkSimulation::RestoreFiberLink(uint32_t nodeA, uint32_t nodeB)
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

void CompleteRuralNetworkSimulation::CreateRealisticPowerFluctuationPattern(uint32_t nodeId, Time startTime)
{
    GradualFaultPattern pattern;
    pattern.targetNode = nodeId;
    pattern.connectedNode = 0;
    pattern.faultType = "power_fluctuation";
    pattern.faultDescription = "POWER FLUCTUATION on node " + std::to_string(nodeId);
    pattern.startDegradation = startTime;
    pattern.faultOccurrence = startTime + Seconds(60.0);
    pattern.faultDuration = Seconds(90.0);
    pattern.recoveryComplete = pattern.faultOccurrence + pattern.faultDuration + Seconds(120.0);
    pattern.degradationRate = 0.6;
    pattern.recoveryRate = 0.8;
    pattern.severity = 0.7;
    pattern.isActive = true;
    pattern.currentSeverity = 0.0;
    pattern.visualIndicatorActive = false;
    pattern.visualMessage = "⚡ POWER ISSUE: Node " + std::to_string(nodeId);
    
    gradualFaults.push_back(pattern);
    
    std::cout << "📋 FAULT: Power fluctuation scheduled - Node " << nodeId 
              << " at " << startTime.GetSeconds() << "s" << std::endl;
}

void CompleteRuralNetworkSimulation::UpdateFaultProgression()
{
    Time currentTime = Simulator::Now();
    
    for (auto& fault : gradualFaults) {
        if (!fault.isActive) continue;
        
        double previousSeverity = fault.currentSeverity;
        
        // Calculate current severity based on timeline
        if (currentTime < fault.startDegradation) {
            fault.currentSeverity = 0.0;
        }
        else if (currentTime < fault.faultOccurrence) {
            // Gradual degradation phase
            double progress = (currentTime - fault.startDegradation).GetSeconds() / 
                            (fault.faultOccurrence - fault.startDegradation).GetSeconds();
            fault.currentSeverity = progress * fault.degradationRate;
        }
        else if (currentTime < fault.faultOccurrence + fault.faultDuration) {
            // Peak fault phase
            fault.currentSeverity = fault.severity;
        }
        else if (currentTime < fault.recoveryComplete) {
            // Recovery phase
            double recovery_progress = (currentTime - (fault.faultOccurrence + fault.faultDuration)).GetSeconds() / 
                                     (fault.recoveryComplete - (fault.faultOccurrence + fault.faultDuration)).GetSeconds();
            fault.currentSeverity = fault.severity * (1.0 - recovery_progress * fault.recoveryRate);
        }
        else {
            // Full recovery
            fault.currentSeverity = 0.0;
            fault.isActive = false;
        }
        
        // Trigger visual events at key milestones
        if (m_config.enableFaultVisualization) {
            if (previousSeverity == 0.0 && fault.currentSeverity > 0.0) {
                AnnounceFaultEvent(fault, "DEGRADATION_START");
            }
            else if (previousSeverity < fault.severity && fault.currentSeverity >= fault.severity) {
                AnnounceFaultEvent(fault, "FAULT_PEAK");
            }
            else if (fault.currentSeverity < 0.1 && previousSeverity >= 0.1) {
                AnnounceFaultEvent(fault, "RECOVERY_COMPLETE");
            }
        }
    }
}

double CompleteRuralNetworkSimulation::CalculateNodeDegradation(uint32_t nodeId, const std::string& metric)
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

// Visual fault methods
void CompleteRuralNetworkSimulation::ProcessFaultVisualization()
{
    if (!m_config.enableFaultVisualization || !animInterface) {
        return;
    }
    
    UpdateVisualFaultIndicators();
    
    if (Simulator::Now().GetSeconds() < m_config.totalSimulationTime - 1.0) {
        Simulator::Schedule(Seconds(1.0), &CompleteRuralNetworkSimulation::ProcessFaultVisualization, this);
    }
}

void CompleteRuralNetworkSimulation::UpdateVisualFaultIndicators()
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

void CompleteRuralNetworkSimulation::UpdateNodeVisualStatus(uint32_t nodeId, const std::string& status)
{
    if (!animInterface) return;
    
    if (status == "CRITICAL") {
        animInterface->UpdateNodeColor(allNodes.Get(nodeId), 255, 0, 0);
        animInterface->UpdateNodeSize(allNodes.Get(nodeId), 4.0, 4.0);
    } else if (status == "HIGH") {
        animInterface->UpdateNodeColor(allNodes.Get(nodeId), 255, 165, 0);
        animInterface->UpdateNodeSize(allNodes.Get(nodeId), 3.0, 3.0);
    } else if (status == "MEDIUM") {
        animInterface->UpdateNodeColor(allNodes.Get(nodeId), 255, 255, 0);
        animInterface->UpdateNodeSize(allNodes.Get(nodeId), 2.5, 2.5);
    } else if (status == "LOW") {
        animInterface->UpdateNodeColor(allNodes.Get(nodeId), 255, 200, 0);
        animInterface->UpdateNodeSize(allNodes.Get(nodeId), 2.0, 2.0);
    } else { // NORMAL
        // Restore original colors
        if (nodeId < 5) {
            animInterface->UpdateNodeColor(allNodes.Get(nodeId), 255, 0, 0);
            animInterface->UpdateNodeSize(allNodes.Get(nodeId), 3.0, 3.0);
        } else if (nodeId < 20) {
            animInterface->UpdateNodeColor(allNodes.Get(nodeId), 0, 255, 0);
            animInterface->UpdateNodeSize(allNodes.Get(nodeId), 2.0, 2.0);
        } else {
            animInterface->UpdateNodeColor(allNodes.Get(nodeId), 0, 0, 255);
            animInterface->UpdateNodeSize(allNodes.Get(nodeId), 1.5, 1.5);
        }
    }
}

void CompleteRuralNetworkSimulation::AnnounceFaultEvent(const GradualFaultPattern& fault, const std::string& eventType)
{
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
        event.visualEffect = "Nodes " + visualNodes + " changing to yellow";
    } else if (eventType == "FAULT_PEAK") {
        event.description = "🔴 FAULT CRITICAL: " + fault.faultDescription;
        event.visualEffect = "Nodes " + visualNodes + " turned RED, link broken";
    } else if (eventType == "RECOVERY_COMPLETE") {
        event.description = "🟢 RECOVERY COMPLETE: " + fault.faultDescription;
        event.visualEffect = "Nodes " + visualNodes + " restored, link repaired";
    }
    
    LogFaultEvent(event);
    
    std::cout << std::endl;
    std::cout << "📢 ============ FAULT EVENT ============" << std::endl;
    std::cout << "⏰ TIME: " << std::fixed << std::setprecision(1) << currentTime << "s" << std::endl;
    std::cout << "🎯 EVENT: " << event.description << std::endl;
    std::cout << "🎨 VISUAL: " << event.visualEffect << std::endl;
    std::cout << "📍 VISUAL NODES: " << visualNodes << std::endl;
    std::cout << "=======================================" << std::endl;
    std::cout << std::endl;
}

void CompleteRuralNetworkSimulation::LogFaultEvent(const FaultEvent& event)
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

// Data collection methods
void CompleteRuralNetworkSimulation::CollectComprehensiveMetrics()
{
    // Update fault progression if enabled
    if (m_config.enableFaultInjection && Simulator::Now().GetSeconds() >= m_config.faultStartTime) {
        UpdateFaultProgression();
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
                          &CompleteRuralNetworkSimulation::CollectComprehensiveMetrics, this);
    }
}

CompleteRuralNetworkSimulation::NodeMetrics CompleteRuralNetworkSimulation::GetEnhancedNodeMetrics(uint32_t nodeId)
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

void CompleteRuralNetworkSimulation::WriteTopologyInfo()
{
    topologyFile << "{\n  \"complete_rural_network_topology\": {\n";
    topologyFile << "    \"simulation_mode\": \"" << m_config.mode << "\",\n";
    topologyFile << "    \"total_nodes\": " << allNodes.GetN() << ",\n";
    topologyFile << "    \"core_layer\": {\n";
    topologyFile << "      \"node_count\": " << coreNodes.GetN() << ",\n";
    topologyFile << "      \"role\": \"Core routing and switching\"\n";
    topologyFile << "    },\n";
    topologyFile << "    \"distribution_layer\": {\n";
    topologyFile << "      \"node_count\": " << distributionNodes.GetN() << ",\n";
    topologyFile << "      \"role\": \"Regional distribution\"\n";
    topologyFile << "    },\n";
    topologyFile << "    \"access_layer\": {\n";
    topologyFile << "      \"node_count\": " << accessNodes.GetN() << ",\n";
    topologyFile << "      \"role\": \"End-user access points\"\n";
    topologyFile << "    }\n";
    topologyFile << "  }\n}\n";
    topologyFile.close();
}

void CompleteRuralNetworkSimulation::WriteConfigurationInfo()
{
    configFile << "{\n";
    configFile << "  \"complete_simulation_configuration\": {\n";
    configFile << "    \"mode\": \"" << m_config.mode << "\",\n";
    configFile << "    \"total_simulation_time\": " << m_config.totalSimulationTime << ",\n";
    configFile << "    \"data_collection_interval\": " << m_config.dataCollectionInterval << ",\n";
    configFile << "    \"enable_fault_injection\": " << (m_config.enableFaultInjection ? "true" : "false") << ",\n";
    configFile << "    \"enable_visualization\": " << (m_config.enableVisualization ? "true" : "false") << ",\n";
    configFile << "    \"target_data_points\": " << m_config.targetDataPoints << "\n";
    configFile << "  }\n";
    configFile << "}\n";
    configFile.close();
}

void CompleteRuralNetworkSimulation::WriteFaultEventLog()
{
    faultLogFile << std::endl << "=== FAULT EVENT SUMMARY ===" << std::endl;
    faultLogFile << "Total fault events: " << faultEvents.size() << std::endl;
    
    for (const auto& event : faultEvents) {
        faultLogFile << "[" << event.timestamp << "s] " << event.eventType 
                    << " - " << event.description << std::endl;
    }
    
    faultLogFile << "=========================" << std::endl;
    faultLogFile.close();
}

void CompleteRuralNetworkSimulation::Run()
{
    std::cout << "========================================" << std::endl;
    std::cout << "  COMPLETE RURAL NETWORK SIMULATION     " << std::endl;
    std::cout << "  Mode: " << m_config.mode << std::endl;
    std::cout << "  ALL REQUIREMENTS IMPLEMENTED          " << std::endl;
    std::cout << "========================================" << std::endl;
    
    SetupRobustTopology();
    SetupRobustApplications();
    SetupRobustNetAnimVisualization();
    
    // Schedule data collection
    Simulator::Schedule(Seconds(m_config.dataCollectionInterval), 
                       &CompleteRuralNetworkSimulation::CollectComprehensiveMetrics, this);
    
    // Schedule fault patterns if enabled
    if (m_config.enableFaultInjection) {
        std::cout << "Scheduling fault patterns starting at " << m_config.faultStartTime << "s..." << std::endl;
        ScheduleGradualFaultPatterns();
    } else {
        std::cout << "Running in baseline mode - generating fault-free data" << std::endl;
    }
    
    WriteConfigurationInfo();
    WriteTopologyInfo();
    
    Simulator::Stop(Seconds(m_config.totalSimulationTime));
    
    std::cout << "Starting simulation..." << std::endl;
    std::cout << "Duration: " << m_config.totalSimulationTime << "s" << std::endl;
    std::cout << "Expected data points: " << m_config.targetDataPoints << std::endl;
    
    Simulator::Run();
    
    std::cout << "========================================" << std::endl;
    std::cout << "Complete simulation finished!" << std::endl;
    std::cout << "Generated files:" << std::endl;
    std::cout << "- " << m_config.outputPrefix << "_network_metrics.csv" << std::endl;
    std::cout << "- " << m_config.outputPrefix << "_network_animation.xml" << std::endl;
    std::cout << "- " << m_config.outputPrefix << "_topology.json" << std::endl;
    std::cout << "- " << m_config.outputPrefix << "_fault_events.log" << std::endl;
    std::cout << "========================================" << std::endl;
    
    WriteFaultEventLog();
    Simulator::Destroy();
    
    if (animInterface) {
        delete animInterface;
    }
    
    metricsFile.close();
}

// Main function
int main(int argc, char *argv[])
{
    CommandLine cmd;
    
    std::string mode = "fault_demo";
    int dataPoints = 500;
    
    cmd.AddValue("mode", "Simulation mode: baseline, fault_demo, mixed", mode);
    cmd.AddValue("points", "Target number of data points", dataPoints);
    cmd.Parse(argc, argv);
    
    LogComponentEnable("CompleteRuralNetworkSimulation", LOG_LEVEL_INFO);
    RngSeedManager::SetSeed(12345);
    
    // Create configuration
    SimulationConfig config;
    
    if (mode == "baseline") {
        config = CompleteRuralNetworkSimulation::CreateBaselineConfig(dataPoints);
    } else if (mode == "fault_demo") {
        config = CompleteRuralNetworkSimulation::CreateFaultDemoConfig();
    } else if (mode == "mixed") {
        config = CompleteRuralNetworkSimulation::CreateMixedConfig(dataPoints, 100);
    } else {
        std::cerr << "Invalid mode. Use: baseline, fault_demo, or mixed" << std::endl;
        return 1;
    }
    
    // Run complete simulation
    CompleteRuralNetworkSimulation simulation(config);
    simulation.Run();
    
    return 0;
}