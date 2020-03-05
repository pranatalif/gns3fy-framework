from gns3fy import Gns3Connector, Project, Node, Link
import json
import configparser
import config

SERVER_URL = "http://10.0.0.4:3080"
server = Gns3Connector(url=SERVER_URL)

def getVersion():
    print(server.get_version())

def listProject():
    server = Gns3Connector(url=SERVER_URL)
    print(server.projects_summary())
    #server.delete_project(lab.project_id)

def createProject(projectName):
    lab = Project(name=projectName, connector=server)
    getProject = next((project for project in server.projects_summary(is_print=False) if project[0] == lab.name), "Project not found")
    if getProject[0] == lab.name:
        print("Project name existed, re-creating the project...")
        deleteProject(getProject[1])
    else:
        print("Creating the project...")
    lab.create()
    projectID = lab.project_id
    print("Project " + lab.name + " created. ID: " + lab.project_id)
    return projectID

def deleteProject(id):
    server.delete_project(id)

def createNode(projectID):
    print(server.get_templates())
    for template in server.get_templates():
        if "dock" in template["name"]:
            print(f"Template: {template['name']} -- ID: {template['template_id']}")

    switch = Node(project_id=projectID, connector=server, name='EthSwitch', template='Ethernet switch')
    #switch.create()

if __name__ == '__main__':
    config = configparser.RawConfigParser()
    config.read('config.properties')
    projectName = config.get('Project', 'name')

    ### Check connectivity and get the server version
    getVersion()

    ### List all created projects
    listProject()

    ### Create project and get its ID
    print("Creating GNS3 project")
    projectID = createProject(projectName)

    ### Create node
    print("Creating node")
    createNode(projectID)