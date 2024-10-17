from .forms_query import FormsQuery
from .forms_res import FormsRes

class FormsQueryArray(FormsQuery):
    """
    An utility class to retrieve forms from formArray block
    """
    
    def with_array(self, form_id: str, form_field: str):
        self.form_id = form_id
        self.form_field = form_field
        return self
    
    def call(self):                
        return FormsRes(self.client.call_forms_query_array(
            self.form_id, 
            self.form_field, 
            self.call_args + [ self._create_raw_query() ], self.module_name)) 
