from ..api.client import APIClient
from ..root import Root

class Roots():
    """
    An utility class to retrieve forms informations
    """    

    def __init__(self, client: APIClient) -> None:
        self.client = client        
    
    def self(self):
        pass    
            
    def get_form(self, fid: str) -> Root:
        """
        Returns the specified form root.
        """        
        return Root(self.client.call_get_root(fid))
    
    
        