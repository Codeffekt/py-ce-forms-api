from ..api.client import APIClient
from ..api.modules import *
from ..form import Form, FormBlock

class FormMutate():
    """
    An utility class to mutate the forms dataset.
    """
    
    def __init__(self, client: APIClient) -> None:
        self.client = client
        self.module_name = FORMS_MODULE_NAME
        
    def update(self, form: Form):
        return self.update_single(form.form)
    
    def delete(self, form: Form):
        return self.delete_single(form)
    
    def update_single(self, form: dict):
        return Form(self.client.call_mutation({
            "type": "form",
            "op": "update",
            "elts": [form]
        }, self.module_name))
    
    def create(self, root: str) -> Form:
        return Form(self.client.call_module(
            func="create",
            params=[root],
            module_name=FORMS_MODULE_NAME))
    
    def create_from_array(self, block: FormBlock) -> Form:
        return Form(self.client.call_mutation({
            "type": "formArray",
            "op": "create",
            "indices": [block.get_form().id()],
            "formArrayField": block.get_field()
        }))
    
    def delete_single(self, form: Form):
        return Form(self.client.call_mutation({
            "type": "form",
            "op": "delete",
            "indices": [form.id()]
        }, self.module_name))
    
    def copy(self, form: Form) -> Form:
        return Form(self.client.call_module(
            func="copy", 
            params=[form.id()],
            module_name=FORMS_MODULE_NAME
        ))