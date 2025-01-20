import math
from datetime import datetime
from .form_utils import FormUtils

class FormBlock:
    TEXT_TYPE = "text"
    NUMBER_TYPE = "number"
    BOOLEAN_TYPE = "boolean"
    TIMESTAMP_TYPE = "timestamp"
    COORDINATES_TYPE = "coordinates"
    FORM_ARRAY_TYPE = "formArray"
    ASSET_ARRAY_TYPE = "assetArray"
    ASSET_TYPE = "asset"
    
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
    
    def get_field(self) -> str:
        return self.block["field"]
    
    def get_block_attr(self, field: str):
        return self.block[field]
    
    def get_root(self):
        return self.block["root"]
    
    def is_type_asset(self) -> bool:
        return self.get_type() == FormBlock.ASSET_TYPE
    
    def get_value(self):
        if self.block["value"] is None:
            return None
        if self.block["type"] == FormBlock.NUMBER_TYPE:
            return self._get_float_value(self.block["value"])
        if self.block["type"] == FormBlock.BOOLEAN_TYPE:
            return bool(self.block["value"]) if self.block["value"] != "false" else False
        if self.block["type"] == FormBlock.TIMESTAMP_TYPE:
            num_value = self._get_float_value(self.block["value"])
            if num_value is None or math.isnan(num_value):
                return None
            try:
                return datetime.fromtimestamp(int(num_value) / 1000)
            except ValueError:
                return None
        if self.block["type"] == FormBlock.COORDINATES_TYPE:
            try:
                return map(lambda x: float(x), self.block["value"]) if type(self.block["value"]) == list else None
            except ValueError:
                return None
        if self.block["type"] == FormBlock.ASSET_ARRAY_TYPE:
            return FormUtils.eval(self.get_form(), self.block["value"])        
            
        return self.block["value"]

    def set_value(self, value):
        if value is None:
            self.block["value"] = value
            return
        if self.block["type"] == FormBlock.TIMESTAMP_TYPE and type(value) == datetime:
            self.block["value"] = int(value.timestamp())
            return
        self.block["value"] = value

    def _get_float_value(self, value):
        try:
            return float(value)                
        except ValueError:
                return None
                
                
                