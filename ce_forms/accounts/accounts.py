from ..api.client import APIClient
from ..query.forms_query import FormsQuery

class Accounts():
    """
    An utility class to retrieve accounts informations.
    """
    
    root = "forms-account"
    
    def __init__(self, client: APIClient) -> None:
        self.client = client
    
    def self(self):
        pass
    
    def get_members(self):
        pass
    
    def get_account_from_login(self, login: str):
        return FormsQuery(self.client).with_root(self.root).where("login", login).with_limit(1)
    
    