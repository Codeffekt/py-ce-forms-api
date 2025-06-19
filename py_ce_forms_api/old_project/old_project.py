from datetime import datetime

class OldProject:
    """
    An utility class to retrieve old deprecated project informations
    """
    
    def __init__(self, form) -> None:
        
        if form is None or form == {}:
            raise TypeError("Invalid form passed, maybe the underlying form was not found")
        
        self.form = form
    
    def __str__(self) -> str:
        modified_at = f'modified at {self.mtime().isoformat(" ", "seconds")}' if self.form.get("mtime") is not None else ''
        return f'Project id:{self.form["id"]} name:{self.form["name"]} {modified_at} created at {self.ctime().isoformat(" ", "seconds")}'
    
    def ctime(self) -> datetime:
        return datetime.fromtimestamp(self.form["ctime"] / 1000)
    
    def mtime(self) -> datetime|None:
        return datetime.fromtimestamp(self.form["mtime"] / 1000) if self.form.get("mtime") is not None else None
        
    
    