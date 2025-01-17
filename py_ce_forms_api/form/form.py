from __future__ import annotations
from datetime import datetime
from .form_block import FormBlock
from .form_block_assoc import FormBlockAssoc
from .form_block_asset_array import FormBlockAssetArray 
from .form_block_factory import FormBlockFactory
class Form:
    """
    An utility class to manipulate form properties
    """
    def __init__(self, form) -> None:                        
        
        if form is None or form == {}:
            raise TypeError("Invalid form passed, maybe the underlying form was not found")
        
        self.form = form
    
    def set_value(self, field: str, value):
        self.get_block(field).set_value(value)
        return self    
    
    def get_value(self, field: str):
        return self.get_block(field).get_value()        
    
    def get_block(self, field: str) -> FormBlock:
        return FormBlock(self, self.form["content"][field])
    
    def get_assoc(self, field: str) -> FormBlockAssoc:
        return FormBlockAssoc(self.get_block(field))
    
    def get_asset_array(self, field: str) -> FormBlockAssetArray:
        return FormBlockFactory.create_asset_array(self.get_block(field))
    
    def get_sub_form(self, field: str) -> Form:
        if self.form.get("fields") is None or self.form["fields"].get(field) is None:
            raise Exception(f"Form {self.id()} has no subform {field}")
        return Form(self.form["fields"][field])
    
    def get_root(self) -> str:
        return self.form["root"]
    
    def get_type(self) -> str:
        return self.form["type"]
    
    def id(self):
        return self.form["id"]
    
    def __str__(self) -> str:        
        modified_at = f'modified at {self.mtime().isoformat(" ", "seconds")}' if self.form.get("mtime") is not None else ''
        return f'Form {self.form["id"]} from root {self.form["root"]} {modified_at} created at {self.ctime().isoformat(" ", "seconds")}'
    
    def ctime(self) -> datetime:
        return datetime.fromtimestamp(self.form["ctime"] / 1000)
    
    def mtime(self) -> datetime|None:
        return datetime.fromtimestamp(self.form["mtime"] / 1000) if self.form.get("mtime") is not None else None
            
    