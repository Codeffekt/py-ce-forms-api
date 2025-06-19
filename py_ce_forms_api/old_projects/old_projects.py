from ..api.client import APIClient
from ..old_project import OldProject
from ..api.modules import PROJECTS_MODULE_NAME

class OldProjects():
    """
    An utility class to retrieve Old deprecated projects
    """
    
    def __init__(self, client: APIClient) -> None:
        self.client = client
    
    def self(self):
        pass
    
    def get_project(self, pid: str) -> OldProject:
        return OldProject(self.client.call_module("getProject", [pid], PROJECTS_MODULE_NAME))