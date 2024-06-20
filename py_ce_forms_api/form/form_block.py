import math
from datetime import datetime

class FormBlock:
    """
    An utility class to manipulate form block values
    """
    def __init__(self, form, block) -> None:
        self.form = form
        self.block = block
    
    def get_form(self):
        return self.form
    
    def get_type(self):
        return self.block["type"]
    
    def get_field(self):
        return self.block["field"]
    
    def get_block_attr(self, field: str):
        return self.block[field]
    
    def get_value(self):
        if self.block["value"] is None:
            return None
        if self.block["type"] == "number":
            return self._get_float_value(self.block["value"])
        if self.block["type"] == "boolean":
            return bool(self.block["value"]) if self.block["value"] != "false" else False
        if self.block["type"] == "timestamp":
            num_value = self._get_float_value(self.block["value"])
            if num_value is None or math.isnan(num_value):
                return None
            try:
                return datetime.fromtimestamp(int(num_value) / 1000)
            except ValueError:
                return None
        if self.block["type"] == "coordinates":
            try:
                return map(lambda x: float(x), self.block["value"]) if type(self.block["value"]) == list else None
            except ValueError:
                return None
            
        return self.block["value"]

    def set_value(self, value):
        if value is None:
            self.block["value"] = value
            return
        if self.block["type"] == "timestamp" and type(value) == datetime:
            self.block["value"] = int(value.timestamp())
            return
        self.block["value"] = value

    def _get_float_value(self, value):
        try:
            return float(value)                
        except ValueError:
                return None
                
                
                