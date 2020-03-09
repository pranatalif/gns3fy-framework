from gns3fy import Gns3Connector, Project, Node, Link
from json import dumps
import yaml
import time
from telnetlib import Telnet
import sys

global CONFIG
global server
global projectObj

def getVersion(server):
    print(str(server.get_version()) + "...", end="")

def listProject(server):
    print(server.projects_summary())

def createProject(server, project):
    projectObj = Project(name=project, connector=server)
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
    server = Gns3Connector(url="http://"+CONFIG["gns3_server"]+":"+CONFIG["gns3_port"])
    server.delete_project(id)

def createNodes(server, projectID):
    nodeDict = dict()
    for nodes in CONFIG["nodes"]:
        node = Node(project_id=projectID, connector=server, template=nodes["appliance_name"], name=nodes["node_name"], x=nodes["x"], y=nodes["y"])
        node.create()
        nodeDict.update({node.name : node.node_id})      
        node.start()

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

    for node in CONFIG["nodes"]:
        if "ip" in node:
            ip = node["ip"]
            gw = node["gw"]
            for node in summary:
                if str(node[2]) == "5000" or str(node[2]) == "None":
                    continue
                else:
                    nodePort = str(node[2])
                    configureIP(ip, netmask, broadcast, gw, nodePort)

def configureIP(ip, netmask, broadcast, gateway, port):
    try:
        telnet = Telnet(CONFIG["gns3_server"], port)
        cmdIP = 'auto "eth0\niface eth0 inet static\naddress '+ip+'\nnetmask '+netmask+'\nbroadcast '+broadcast+'\ngateway '+gateway+'\nup echo nameserver '+gateway+' > /etc/resolv.conf"'
        telnet.write(("echo -e "+cmdIP+" > /etc/network/interfaces\r\n").encode())
        time.sleep(1) # should have wait before 2 commands, otherwise the file not changed.
        telnet.write(b"/etc/init.d/networking restart\r\n")                   
    except:
        print("Unable to connect to Telnet server: ", sys.exc_info()[0])

    telnet.close()
    

if __name__ == "__main__":
    ### Read configuration file
    with open("config.yml") as config_file:
        CONFIG = yaml.full_load(config_file)
      
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
    print("[5/6] Configuring IP...", end="")
    findNodeforIPConf(projectObj)
    print("OK")
    time.sleep(1)