from ..api.client import APIClient
from ..query import FormsQuery, FormsResIterable, FormMutate
from ..form import Form, FormBlockAssoc

class Forms():
    """
    An utility class to retrieve forms informations
    """    

    def __init__(self, client: APIClient) -> None:
        self.client = client        
    
    def self(self):
        pass    
            
    def get_form(self, fid: str) -> Form:
        """
        Returns the specified form.
        """
        return Form(FormsQuery(self.client).call_single(fid))
    
    def get_form_assoc(self, block: FormBlockAssoc) -> FormsResIterable:        
        return FormsResIterable(FormsQuery(self.client).with_ref(block.get_ref()))        
        