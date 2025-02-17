import os.path
from ..api.client import APIClient
from .asset_elt import AssetElt

class AssetLocalFileElt():
    """
    Utility class to manage local stored assets
    """
    def __init__(self, client: APIClient) -> None:
        self.client = client 
        
        if self.client.get_dir_path() is None:
            raise TypeError("Invalid dir_path None value, you must init the APIClient with dir_path or use CE_FORMS_DIR_PATH env")
        
        if not os.path.isdir(self.client.get_dir_path()):                
            os.mkdir(self.client.get_dir_path())
            
    def save(self, id: str):
        if not self.exists(id):
            data = self._download_file_content(id)
            self._write_file_content(id, data)
            return True
        return False
    
    def load(self, block_value) -> AssetElt:
        if self.exists(block_value['id']):
            return AssetElt(self._get_file_content(block_value['id']), block_value)
        else:
            data = self._download_file_content(id)
            self._write_file_content(block_value['id'], data)
            return AssetElt(data, block_value)
    
    def exists(self, id: str) -> bool:
        return os.path.isfile(self.get_file_path(id))
    
    def get_file_path(self, id: str) -> str:
        return f'{self.client.get_dir_path()}/{id}'
    
    def _get_file_content(self, id: str) -> bytes:
        with open(self.get_file_path(id), "rb") as f:
            return f.read()
        
    def _write_file_content(self, id: str, data: bytes):
        with open(self.get_file_path(id), "wb") as f:
            return f.write(data)
        
    def _download_file_content(self, id: str) -> bytes:
        return self.client.call_download(id)
    