/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Enhanced Rural 50-Node Self-Healing Network Simulation
 * With Gradual Fault Patterns and NetAnim Visualization
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
#include "ns3/nix-vector-routing-module.h"
#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <iomanip>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <thread>
#include <map>
#include <cmath>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("RuralSelfHealingNetwork");

// Progress printing function
void PrintProgress(int minute)
{
    std::cout << "[" << minute << "/10] Simulation progress: " << minute*10 << "% complete" << std::endl;
}

// Enhanced fault pattern structure
struct GradualFaultPattern {
    uint32_t targetNode;
    uint32_t connectedNode;       // For fiber cuts
    std::string faultType;
    Time startDegradation;        // When degradation begins
    Time faultOccurrence;         // When actual fault occurs  
    Time faultDuration;           // How long fault lasts
    Time recoveryComplete;        // When full recovery completes
    double degradationRate;       // How fast degradation happens (0.0-1.0)
    double recoveryRate;          // How fast recovery happens (0.0-1.0)
    double severity;              // Final fault severity (0.0-1.0)
    bool isActive;
    double currentSeverity;
};

class RuralNetworkSimulation
{
public:
    RuralNetworkSimulation();
    void Run();

private:
    // Network containers
    NodeContainer coreNodes;
    NodeContainer distributionNodes;
    NodeContainer accessNodes;
    NodeContainer allNodes;
    
    // Network devices
    NetDeviceContainer coreDevices;
    NetDeviceContainer distributionDevices;
    NetDeviceContainer accessDevices;
    std::map<std::pair<uint32_t, uint32_t>, NetDeviceContainer> linkMap;
    
    // Helper objects
    PointToPointHelper p2pHelper;
    WifiHelper wifiHelper;
    YansWifiChannelHelper wifiChannel;
    YansWifiPhyHelper wifiPhy;
    WifiMacHelper wifiMac;
    MobilityHelper mobility;
    InternetStackHelper stack;
    Ipv4AddressHelper address;
    
    // Applications and monitoring
    ApplicationContainer sourceApps;
    ApplicationContainer sinkApps;
    FlowMonitorHelper flowHelper;
    Ptr<FlowMonitor> flowMonitor;
    
    // Socket server for Python integration
    int serverSocket;
    bool simulationRunning;
    
    // Output files
    std::ofstream metricsFile;
    std::ofstream topologyFile;
    
    // Enhanced fault patterns
    std::vector<GradualFaultPattern> gradualFaults;
    Time dataCollectionInterval;
    bool useVisualizationSpeeds;  // Flag for slow speeds
    
    // Setup methods
    void SetupTopology();
    void SetupApplications();
    void SetupMetricsCollection();
    void SetupCoreLayer();
    void SetupDistributionLayer();
    void SetupAccessLayer();
    void ConnectLayers();
    void SetupRouting();
    void SetupEnergyModel();
    
    // Visualization methods
    void CreateTestTrafficForVisualization();
    
    // Enhanced fault pattern methods
    void ScheduleGradualFaultPatterns();
    void CreateRealisticFiberCutPattern(uint32_t nodeA, uint32_t nodeB, Time startTime);
    void CreateRealisticPowerFluctuationPattern(uint32_t nodeId, Time startTime);
    void UpdateFaultProgression();
    double CalculateNodeDegradation(uint32_t nodeId, const std::string& metric);
    
    // Data collection
    void CollectHighFrequencyMetrics();
    void WriteTopologyInfo();
    
    // Socket server
    void StartSocketServer();
    void HandleSocketConnection();
    void ProcessCommand(const std::string& command);
    
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
        double degradationLevel;    // New: gradual degradation
        double faultSeverity;       // New: fault severity
    };
    
    NodeMetrics GetEnhancedNodeMetrics(uint32_t nodeId);
};

RuralNetworkSimulation::RuralNetworkSimulation() : simulationRunning(true)
{
    // High-frequency data collection (every 10 seconds for LSTM)
    dataCollectionInterval = Seconds(10.0);
    
    // Set to true for packet visualization, false for realistic performance
    useVisualizationSpeeds = true;  // Change to true to see packets in NetAnim
    
    // Open output files with enhanced headers
    metricsFile.open("rural_network_metrics.csv");
    metricsFile << "Time,NodeId,NodeType,Throughput_Mbps,Latency_ms,PacketLoss_Rate,Jitter_ms,"
                << "SignalStrength_dBm,CPU_Usage,Memory_Usage,Buffer_Occupancy,Active_Links,"
                << "Neighbor_Count,Link_Utilization,Critical_Load,Normal_Load,Energy_Level,"
                << "X_Position,Y_Position,Z_Position,Operational_Status,"
                << "Voltage_Level,Power_Stability,Degradation_Level,Fault_Severity\n";
    
    topologyFile.open("network_topology.json");
}

void RuralNetworkSimulation::SetupTopology()
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
    
    // Setup layers
    SetupCoreLayer();
    SetupDistributionLayer();
    SetupAccessLayer();
    ConnectLayers();
    
    // Setup routing and energy
    SetupRouting();
    SetupEnergyModel();
    WriteTopologyInfo();
}

void RuralNetworkSimulation::SetupCoreLayer()
{
    // Configure speeds based on visualization flag
    if (useVisualizationSpeeds) {
        std::cout << "Using slow speeds for NetAnim packet visibility" << std::endl;
        p2pHelper.SetDeviceAttribute("DataRate", StringValue("10Mbps"));
        p2pHelper.SetChannelAttribute("Delay", StringValue("100ms"));
    } else {
        // High-capacity core network for realistic simulation
        p2pHelper.SetDeviceAttribute("DataRate", StringValue("1Gbps"));
        p2pHelper.SetChannelAttribute("Delay", StringValue("2ms"));
    }
    
    // Position core nodes
    MobilityHelper coreMobility;
    Ptr<ListPositionAllocator> corePositions = CreateObject<ListPositionAllocator>();
    corePositions->Add(Vector(0.0, 0.0, 0.0));
    corePositions->Add(Vector(50.0, 0.0, 0.0));
    corePositions->Add(Vector(-50.0, 0.0, 0.0));
    corePositions->Add(Vector(0.0, 50.0, 0.0));
    corePositions->Add(Vector(0.0, -50.0, 0.0));
    
    coreMobility.SetPositionAllocator(corePositions);
    coreMobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    coreMobility.Install(coreNodes);
    
    // Create mesh connectivity
    for (uint32_t i = 0; i < coreNodes.GetN(); ++i) {
        for (uint32_t j = i + 1; j < coreNodes.GetN(); ++j) {
            NetDeviceContainer link = p2pHelper.Install(coreNodes.Get(i), coreNodes.Get(j));
            coreDevices.Add(link);
            linkMap[std::make_pair(i, j)] = link;
        }
    }
    
    std::cout << "Core layer setup complete" << std::endl;
}

void RuralNetworkSimulation::SetupDistributionLayer()
{
    // Configure speeds based on visualization flag
    if (useVisualizationSpeeds) {
        p2pHelper.SetDeviceAttribute("DataRate", StringValue("5Mbps"));
        p2pHelper.SetChannelAttribute("Delay", StringValue("200ms"));
    } else {
        // Medium-capacity distribution network
        p2pHelper.SetDeviceAttribute("DataRate", StringValue("100Mbps"));
        p2pHelper.SetChannelAttribute("Delay", StringValue("10ms"));
    }
    
    // Position distribution nodes in ring
    MobilityHelper distMobility;
    Ptr<ListPositionAllocator> distPositions = CreateObject<ListPositionAllocator>();
    
    for (uint32_t i = 0; i < distributionNodes.GetN(); ++i) {
        double angle = (2.0 * M_PI * i) / distributionNodes.GetN();
        double radius = 25.0;
        double x = radius * cos(angle);
        double y = radius * sin(angle);
        distPositions->Add(Vector(x, y, 0.0));
    }
    
    distMobility.SetPositionAllocator(distPositions);
    distMobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    distMobility.Install(distributionNodes);
    
    // Connect to core nodes
    for (uint32_t i = 0; i < distributionNodes.GetN(); ++i) {
        uint32_t core1 = i % coreNodes.GetN();
        uint32_t core2 = (i + 1) % coreNodes.GetN();
        
        NetDeviceContainer link1 = p2pHelper.Install(distributionNodes.Get(i), coreNodes.Get(core1));
        NetDeviceContainer link2 = p2pHelper.Install(distributionNodes.Get(i), coreNodes.Get(core2));
        
        distributionDevices.Add(link1);
        distributionDevices.Add(link2);
        
        uint32_t distNodeId = i + 5;
        linkMap[std::make_pair(std::min(distNodeId, core1), std::max(distNodeId, core1))] = link1;
        linkMap[std::make_pair(std::min(distNodeId, core2), std::max(distNodeId, core2))] = link2;
    }
    
    std::cout << "Distribution layer setup complete" << std::endl;
}

void RuralNetworkSimulation::SetupAccessLayer()
{
    // WiFi for access layer
    wifiChannel = YansWifiChannelHelper::Default();
    wifiChannel.SetPropagationDelay("ns3::ConstantSpeedPropagationDelayModel");
    wifiChannel.AddPropagationLoss("ns3::RangePropagationLossModel", "MaxRange", DoubleValue(10000));
    
    wifiPhy.SetErrorRateModel("ns3::NistErrorRateModel");
    wifiPhy.SetChannel(wifiChannel.Create());
    wifiPhy.Set("TxPowerStart", DoubleValue(20.0));
    wifiPhy.Set("TxPowerEnd", DoubleValue(20.0));
    
    wifiHelper.SetStandard(WIFI_STANDARD_80211b);
    wifiHelper.SetRemoteStationManager("ns3::ConstantRateWifiManager",
                                      "DataMode", StringValue("DsssRate11Mbps"),
                                      "ControlMode", StringValue("DsssRate11Mbps"));
    
    // Position access nodes randomly
    MobilityHelper accessMobility;
    accessMobility.SetPositionAllocator("ns3::RandomRectanglePositionAllocator",
                                       "X", StringValue("ns3::UniformRandomVariable[Min=-75.0|Max=75.0]"),
                                       "Y", StringValue("ns3::UniformRandomVariable[Min=-75.0|Max=75.0]"));
    accessMobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    accessMobility.Install(accessNodes);
    
    Ssid ssid = Ssid("rural-network-access");
    wifiMac.SetType("ns3::ApWifiMac", "Ssid", SsidValue(ssid));
    accessDevices = wifiHelper.Install(wifiPhy, wifiMac, accessNodes);
    
    std::cout << "Access layer setup complete" << std::endl;
}

void RuralNetworkSimulation::ConnectLayers()
{
    // Configure speeds based on visualization flag
    if (useVisualizationSpeeds) {
        p2pHelper.SetDeviceAttribute("DataRate", StringValue("1Mbps"));
        p2pHelper.SetChannelAttribute("Delay", StringValue("500ms"));
    } else {
        // Connect access to distribution
        p2pHelper.SetDeviceAttribute("DataRate", StringValue("50Mbps"));
        p2pHelper.SetChannelAttribute("Delay", StringValue("5ms"));
    }
    
    // Create separate container for access-to-distribution links
    NetDeviceContainer accessToDistLinks;
    
    for (uint32_t i = 0; i < accessNodes.GetN(); ++i) {
        uint32_t distIndex = i % distributionNodes.GetN();
        NetDeviceContainer link = p2pHelper.Install(accessNodes.Get(i), distributionNodes.Get(distIndex));
        accessToDistLinks.Add(link);
        
        uint32_t accessNodeId = i + 20;
        uint32_t distNodeId = distIndex + 5;
        linkMap[std::make_pair(std::min(accessNodeId, distNodeId), std::max(accessNodeId, distNodeId))] = link;
    }
    
    std::cout << "Layer connectivity established" << std::endl;
}

void RuralNetworkSimulation::SetupRouting()
{
    NS_LOG_FUNCTION(this);
    
    // Set up NixVector routing BEFORE installing Internet stack
    Ipv4NixVectorHelper nixRouting;
    stack.SetRoutingHelper(nixRouting);
    
    // Install Internet stack with NixVector routing
    stack.Install(allNodes);
    
    // Assign IP addresses AFTER installing stack
    address.SetBase("10.1.1.0", "255.255.255.0");
    
    // Core network
    for (uint32_t i = 0; i < coreDevices.GetN(); ++i) {
        address.Assign(coreDevices.Get(i));
        address.NewNetwork();
    }
    
    // Distribution network
    for (uint32_t i = 0; i < distributionDevices.GetN(); ++i) {
        address.Assign(distributionDevices.Get(i));
        address.NewNetwork();
    }
    
    // Access network
    address.SetBase("10.100.1.0", "255.255.255.0");
    address.Assign(accessDevices);
    
    std::cout << "NixVector routing setup complete" << std::endl;
}

void RuralNetworkSimulation::SetupEnergyModel()
{
    BasicEnergySourceHelper basicSourceHelper;
    basicSourceHelper.Set("BasicEnergySourceInitialEnergyJ", DoubleValue(10000));
    energy::EnergySourceContainer sources = basicSourceHelper.Install(allNodes);
    
    std::cout << "Energy model setup complete" << std::endl;
}

void RuralNetworkSimulation::SetupApplications()
{
    // Configure application speeds based on visualization flag
    uint16_t port = 8080;
    
    PacketSinkHelper packetSinkHelper("ns3::UdpSocketFactory", InetSocketAddress(Ipv4Address::GetAny(), port));
    sinkApps = packetSinkHelper.Install(accessNodes);
    sinkApps.Start(Seconds(1.0));
    sinkApps.Stop(Seconds(600.0));
    
    if (useVisualizationSpeeds) {
        // Slower, more visible traffic for NetAnim
        for (uint32_t i = 0; i < coreNodes.GetN(); ++i) {
            for (uint32_t j = 0; j < accessNodes.GetN(); j += 15) { // Even fewer connections
                Ptr<Node> accessNode = accessNodes.Get(j);
                Ptr<Ipv4> ipv4 = accessNode->GetObject<Ipv4>();
                Ipv4Address addr = ipv4->GetAddress(1, 0).GetLocal();
                
                UdpEchoClientHelper echoClient(addr, port);
                echoClient.SetAttribute("MaxPackets", UintegerValue(30));
                echoClient.SetAttribute("Interval", TimeValue(Seconds(5.0))); // Very slow: 1 packet every 5 seconds
                echoClient.SetAttribute("PacketSize", UintegerValue(256));
                
                ApplicationContainer app = echoClient.Install(coreNodes.Get(i));
                app.Start(Seconds(2.0 + i * 0.5));
                app.Stop(Seconds(600.0));
                sourceApps.Add(app);
            }
        }
        
        // Add test traffic for visualization
        CreateTestTrafficForVisualization();
        
    } else {
        // Normal speed traffic for realistic simulation
        for (uint32_t i = 0; i < coreNodes.GetN(); ++i) {
            for (uint32_t j = 0; j < accessNodes.GetN(); j += 10) {
                Ptr<Node> accessNode = accessNodes.Get(j);
                Ptr<Ipv4> ipv4 = accessNode->GetObject<Ipv4>();
                Ipv4Address addr = ipv4->GetAddress(1, 0).GetLocal();
                
                UdpEchoClientHelper echoClient(addr, port);
                echoClient.SetAttribute("MaxPackets", UintegerValue(50));
                echoClient.SetAttribute("Interval", TimeValue(Seconds(2.0)));
                echoClient.SetAttribute("PacketSize", UintegerValue(512));
                
                ApplicationContainer app = echoClient.Install(coreNodes.Get(i));
                app.Start(Seconds(2.0 + i * 0.1));
                app.Stop(Seconds(600.0));
                sourceApps.Add(app);
            }
        }
    }
    
    std::cout << "Applications setup complete" << std::endl;
}

void RuralNetworkSimulation::CreateTestTrafficForVisualization()
{
    std::cout << "Creating additional test traffic for NetAnim visualization..." << std::endl;
    
    // Super slow test traffic between specific nodes for clear visibility
    uint16_t testPort = 9999;
    
    // Test server on access node 0
    UdpEchoServerHelper testServer(testPort);
    ApplicationContainer testSinkApp = testServer.Install(accessNodes.Get(0));
    testSinkApp.Start(Seconds(90.0));
    testSinkApp.Stop(Seconds(400.0));
    
    // Test client on core node 0 - very slow traffic
    Ptr<Node> testTargetNode = accessNodes.Get(0);
    Ptr<Ipv4> testIpv4 = testTargetNode->GetObject<Ipv4>();
    Ipv4Address testAddr = testIpv4->GetAddress(1, 0).GetLocal();
    
    UdpEchoClientHelper testClient(testAddr, testPort);
    testClient.SetAttribute("MaxPackets", UintegerValue(20));
    testClient.SetAttribute("Interval", TimeValue(Seconds(8.0))); // 1 packet every 8 seconds
    testClient.SetAttribute("PacketSize", UintegerValue(128));
    
    ApplicationContainer testClientApp = testClient.Install(coreNodes.Get(0));
    testClientApp.Start(Seconds(100.0));
    testClientApp.Stop(Seconds(350.0));
    
    std::cout << "Test traffic: Core0 → Access0 every 8 seconds for clear packet visibility" << std::endl;
}

void RuralNetworkSimulation::ScheduleGradualFaultPatterns()
{
    std::cout << "Scheduling realistic gradual fault patterns..." << std::endl;
    
    // TC-01: Realistic Fiber Cut Patterns with gradual degradation
    CreateRealisticFiberCutPattern(5, 20, Seconds(100.0));   // Starts degrading at 100s
    CreateRealisticFiberCutPattern(0, 1, Seconds(200.0));    // Starts degrading at 200s
    CreateRealisticFiberCutPattern(10, 25, Seconds(350.0));  // Starts degrading at 350s
    
    // TC-02: Realistic Power Fluctuation Patterns with gradual degradation
    CreateRealisticPowerFluctuationPattern(25, Seconds(150.0));  // Starts degrading at 150s
    CreateRealisticPowerFluctuationPattern(15, Seconds(280.0));  // Starts degrading at 280s
    CreateRealisticPowerFluctuationPattern(35, Seconds(400.0));  // Starts degrading at 400s
    
    std::cout << "Scheduled " << gradualFaults.size() << " gradual fault patterns" << std::endl;
}

void RuralNetworkSimulation::CreateRealisticFiberCutPattern(uint32_t nodeA, uint32_t nodeB, Time startTime)
{
    // Create gradual degradation pattern for fiber cut
    GradualFaultPattern pattern;
    pattern.targetNode = nodeA;
    pattern.connectedNode = nodeB;
    pattern.faultType = "fiber_cut";
    pattern.startDegradation = startTime;
    pattern.faultOccurrence = startTime + Seconds(60.0);   // Fault occurs 1 minute after degradation starts
    pattern.faultDuration = Seconds(180.0);               // Fault lasts 3 minutes
    pattern.recoveryComplete = pattern.faultOccurrence + pattern.faultDuration + Seconds(120.0); // 2 min recovery
    pattern.degradationRate = 0.8;   // 80% degradation by fault time
    pattern.recoveryRate = 0.7;      // 70% recovery rate
    pattern.severity = 1.0;          // Complete failure at peak
    pattern.isActive = true;
    pattern.currentSeverity = 0.0;
    
    gradualFaults.push_back(pattern);
    
    // Also create pattern for connected node (nodeB)
    pattern.targetNode = nodeB;
    pattern.connectedNode = nodeA;
    pattern.severity = 0.6;  // Connected node less affected
    gradualFaults.push_back(pattern);
    
    std::cout << "Created fiber cut pattern: nodes " << nodeA << "-" << nodeB 
              << " starting at " << startTime.GetSeconds() << "s" << std::endl;
}

void RuralNetworkSimulation::CreateRealisticPowerFluctuationPattern(uint32_t nodeId, Time startTime)
{
    // Create gradual power degradation pattern
    GradualFaultPattern pattern;
    pattern.targetNode = nodeId;
    pattern.connectedNode = 0;  // Not applicable for power issues
    pattern.faultType = "power_fluctuation";
    pattern.startDegradation = startTime;
    pattern.faultOccurrence = startTime + Seconds(90.0);   // Fault occurs 1.5 minutes after degradation
    pattern.faultDuration = Seconds(120.0);               // Fault lasts 2 minutes
    pattern.recoveryComplete = pattern.faultOccurrence + pattern.faultDuration + Seconds(150.0); // 2.5 min recovery
    pattern.degradationRate = 0.6;   // 60% degradation by fault time
    pattern.recoveryRate = 0.8;      // 80% recovery rate
    pattern.severity = 0.7;          // 70% severity at peak
    pattern.isActive = true;
    pattern.currentSeverity = 0.0;
    
    gradualFaults.push_back(pattern);
    
    std::cout << "Created power fluctuation pattern: node " << nodeId 
              << " starting at " << startTime.GetSeconds() << "s" << std::endl;
}

void RuralNetworkSimulation::UpdateFaultProgression()
{
    Time currentTime = Simulator::Now();
    
    for (auto& fault : gradualFaults) {
        if (!fault.isActive) continue;
        
        // Calculate current severity based on timeline
        if (currentTime < fault.startDegradation) {
            fault.currentSeverity = 0.0;  // No degradation yet
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
    }
}

double RuralNetworkSimulation::CalculateNodeDegradation(uint32_t nodeId, const std::string& metric)
{
    double maxDegradation = 0.0;
    
    for (const auto& fault : gradualFaults) {
        if (fault.targetNode == nodeId && fault.isActive) {
            double degradation = fault.currentSeverity;
            
            if (fault.faultType == "fiber_cut") {
                if (metric == "throughput") degradation *= 0.9;
                else if (metric == "latency") degradation *= 0.8;
                else if (metric == "packet_loss") degradation *= 1.0;
                else if (metric == "operational") degradation *= 1.0;
            }
            else if (fault.faultType == "power_fluctuation") {
                if (metric == "voltage") degradation *= 1.0;
                else if (metric == "throughput") degradation *= 0.4;
                else if (metric == "power_stability") degradation *= 0.9;
            }
            
            maxDegradation = std::max(maxDegradation, degradation);
        }
    }
    
    return maxDegradation;
}

void RuralNetworkSimulation::CollectHighFrequencyMetrics()
{
    // Update fault progression
    UpdateFaultProgression();
    
    // Collect metrics for all nodes
    for (uint32_t i = 0; i < allNodes.GetN(); ++i) {
        NodeMetrics metrics = GetEnhancedNodeMetrics(i);
        
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
                   << metrics.faultSeverity << "\n";
    }
    
    metricsFile.flush();
    
    // Schedule next collection
    if (Simulator::Now().GetSeconds() < 590.0) {
        Simulator::Schedule(dataCollectionInterval, &RuralNetworkSimulation::CollectHighFrequencyMetrics, this);
    }
}

RuralNetworkSimulation::NodeMetrics RuralNetworkSimulation::GetEnhancedNodeMetrics(uint32_t nodeId)
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
    
    // Get degradation factors for this node
    double throughputDegradation = CalculateNodeDegradation(nodeId, "throughput");
    double latencyDegradation = CalculateNodeDegradation(nodeId, "latency");
    double packetLossDegradation = CalculateNodeDegradation(nodeId, "packet_loss");
    double voltageDegradation = CalculateNodeDegradation(nodeId, "voltage");
    double operationalDegradation = CalculateNodeDegradation(nodeId, "operational");
    
    // Store degradation and severity levels
    metrics.degradationLevel = std::max({throughputDegradation, latencyDegradation, voltageDegradation});
    metrics.faultSeverity = operationalDegradation;
    
    // Generate realistic base metrics with random variation
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
    
    // Operational status (binary but based on degradation threshold)
    metrics.isOperational = operationalDegradation < 0.8;  // Fails when 80% degraded
    
    // Ensure realistic bounds
    metrics.throughputMbps = std::max(0.0, metrics.throughputMbps);
    metrics.latencyMs = std::max(1.0, metrics.latencyMs);
    metrics.packetLossRate = std::min(1.0, std::max(0.0, metrics.packetLossRate));
    metrics.voltageLevel = std::max(100.0, std::min(300.0, metrics.voltageLevel));
    metrics.powerStability = std::max(0.1, std::min(1.0, metrics.powerStability));
    
    // Other standard metrics
    metrics.jitterMs = metrics.latencyMs * 0.1 + (rand() % 5);
    metrics.signalStrengthDbm = -60.0 - (rand() % 30);
    metrics.cpuUsage = 30.0 + (rand() % 50);
    metrics.memoryUsage = 40.0 + (rand() % 40);
    metrics.bufferOccupancy = 20.0 + (rand() % 60);
    metrics.neighborCount = metrics.activeLinks;
    metrics.linkUtilization = 30.0 + (rand() % 50);
    metrics.criticalServiceLoad = 10.0 + (rand() % 30);
    metrics.normalServiceLoad = 40.0 + (rand() % 40);
    metrics.energyLevel = 100.0 - (Simulator::Now().GetSeconds() / 600.0) * 20.0; // Gradual energy decline
    
    return metrics;
}

void RuralNetworkSimulation::WriteTopologyInfo()
{
    topologyFile << "{\n  \"network_topology\": {\n";
    topologyFile << "    \"total_nodes\": " << allNodes.GetN() << ",\n";
    topologyFile << "    \"core_layer\": {\n";
    topologyFile << "      \"node_count\": " << coreNodes.GetN() << ",\n";
    topologyFile << "      \"node_ids\": [";
    for (uint32_t i = 0; i < coreNodes.GetN(); ++i) {
        topologyFile << i;
        if (i < coreNodes.GetN() - 1) topologyFile << ", ";
    }
    topologyFile << "]\n    },\n";
    
    topologyFile << "    \"distribution_layer\": {\n";
    topologyFile << "      \"node_count\": " << distributionNodes.GetN() << ",\n";
    topologyFile << "      \"node_ids\": [";
    for (uint32_t i = 0; i < distributionNodes.GetN(); ++i) {
        topologyFile << (i + 5);
        if (i < distributionNodes.GetN() - 1) topologyFile << ", ";
    }
    topologyFile << "]\n    },\n";
    
    topologyFile << "    \"access_layer\": {\n";
    topologyFile << "      \"node_count\": " << accessNodes.GetN() << ",\n";
    topologyFile << "      \"node_ids\": [";
    for (uint32_t i = 0; i < accessNodes.GetN(); ++i) {
        topologyFile << (i + 20);
        if (i < accessNodes.GetN() - 1) topologyFile << ", ";
    }
    topologyFile << "]\n    }\n";
    topologyFile << "  }\n}\n";
    
    topologyFile.close();
}

void RuralNetworkSimulation::StartSocketServer()
{
    serverSocket = socket(AF_INET, SOCK_STREAM, 0);
    if (serverSocket < 0) {
        NS_LOG_ERROR("Socket creation failed");
        return;
    }
    
    int opt = 1;
    if (setsockopt(serverSocket, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt))) {
        NS_LOG_ERROR("setsockopt failed");
        close(serverSocket);
        return;
    }
    
    struct sockaddr_in serverAddr;
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_addr.s_addr = INADDR_ANY;
    serverAddr.sin_port = htons(8888);
    
    if (bind(serverSocket, (struct sockaddr*)&serverAddr, sizeof(serverAddr)) < 0) {
        NS_LOG_ERROR("Socket bind failed");
        close(serverSocket);
        return;
    }
    
    if (listen(serverSocket, 5) < 0) {
        NS_LOG_ERROR("Socket listen failed");
        close(serverSocket);
        return;
    }
    
    NS_LOG_INFO("Socket server listening on port 8888");
}

void RuralNetworkSimulation::HandleSocketConnection()
{
    // Socket handling for Python integration
}

void RuralNetworkSimulation::ProcessCommand(const std::string& command)
{
    std::cout << "Received command: " << command << std::endl;
}

void RuralNetworkSimulation::SetupMetricsCollection()
{
    flowMonitor = flowHelper.InstallAll();
    // Start high-frequency collection immediately
    Simulator::Schedule(Seconds(10.0), &RuralNetworkSimulation::CollectHighFrequencyMetrics, this);
    std::cout << "High-frequency metrics collection setup complete (every " 
              << dataCollectionInterval.GetSeconds() << "s)" << std::endl;
}

void RuralNetworkSimulation::Run()
{
    std::cout << "========================================" << std::endl;
    std::cout << "  Enhanced Rural 50-Node Network       " << std::endl;
    std::cout << "  With Gradual Fault Patterns          " << std::endl;
    
    if (useVisualizationSpeeds) {
        std::cout << "  VISUALIZATION MODE: Slow speeds      " << std::endl;
    } else {
        std::cout << "  PERFORMANCE MODE: Realistic speeds   " << std::endl;
    }
    
    std::cout << "========================================" << std::endl;
    
    std::cout << "Setting up 50-node rural network..." << std::endl;
    SetupTopology();
    SetupApplications();
    SetupMetricsCollection();
    
    std::cout << "Scheduling gradual fault patterns..." << std::endl;
    ScheduleGradualFaultPatterns();
    
    std::cout << "Starting socket server..." << std::endl;
    StartSocketServer();
    
    // Enhanced NetAnim configuration for packet visibility
    AnimationInterface anim("rural-network-animation.xml");
    
    if (useVisualizationSpeeds) {
        // Optimized settings for packet visibility
        anim.SetMaxPktsPerTraceFile(20000);         // Reduced for performance
        anim.EnablePacketMetadata(true);            // Show packet details
        anim.SetMobilityPollInterval(Seconds(2));   // More frequent updates
        anim.SetStartTime(Seconds(90));             // Start just before test traffic
        anim.SetStopTime(Seconds(400));             // Focus on fault period
    } else {
        // Standard settings for data generation
        anim.SetMaxPktsPerTraceFile(100000);
        anim.EnablePacketMetadata(true);
        anim.SetMobilityPollInterval(Seconds(5));
        anim.SetStartTime(Seconds(50));
        anim.SetStopTime(Seconds(350));
    }
    
    // Enhanced node visualization
    for (uint32_t i = 0; i < allNodes.GetN(); ++i) {
        std::string nodeType;
        std::string nodeDesc;
        
        if (i < 5) {
            nodeType = "Core";
            nodeDesc = "C" + std::to_string(i);
            anim.UpdateNodeColor(allNodes.Get(i), 255, 50, 50);     // Bright red
            anim.UpdateNodeSize(allNodes.Get(i), 2.0, 2.0);        // Larger core nodes
        } else if (i < 20) {
            nodeType = "Dist";
            nodeDesc = "D" + std::to_string(i-5);
            anim.UpdateNodeColor(allNodes.Get(i), 50, 255, 50);     // Bright green
            anim.UpdateNodeSize(allNodes.Get(i), 1.5, 1.5);        // Medium nodes
        } else {
            nodeType = "Access";
            nodeDesc = "A" + std::to_string(i-20);
            anim.UpdateNodeColor(allNodes.Get(i), 50, 50, 255);     // Bright blue
            anim.UpdateNodeSize(allNodes.Get(i), 1.0, 1.0);        // Smaller nodes
        }
        
        anim.UpdateNodeDescription(allNodes.Get(i), nodeDesc);
    }
    
    std::cout << "========================================" << std::endl;
    std::cout << "Starting 10-minute simulation..." << std::endl;
    std::cout << "High-frequency data collection active" << std::endl;
    
    if (useVisualizationSpeeds) {
        std::cout << "NetAnim: Slow packet flow for visibility" << std::endl;
        std::cout << "In NetAnim: Set Update Rate to SLOWEST" << std::endl;
    }
    
    std::cout << "========================================" << std::endl;
    
    // Schedule progress updates
    for (int i = 1; i <= 10; ++i) {
        Simulator::Schedule(Seconds(i * 60.0), &PrintProgress, i);
    }
    
    Simulator::Stop(Seconds(600.0));
    Simulator::Run();
    
    std::cout << "========================================" << std::endl;
    std::cout << "Enhanced simulation completed!" << std::endl;
    std::cout << "Files generated:" << std::endl;
    std::cout << "- rural_network_metrics.csv (enhanced data)" << std::endl;
    std::cout << "- rural-network-animation.xml (visualization)" << std::endl;
    std::cout << "- network_topology.json (topology info)" << std::endl;
    std::cout << "- rural-network-flowmon.xml (flow analysis)" << std::endl;
    std::cout << "========================================" << std::endl;
    
    if (flowMonitor) {
        flowMonitor->SerializeToXmlFile("rural-network-flowmon.xml", true, true);
    }
    
    Simulator::Destroy();
    
    metricsFile.close();
    simulationRunning = false;
    
    if (serverSocket >= 0) {
        close(serverSocket);
    }
}

int main(int argc, char *argv[])
{
    CommandLine cmd;
    cmd.Parse(argc, argv);
    
    LogComponentEnable("RuralSelfHealingNetwork", LOG_LEVEL_INFO);
    
    RngSeedManager::SetSeed(12345);
    
    RuralNetworkSimulation simulation;
    simulation.Run();
    
    return 0;
}

