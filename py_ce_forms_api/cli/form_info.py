from ..form import Form
from ..client import CeFormsClient

class FormInfo():
    """_summary_
    """
    
    def __init__(self, client: CeFormsClient, id: str) -> None:
        self.id = id
        self.client = client
        self.form = Form(self.client.query().call_single(self.id))
    
    def get_summary(self) -> str|None:                            
        return str(self.form)
    
    def get_root(self) -> str|None:
        root = self.client.roots().get_form(self.form.get_root())           
        root_blocks = list(map(lambda b: b.get_field(), root.get_blocks()))
        return '\n'.join([str(root), str(root_blocks)])