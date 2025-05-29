/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Rural 50-Node Self-Healing Network Simulation
 * SIMPLIFIED VERSION - Just inject faults, let Monitor Agent detect
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

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("RuralSelfHealingNetwork");

void PrintProgress(int minute)
{
    std::cout << "[" << minute << "/10] Simulation progress: " << minute*10 << "% complete" << std::endl;
}

// Simple structures for fault injection
struct FaultInjection {
    uint32_t nodeA, nodeB;
    std::string faultType;
    Time injectionTime;
    Time duration;
    double severity;
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
    
    // Fault injection
    std::vector<FaultInjection> scheduledFaults;
    
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
    
    // Fault injection methods
    void ScheduleFaultInjections();
    void InjectFiberCut(uint32_t nodeA, uint32_t nodeB);
    void InjectPowerFluctuation(uint32_t nodeId, double severity);
    void RestoreConnection(uint32_t nodeA, uint32_t nodeB);
    void RestorePowerStability(uint32_t nodeId);
    
    // Data collection
    void CollectMetrics();
    void WriteTopologyInfo();
    
    // Socket server
    void StartSocketServer();
    void HandleSocketConnection();
    void ProcessCommand(const std::string& command);
    
    // Metrics generation
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
    };
    
    NodeMetrics GetNodeMetrics(uint32_t nodeId);
};

RuralNetworkSimulation::RuralNetworkSimulation() : simulationRunning(true)
{
    // Open output files
    metricsFile.open("rural_network_metrics.csv");
    metricsFile << "Time,NodeId,NodeType,Throughput_Mbps,Latency_ms,PacketLoss_Rate,Jitter_ms,"
                << "SignalStrength_dBm,CPU_Usage,Memory_Usage,Buffer_Occupancy,Active_Links,"
                << "Neighbor_Count,Link_Utilization,Critical_Load,Normal_Load,Energy_Level,"
                << "X_Position,Y_Position,Z_Position,Operational_Status,"
                << "Voltage_Level,Power_Stability\n";
    
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
    
    // Install Internet stack with routing (moved to SetupRouting)
    SetupRouting();  // This now handles both stack installation and routing
    SetupEnergyModel();
    WriteTopologyInfo();
}

void RuralNetworkSimulation::SetupCoreLayer()
{
    // High-capacity core network
    p2pHelper.SetDeviceAttribute("DataRate", StringValue("1Gbps"));
    p2pHelper.SetChannelAttribute("Delay", StringValue("2ms"));
    
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
    // Medium-capacity distribution network
    p2pHelper.SetDeviceAttribute("DataRate", StringValue("100Mbps"));
    p2pHelper.SetChannelAttribute("Delay", StringValue("10ms"));
    
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
    // Connect access to distribution
    p2pHelper.SetDeviceAttribute("DataRate", StringValue("50Mbps"));
    p2pHelper.SetChannelAttribute("Delay", StringValue("5ms"));
    
    // Create separate container for access-to-distribution links
    NetDeviceContainer accessToDistLinks;
    
    for (uint32_t i = 0; i < accessNodes.GetN(); ++i) {
        uint32_t distIndex = i % distributionNodes.GetN();
        NetDeviceContainer link = p2pHelper.Install(accessNodes.Get(i), distributionNodes.Get(distIndex));
        accessToDistLinks.Add(link);  // Use separate container
        
        uint32_t accessNodeId = i + 20;
        uint32_t distNodeId = distIndex + 5;
        linkMap[std::make_pair(std::min(accessNodeId, distNodeId), std::max(accessNodeId, distNodeId))] = link;
    }
    
    std::cout << "Layer connectivity established" << std::endl;
}

void RuralNetworkSimulation::SetupRouting()
{
    NS_LOG_FUNCTION(this);
    
    // IMPORTANT: Set up NixVector routing BEFORE installing Internet stack
    Ipv4NixVectorHelper nixRouting;
    stack.SetRoutingHelper(nixRouting);  // Must be called before Install()
    
    // Now install Internet stack with NixVector routing
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
    
    // CORRECTED: Only install WiFi energy model on WiFi devices, not P2P devices
    WifiRadioEnergyModelHelper radioEnergyHelper;
    radioEnergyHelper.Set("TxCurrentA", DoubleValue(0.0174));
    radioEnergyHelper.Set("RxCurrentA", DoubleValue(0.0197));
    
    // Create container with ONLY WiFi devices (first 30 devices in accessDevices)
    NetDeviceContainer wifiDevicesOnly;
    for (uint32_t i = 0; i < accessNodes.GetN(); ++i) {
        wifiDevicesOnly.Add(accessDevices.Get(i));  // Only first 30 devices are WiFi
    }
    
    // Create energy source container for access nodes only
    energy::EnergySourceContainer accessSources;
    for (uint32_t i = 0; i < accessNodes.GetN(); ++i) {
        accessSources.Add(sources.Get(i + 20));  // Access nodes start at index 20
    }
    
    // Install WiFi energy model on WiFi devices only
    radioEnergyHelper.Install(wifiDevicesOnly, accessSources);
    
    std::cout << "Energy model setup complete" << std::endl;
}

void RuralNetworkSimulation::SetupApplications()
{
    // Simple traffic generation
    uint16_t port = 8080;
    
    PacketSinkHelper packetSinkHelper("ns3::UdpSocketFactory", InetSocketAddress(Ipv4Address::GetAny(), port));
    sinkApps = packetSinkHelper.Install(accessNodes);
    sinkApps.Start(Seconds(1.0));
    sinkApps.Stop(Seconds(600.0));
    
    for (uint32_t i = 0; i < coreNodes.GetN(); ++i) {
        for (uint32_t j = 0; j < accessNodes.GetN(); j += 5) {
            Ptr<Node> accessNode = accessNodes.Get(j);
            Ptr<Ipv4> ipv4 = accessNode->GetObject<Ipv4>();
            Ipv4Address addr = ipv4->GetAddress(1, 0).GetLocal();
            
            UdpEchoClientHelper echoClient(addr, port);
            echoClient.SetAttribute("MaxPackets", UintegerValue(1000));
            echoClient.SetAttribute("Interval", TimeValue(Seconds(0.1)));
            echoClient.SetAttribute("PacketSize", UintegerValue(1024));
            
            ApplicationContainer app = echoClient.Install(coreNodes.Get(i));
            app.Start(Seconds(2.0 + i * 0.1));
            app.Stop(Seconds(600.0));
            sourceApps.Add(app);
        }
    }
    
    std::cout << "Applications setup complete" << std::endl;
}

void RuralNetworkSimulation::ScheduleFaultInjections()
{
    // TC-01: Fiber Cut Injections (SILENT - just inject)
    scheduledFaults.push_back({5, 20, "fiber_cut", Seconds(120.0), Seconds(300.0), 1.0});
    scheduledFaults.push_back({0, 1, "fiber_cut", Seconds(240.0), Seconds(300.0), 1.0});
    scheduledFaults.push_back({10, 25, "fiber_cut", Seconds(360.0), Seconds(300.0), 1.0});
    
    // TC-02: Power Fluctuation Injections (SILENT - just inject)
    scheduledFaults.push_back({25, 0, "power_fluctuation", Seconds(180.0), Seconds(120.0), 0.7});
    scheduledFaults.push_back({15, 0, "power_fluctuation", Seconds(300.0), Seconds(180.0), 0.8});
    scheduledFaults.push_back({35, 0, "power_fluctuation", Seconds(420.0), Seconds(90.0), 0.6});
    
    // Schedule all fault injections
    for (const auto& fault : scheduledFaults) {
        if (fault.faultType == "fiber_cut") {
            Simulator::Schedule(fault.injectionTime, &RuralNetworkSimulation::InjectFiberCut, 
                               this, fault.nodeA, fault.nodeB);
            Simulator::Schedule(fault.injectionTime + fault.duration, 
                               &RuralNetworkSimulation::RestoreConnection, 
                               this, fault.nodeA, fault.nodeB);
        } else if (fault.faultType == "power_fluctuation") {
            Simulator::Schedule(fault.injectionTime, &RuralNetworkSimulation::InjectPowerFluctuation, 
                               this, fault.nodeA, fault.severity);
            Simulator::Schedule(fault.injectionTime + fault.duration, 
                               &RuralNetworkSimulation::RestorePowerStability, 
                               this, fault.nodeA);
        }
    }
    
    std::cout << "Scheduled " << scheduledFaults.size() << " fault injections" << std::endl;
}

void RuralNetworkSimulation::InjectFiberCut(uint32_t nodeA, uint32_t nodeB)
{
    NS_LOG_INFO("SILENT: Injecting fiber cut between nodes " << nodeA << " and " << nodeB);
    // Effect is handled in GetNodeMetrics() - Monitor Agent will detect through metrics
}

void RuralNetworkSimulation::InjectPowerFluctuation(uint32_t nodeId, double severity)
{
    NS_LOG_INFO("SILENT: Injecting power fluctuation on node " << nodeId << " severity " << severity);
    // Effect is handled in GetNodeMetrics() - Monitor Agent will detect through metrics
}

void RuralNetworkSimulation::RestoreConnection(uint32_t nodeA, uint32_t nodeB)
{
    NS_LOG_INFO("SILENT: Restoring connection between nodes " << nodeA << " and " << nodeB);
    // Effect is handled in GetNodeMetrics() - Monitor Agent will detect restoration
}

void RuralNetworkSimulation::RestorePowerStability(uint32_t nodeId)
{
    NS_LOG_INFO("SILENT: Restoring power stability on node " << nodeId);
    // Effect is handled in GetNodeMetrics() - Monitor Agent will detect restoration
}

void RuralNetworkSimulation::CollectMetrics()
{
    for (uint32_t i = 0; i < allNodes.GetN(); ++i) {
        NodeMetrics metrics = GetNodeMetrics(i);
        
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
                   << metrics.powerStability << "\n";
    }
    
    metricsFile.flush();
    
    if (Simulator::Now().GetSeconds() < 590.0) {
        Simulator::Schedule(Seconds(30.0), &RuralNetworkSimulation::CollectMetrics, this);
    }
}

RuralNetworkSimulation::NodeMetrics RuralNetworkSimulation::GetNodeMetrics(uint32_t nodeId)
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
    
    Ptr<energy::EnergySource> energySource = node->GetObject<energy::EnergySource>();
    if (energySource) {
        metrics.energyLevel = energySource->GetRemainingEnergy() / energySource->GetInitialEnergy() * 100.0;
    } else {
        metrics.energyLevel = 100.0;
    }
    
    // Check for active faults
    bool hasFailure = false;
    
    for (const auto& fault : scheduledFaults) {
        if (fault.faultType == "fiber_cut" && 
            (fault.nodeA == nodeId || fault.nodeB == nodeId) &&
            Simulator::Now() > fault.injectionTime && 
            Simulator::Now() < fault.injectionTime + fault.duration) {
            hasFailure = true;
            break;
        } else if (fault.faultType == "power_fluctuation" && 
                   fault.nodeA == nodeId &&
                   Simulator::Now() > fault.injectionTime && 
                   Simulator::Now() < fault.injectionTime + fault.duration) {
            metrics.voltageLevel = 220.0 * (1.0 - fault.severity * 0.3);
            metrics.powerStability = 0.95 * (1.0 - fault.severity * 0.1);
            hasFailure = true;
            break;
        }
    }
    
    metrics.isOperational = !hasFailure;
    
    // Generate metrics based on node type and status
    if (metrics.isOperational) {
        if (metrics.nodeType == "core") {
            metrics.throughputMbps = 800.0 + (rand() % 200) - 100;
            metrics.latencyMs = 5.0 + (rand() % 10);
            metrics.packetLossRate = 0.001 + (rand() % 10) * 0.0001;
            metrics.activeLinks = 4;
        } else if (metrics.nodeType == "distribution") {
            metrics.throughputMbps = 60.0 + (rand() % 40) - 20;
            metrics.latencyMs = 15.0 + (rand() % 20);
            metrics.packetLossRate = 0.005 + (rand() % 10) * 0.001;
            metrics.activeLinks = 3;
        } else {
            metrics.throughputMbps = 25.0 + (rand() % 30) - 15;
            metrics.latencyMs = 25.0 + (rand() % 35);
            metrics.packetLossRate = 0.01 + (rand() % 20) * 0.001;
            metrics.activeLinks = 1;
        }
        
        metrics.voltageLevel = metrics.voltageLevel > 0 ? metrics.voltageLevel : 220.0 + (rand() % 20) - 10;
        metrics.powerStability = metrics.powerStability > 0 ? metrics.powerStability : 0.95 + (rand() % 10) * 0.001;
        
    } else {
        // Failed node metrics
        metrics.throughputMbps = 0.0;
        metrics.latencyMs = 1000.0;
        metrics.packetLossRate = 1.0;
        metrics.activeLinks = 0;
        metrics.voltageLevel = metrics.voltageLevel > 0 ? metrics.voltageLevel : 180.0;
        metrics.powerStability = metrics.powerStability > 0 ? metrics.powerStability : 0.5;
    }
    
    metrics.jitterMs = metrics.latencyMs * 0.1 + (rand() % 5);
    metrics.signalStrengthDbm = -60.0 - (rand() % 30);
    metrics.cpuUsage = 30.0 + (rand() % 50);
    metrics.memoryUsage = 40.0 + (rand() % 40);
    metrics.bufferOccupancy = 20.0 + (rand() % 60);
    metrics.neighborCount = metrics.activeLinks;
    metrics.linkUtilization = 30.0 + (rand() % 50);
    metrics.criticalServiceLoad = 10.0 + (rand() % 30);
    metrics.normalServiceLoad = 40.0 + (rand() % 40);
    
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
    // Simple socket handling for Python integration
    // Can be enhanced later for TC-05 intent processing
}

void RuralNetworkSimulation::ProcessCommand(const std::string& command)
{
    // Process commands from Python Monitor Agent
    std::cout << "Received command: " << command << std::endl;
}

void RuralNetworkSimulation::SetupMetricsCollection()
{
    flowMonitor = flowHelper.InstallAll();
    Simulator::Schedule(Seconds(30.0), &RuralNetworkSimulation::CollectMetrics, this);
    std::cout << "Metrics collection setup complete" << std::endl;
}

void RuralNetworkSimulation::Run()
{
    std::cout << "========================================" << std::endl;
    std::cout << "  Rural 50-Node Self-Healing Network   " << std::endl;
    std::cout << "========================================" << std::endl;
    
    std::cout << "Setting up 50-node rural network..." << std::endl;
    SetupTopology();
    SetupApplications();
    SetupMetricsCollection();
    
    std::cout << "Scheduling fault injections..." << std::endl;
    ScheduleFaultInjections();
    
    std::cout << "Starting socket server..." << std::endl;
    StartSocketServer();
    
    // Enable NetAnim with better settings
    AnimationInterface anim("rural-network-animation.xml");
    anim.SetMaxPktsPerTraceFile(500000);
    
    // Add node descriptions for better visualization
    for (uint32_t i = 0; i < allNodes.GetN(); ++i) {
        std::string nodeType;
        if (i < 5) nodeType = "Core";
        else if (i < 20) nodeType = "Dist";
        else nodeType = "Access";
        
        anim.UpdateNodeDescription(allNodes.Get(i), nodeType + std::to_string(i));
        
        // Set node colors based on type
        if (i < 5) {
            anim.UpdateNodeColor(allNodes.Get(i), 255, 0, 0); // Red for core
        } else if (i < 20) {
            anim.UpdateNodeColor(allNodes.Get(i), 0, 255, 0); // Green for distribution
        } else {
            anim.UpdateNodeColor(allNodes.Get(i), 0, 0, 255); // Blue for access
        }
    }
    
    std::cout << "========================================" << std::endl;
    std::cout << "Starting 10-minute simulation..." << std::endl;
    std::cout << "Progress will be shown every 60 seconds" << std::endl;
    std::cout << "========================================" << std::endl;
    
    // Schedule progress updates
    for (int i = 1; i <= 10; ++i) {
        Simulator::Schedule(Seconds(i * 60.0), &PrintProgress, i);
    }
    
    Simulator::Stop(Seconds(600.0));
    Simulator::Run();
    
    std::cout << "========================================" << std::endl;
    std::cout << "Simulation completed successfully!" << std::endl;
    std::cout << "Files generated:" << std::endl;
    std::cout << "- rural_network_metrics.csv (network data)" << std::endl;
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
    
    //LogComponentEnable("UdpEchoClientApplication", LOG_LEVEL_INFO);
    //LogComponentEnable("UdpEchoServerApplication", LOG_LEVEL_INFO);
    LogComponentEnable("RuralSelfHealingNetwork", LOG_LEVEL_INFO);
    
    RngSeedManager::SetSeed(12345);
    
    RuralNetworkSimulation simulation;
    simulation.Run();
    
    return 0;
}

