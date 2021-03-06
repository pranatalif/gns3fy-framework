from gns3fy import Gns3Connector, Project, Node, Link
from json import dumps
from telnetlib import Telnet
import yaml
import time
import sys
import os
import json

global CONFIG
global COMMAND
global server
global projectObj
global telnet

def getVersion(server):
    print(str(server.get_version()) + "...", end="")

def listProject(server):
    print(server.projects_summary())

def createProject(server, project):
    projectObj = Project(name=project, connector=server)
    #print(projectObj.status)
    # if projectObj.status == "opened":
    #     print("Closing the current project...", end="")
    #     projectObj.close()
    #     print("OK")

    getProject = next((project for project in server.projects_summary(is_print=False) if project[0] == projectObj.name), "Project not found")
    if getProject[0] == projectObj.name:
        print("Project name existed, re-creating the project...", end="")
        deleteProject(getProject[1])
    #else:
    #    print("Creating the project...", end="")
    projectObj.create()
    print("Project " + projectObj.name + " created. ID: " + projectObj.project_id + "...", end="")
    return projectObj

def deleteProject(id):
    server.delete_project(id)

def checkAppliance(server):
    for nodes in CONFIG["nodes"]:
        applianceName = nodes["appliance_name"]
        search = next((appliance for appliance in server.templates_summary(is_print=False) if appliance[0] == applianceName), None)
        if search == None:
            print("Appliance", applianceName, "not found, check your configuration file...!")
            print("exiting the framework...", end="")
            break
        
    print("Checking appliance passed...", end="")

def createNodes(server, projectID):
    nodeDict = dict()
    for nodes in CONFIG["nodes"]:
        node = Node(project_id=projectID, connector=server, template=nodes["appliance_name"], name=nodes["node_name"], x=nodes["x"], y=nodes["y"])
        node.create()
        if nodes["node_type"] == "docker":
            setContainerName(node, server)
        nodeDict.update({node.name : node.node_id})      
        node.start()
        time.sleep(1)

    return nodeDict

def setContainerName(node, projectID):
    cmdSetContainerName = "curl --unix-socket /var/run/docker.sock -X POST http:/v1.39/containers/"+node.properties["container_id"]+"/rename?name="+node.name+"\n"
    os.system(cmdSetContainerName)

def createLinks(server, projectID, nodeDict):
    # filterDict = {}  
    for links in CONFIG["links"]:
        if all (key in nodeDict for key in (links["node1"], links["node2"])):
            node1ID=nodeDict[links["node1"]]
            node2ID=nodeDict[links["node2"]]
        else:
            print("Neither node1 nor node2 object found. Check the spelling of the nodes name!")
            break

        nodeCombination = [dict(node_id=node1ID, adapter_number=0, port_number=links["port_num1"]), dict(node_id=node2ID, adapter_number=0, port_number=links["port_num2"])]
        link = Link(project_id=projectID, connector=server, nodes=nodeCombination)
        link.create()
        # print("id " + link.link_id)
        #link.get()
        # if "filter" in links:
        #     #filter = links["filter"]
        #     print("id " +link.link_id)
        #     #print(links["filter"][2])
        #     # link.filters["freqDrop"] = links["filter"][0]
        #     # link.filters["packetLos"] = links["filter"][1]
        #     # link.filters["latency"] = links["filter"][2]
        #     # link.filters["corrupt"] = links["filter"][3]
        #     filterDict = links["filter"]
        #     print(link.filters)
            
        #     #print(links["filter"], links["node1"], links["node2"])
        # link.filters(links["filter"])
        # #Link(link.link_id, link.filters)
        # # link.create()
        
        
        # # print(link.link_type)
        # # print(link.filters)

def findNodeforIPConf(project):
    netmask = "255.255.255.0"
    broadcast = "192.168.122.255"
    summary = project.nodes_summary(is_print=False)

    for nodeInConfig in CONFIG["nodes"]:
        if nodeInConfig["appliance_name"] == "Test" and nodeInConfig["node_name"] == "Test1":
            input("Press <ENTER> to start perturbation...")

        if "ip" in nodeInConfig:
            ip = nodeInConfig["ip"]
            gw = nodeInConfig["gw"]
            for nodeInSummary in summary:
                if nodeInConfig["node_name"] == nodeInSummary[0]:
                    telnet = configureIP(ip, netmask, broadcast, gw, nodeInSummary[2])
                    runService(telnet, nodeInConfig["node_name"])    

        print("[STATUS]",  nodeInConfig["node_name"], "has started...OK")                

def configureIP(ip, netmask, broadcast, gateway, consolePort):
    try:
        telnet = Telnet(CONFIG["gns3_server"], consolePort)
    except:
        print("Unable to connect to Telnet server: ", sys.exc_info()[0])

    cmdIP = 'auto "eth0\niface eth0 inet static\naddress '+ip+'\nnetmask '+netmask+'\nbroadcast '+broadcast+'\ngateway '+gateway+'\nup echo nameserver '+gateway+' > /etc/resolv.conf"'
    telnet.write(("echo -e "+cmdIP+" > /etc/network/interfaces\r\n").encode())
    time.sleep(2) # should have wait before 2 commands, otherwise the file not changed.
    telnet.write(b"/etc/init.d/networking restart\r\n")
    return telnet
    
### appliance_name in config.yml is assumed as the service name    
def runService(telnet, service):
    for commands in COMMAND["commands"]:
        if commands["name"] in service:
            #if "Hls" in service or "Test" in service:
            telnet.write(str(commands["workdir"]).encode())
            time.sleep(2)
            # if service == "Nginx":
            #     telnet.write(str(commands["command1"]).encode())
            #     time.sleep(2)
            #     telnet.write(str(commands["command2"]).encode())
            
            telnet.write(str(commands["command"]).encode())
    
    telnet.close()

if __name__ == "__main__":
    ### Read configuration file
    with open("config.yml") as config_file:
        CONFIG = yaml.full_load(config_file)

    with open("run-command.yml") as command_file:
        COMMAND = yaml.full_load(command_file)
      
    ### Set connectivity and get the server version
    print("[1/6] Connecting to server...", end="")
    server = Gns3Connector(url="http://"+CONFIG["gns3_server"]+":"+CONFIG["gns3_port"]) 
    getVersion(server)
    time.sleep(0.5)
    print("OK")
    time.sleep(1)
    #input("Press <ENTER> to continue...")
    ### List all created projects
    #listProject(server)

    ### Create project and get its ID
    print("[2/6] Creating GNS3 project...", end="")
    projectObj = createProject(server, CONFIG["project_name"])
    time.sleep(0.5)
    print("OK")
    time.sleep(1)

    ### Check appliance existance
    print("[3/6] Checking appliances...", end="")
    checkAppliance(server)
    time.sleep(0.5)
    print("OK")
    time.sleep(1)

    ### Create nodes
    print("[4/6] Creating nodes...", end="")
    nodeDict = createNodes(server, projectObj.project_id)
    print("OK. You can open the project now...") # Opening the project before nodes creation will dissarange the topology
    #time.sleep(1)

    ### Create links
    print("[5/6] Creating links...", end="")
    createLinks(server, projectObj.project_id, nodeDict)
    print("OK")
    #time.sleep(1)

    ### Set links filter (on progress)

    ### Configure IP
    print("[6/6] Configuring IP and Running Services...")
    findNodeforIPConf(projectObj)
    print("[STATUS] All services have started")
    time.sleep(1)

    ### Run services (called in the findNodeforIPConf() function)
    # print("[X/X] Run Services...", end="")
    # runService(telnet)
    # print("OK")
    # time.sleep(1)