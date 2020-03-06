from gns3fy import Gns3Connector, Project, Node, Link
import json
from json import dumps
import yaml
import time

global CONFIG
global server
global projectID

def getVersion(server):
    print(server.get_version())
    #exit(1)

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
    projectID = projectObj.project_id
    print("Project " + projectObj.name + " created. ID: " + projectObj.project_id + "...", end="")
    return projectID

def deleteProject(id):
    server = Gns3Connector(url="http://"+CONFIG["gns3_server"]+":"+CONFIG["gns3_port"])
    server.delete_project(id)

def createNodes(server, projectID):
    nodeDict = dict()
    for nodes in CONFIG["nodes"]:
        node = Node(project_id=projectID, connector=server, template=nodes["appliance_name"], name=nodes["node_name"], x=nodes["x"], y=nodes["y"])
        node.create()
        nodeDict.update({node.name : node.node_id})
    
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


if __name__ == "__main__":
    ### Read configuration file
    with open("config.yml") as config_file:
        CONFIG = yaml.full_load(config_file)
      
    ### Set connectivity and get the server version
    server = Gns3Connector(url="http://"+CONFIG["gns3_server"]+":"+CONFIG["gns3_port"]) 
    getVersion(server)
    
    ### List all created projects
    #listProject(server)

    ### Create project and get its ID
    print("Creating GNS3 project...", end="")
    projectID = createProject(server, CONFIG["project_name"])
    print("OK")
    time.sleep(1)

    ### Create nodes
    print("Creating nodes...", end="")
    nodeDict = createNodes(server, projectID)
    print("OK")
    time.sleep(1)

    ### Create links
    print("Creating links...", end="")
    createLinks(server, projectID, nodeDict)
    print("OK")
    time.sleep(1)