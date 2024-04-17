class Form:
    """
    An utility class to manipulate form properties
    """
    def __init__(self, form) -> None:
        self.form = form
    
    def set_value(self, field: str, value):
        self.form["content"][field]["value"] = value
        return self    
    
    def id(self):
        return self.form["id"]
    
    