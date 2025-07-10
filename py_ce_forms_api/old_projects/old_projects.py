from ..api.client import APIClient
from ..old_project import OldProject
from ..api.modules import PROJECTS_MODULE_NAME
from ..query import FormsQuery, FormsResIterable

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
    
    def get_all(self) -> list[OldProject]:
        res = self.client.call_module("getAll", [], PROJECTS_MODULE_NAME)
        return [OldProject(form) for form in res]            
    
    def get_project_forms(self, pid: str, field: str):
        query = FormsQuery(self.client).with_module_name(PROJECTS_MODULE_NAME).with_args([pid, field])
        return FormsResIterable(query)
        