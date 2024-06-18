from ..api.client import APIClient
from ..query import FormsQuery
from ..form import Form
from .project import Project
from ..assets import Assets

class Projects():
    """
    An utility class to retrieve projects informations
    """

    root = "forms-project"

    def __init__(self, client: APIClient, assets_module: Assets) -> None:
        self.client = client
        self.assets_module = assets_module
    
    def self(self):
        pass
    
    def get_members(self):
        pass
    
    def upload_file(self, pid: str, file_path: str):
        """
        Upload a new asset to the specified project.
        """        
        project = self.get_project(pid)
        project_assets_ref = project.get_asset_ref()
        return self.assets_module.upload_file(project_assets_ref, file_path)

    
    def get_project(self, pid: str) -> Project:
        """
        Returns the specified project.
        """
        return Project(Form(FormsQuery(self.client).with_root(self.root).call_single(pid)))