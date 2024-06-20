from ..api.client import APIClient
from ..query import FormsQuery
from .project import Project
from ..form import Form

class Projects():
    """
    An utility class to retrieve projects informations
    """

    root = "forms-project"

    def __init__(self, client: APIClient) -> None:
        self.client = client        
    
    def self(self):
        pass
    
    def get_members(self):
        pass
            
    def get_project(self, pid: str) -> Project:
        """
        Returns the specified project.
        """
        return Project(Form(FormsQuery(self.client).with_root(self.root).call_single(pid)))
        