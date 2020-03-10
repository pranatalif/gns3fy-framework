from gns3fy import Gns3Connector, Project, Node, Link
from json import dumps
from telnetlib import Telnet
import yaml
import time
import sys

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
    getProject = next((project for project in server.projects_summary(is_print=False) if project[0] == projectObj.name), "Project not found")
    #print(getProject)
    if getProject[0] == projectObj.name:
        print("Project name existed, re-creating the project...", end="")
        deleteProject(getProject[1])
    #else:
    #    print("Creating the project...", end="")
    projectObj.create()
    print("Project " + projectObj.name + " created. ID: " + projectObj.project_id + "...", end="")
    return projectObj

def deleteProject(id):
    #server = Gns3Connector(url="http://"+CONFIG["gns3_server"]+":"+CONFIG["gns3_port"])
    server.delete_project(id)

def createNodes(server, projectID):
    nodeDict = dict()
    for nodes in CONFIG["nodes"]:
        node = Node(project_id=projectID, connector=server, template=nodes["appliance_name"], name=nodes["node_name"], x=nodes["x"], y=nodes["y"])
        node.create()
        nodeDict.update({node.name : node.node_id})      
        node.start()
        time.sleep(2)

    return nodeDict

def createLinks(server, projectID, nodeDict):  
    for links in CONFIG["links"]:
        if all (key in nodeDict for key in (links["node1"], links["node2"])):
            node1ID=nodeDict[links["node1"]]
            node2ID=nodeDict[links["node2"]]
        else:
            print("Neither node1 or node2 object found. Check the spelling of the nodes name")
            break

        nodeCombination = [dict(node_id=node1ID, adapter_number=0, port_number=links["port_num1"]), dict(node_id=node2ID, adapter_number=0, port_number=links["port_num2"])]
        link = Link(project_id=projectID, connector=server, nodes=nodeCombination)
        link.create()

def findNodeforIPConf(project):
    netmask = "255.255.255.0"
    broadcast = "192.168.122.255"
    summary = project.nodes_summary(is_print=False)
    
    for nodeInConfig in CONFIG["nodes"]:
        if "ip" in nodeInConfig:
            ip = nodeInConfig["ip"]
            gw = nodeInConfig["gw"]
            #print(nodeInConfig["node_name"])
            for nodeInSummary in summary:
                if nodeInConfig["node_name"] in nodeInSummary[0]:
                    telnet = configureIP(ip, netmask, broadcast, gw, nodeInSummary[2])
                    runService(telnet, nodeInConfig["appliance_name"])
                #else:
                 #   print(template[4])


def configureIP(ip, netmask, broadcast, gateway, port):
    try:
        telnet = Telnet(CONFIG["gns3_server"], port)
        cmdIP = 'auto "eth0\niface eth0 inet static\naddress '+ip+'\nnetmask '+netmask+'\nbroadcast '+broadcast+'\ngateway '+gateway+'\nup echo nameserver '+gateway+' > /etc/resolv.conf"'
        telnet.write(("echo -e "+cmdIP+" > /etc/network/interfaces\r\n").encode())
        time.sleep(2) # should have wait before 2 commands, otherwise the file not changed.
        telnet.write(b"/etc/init.d/networking restart\r\n")                   
    except:
        print("Unable to connect to Telnet server: ", sys.exc_info()[0])

    return telnet
    
def runService(telnet, service):
    if service == "Keycloak":
        time.sleep(15)
    else:
        time.sleep(5)

    for commands in COMMAND["commands"]:
        if commands["name"] == service:
            telnet.write(str(commands["workdir"]).encode())
            time.sleep(2)
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
    print("OK")
    time.sleep(1)
    
    ### List all created projects
    #listProject(server)

    ### Create project and get its ID
    print("[2/6] Creating GNS3 project...", end="")
    projectObj = createProject(server, CONFIG["project_name"])
    print("OK")
    time.sleep(1)

    ### Check appliance existance. put all appliance_name from nodes (in config files) in Array and compare with server.template_summary() (optional)

    ### Create nodes
    print("[3/6] Creating nodes...", end="")
    nodeDict = createNodes(server, projectObj.project_id)
    print("OK")
    time.sleep(1)

    ### Create links
    print("[4/6] Creating links...", end="")
    createLinks(server, projectObj.project_id, nodeDict)
    print("OK")
    time.sleep(1)

    ### Set links filter

    ### Configure IP
    print("[5/6] Configuring IP and Running Services...", end="")
    findNodeforIPConf(projectObj)
    print("OK")
    time.sleep(1)

    ### Run services
    #print("[5/6] Run Services...", end="")
    #runService(telnet)
    #print("OK")
    #time.sleep(1)