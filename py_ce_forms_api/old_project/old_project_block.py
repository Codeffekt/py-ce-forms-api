class OldProjectBlock:
    """
    Utility class to retrieve forms related to a project
    """
    
    def __init__(self, block):
        self.block = block
    
    def id(self) -> str:
        return self.block["id"]
    
    def ref(self) -> str:
        return self.block["ref"]
    
    def root(self) -> str:
        return self.block["root"]