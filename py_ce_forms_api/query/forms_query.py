from ..api.client import APIClient
from ..api.modules import *

class FormsQuery():
    """
    An utility class to query the forms dataset.
    """
    
    def __init__(self, client: APIClient) -> None:
        self.limit = 10
        self.offset = 0
        self.extMode = False
        self.client = client
        self.query_fields = []
        self.module_name = FORMS_MODULE_NAME
        
    def with_root(self, root: str):
        self._add_query_field({
            "field": "root",
            "value": root,
            "onMeta": True
        })
        return self
        
    def with_id(self, id: str):
        self._add_query_field({
            "field": "id",
            "value": id,
            "onMeta": True
        })
        return self
        
    def where(self, field: str, value: str, op = "="):
        self._add_query_field({
            "field": field,
            "value": value,
            "op": op
        })
        return self
    
    def with_sub_forms(self, value: bool = True):
        self.extMode = value
        return self
        
    def with_limit(self, limit: int):
        self.limit = limit
        return self
    
    def with_offset(self, offset: int):
        self.offset = offset
        return self
    
    def with_module_name(self, module_name: str):
        self.module_name = module_name
        return self
    
    def _add_query_field(self, qf):
        self.query_fields.append(qf)
        return self
    
    def call(self):
        return self.client.call_forms_query({
                    "extMode": self.extMode,
                    "limit": self.limit,
                    "offset": self.offset,
                    "queryFields": self.query_fields
                }, self.module_name)
    
    def call_single(self, id: str):
        return self.client.call_form_query(id, {
                    "extMode": self.extMode,
                    "limit": self.limit,
                    "offset": self.offset,
                    "queryFields": self.query_fields
                }, self.module_name)
    
    