class FormQueryNode():
    """
    Represents the node part of the form query
    """

    def __init__(self, field: str, root: str, name: str, type: str = "formArray") -> None:
        self.field = field
        self.root = root
        self.name = name
        self.type = type
    
    def asDict(self):
        return {
            "field": self.field,
            "root": self.root,
            "name": self.name,
            "type": self.type
        }
    
