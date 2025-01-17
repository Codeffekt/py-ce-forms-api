from ..form.form_block import FormBlock
from datetime import datetime

class Root:
    """
    An utility class to retrieve root informations
    """
    def __init__(self, form) -> None:
        
        if form is None or form == {}:
            raise TypeError("Invalid form passed, maybe the underlying form was not found")
        
        self.form = form
    
    def get_block(self, field: str) -> FormBlock:
        return FormBlock(self, self.form["content"][field])
    
    def get_blocks(self) -> list[FormBlock]:
        return list(map(lambda b: FormBlock(self, b), list(self.form["content"].values())))
    
    def id(self):
        return self.form["id"]
    
    def __str__(self) -> str:        
        modified_at = f'modified at {self.mtime().isoformat(" ", "seconds")}' if self.form.get("mtime") is not None else ''
        return f'Root {self.form["id"]} {modified_at} created at {self.ctime().isoformat(" ", "seconds")}'
    
    def ctime(self) -> datetime:
        return datetime.fromtimestamp(self.form["ctime"] / 1000)
    
    def mtime(self) -> datetime|None:
        return datetime.fromtimestamp(self.form["mtime"] / 1000) if self.form.get("mtime") is not None else None
    
    