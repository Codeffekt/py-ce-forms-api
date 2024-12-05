class AssetElt():
    """
    Utility class to manage forms asset element
    """
    def __init__(self, data: (bytes|None), block_value) -> None:
        self.data = data
        self.block_value = block_value
    
    def id(self) -> str:
        return self.block_value["id"]
    
    def mimetype(self) -> str:
        return self.block_value["mimetype"]
    
    def name(self) -> str:
        return self.block_value["name"]
    
    def original_name(self) -> str:
        return self.block_value["originalname"]
    
    def get_bytes(self) -> bytes:
        return self.data
    
    def get_value(self):
        return self.block_value
    