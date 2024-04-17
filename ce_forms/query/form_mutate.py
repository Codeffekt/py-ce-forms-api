from ..api.client import APIClient
from ..api.modules import *

class FormMutate():
    """
    An utility class to mutate the forms dataset.
    """
    
    def __init__(self, client: APIClient) -> None:
        self.client = client
        self.module_name = FORMS_MODULE_NAME
        
    def update_single(self, form):
        return self.client.call_mutation({
            "type": "form",
            "op": "update",
            "elts": [form]
        }, self.module_name)