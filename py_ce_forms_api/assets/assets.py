import os
import mimetypes
from ..api.client import APIClient
from ..api.modules import ASSETS_MODULE_NAME
from ..form import FormBlockAssetArray

class Assets():
    """
    An utility class to manage assets.
    """    
    
    def __init__(self, client: APIClient) -> None:
        self.client = client
    
    def create_bucket(self, ref: str):
        return self.client.call_module(module_name=ASSETS_MODULE_NAME, func="createBucket", params=[ref, {}])
    
    def delete_asset(self, ref: str, id: str):
        return self.client.call_module(module_name=ASSETS_MODULE_NAME, func="deleteAssets", params=[ref, [id]])
    
    def upload_file_to_bucket(self, bucket_id: str, file_path: str, mimetype = "text/plain"):
        return self.client.call_upload(bucket_id=bucket_id, file_path=file_path, mimetype=mimetype)
    
    def upload_file(self, ref: str, file_path: str, mimetype: str = None):
        bucket = self.create_bucket(ref)
        if mimetype is None:
            mimetype = self._find_mimetype_from_filename(os.path.basename(file_path))          
        return self.upload_file_to_bucket(bucket_id=bucket['id'], file_path=file_path, mimetype=mimetype)
    
    def upload_file_to_asset_array(self, block: FormBlockAssetArray, file_path: str, mimetype: str = None):
        """
        Upload a new asset to the specified asset array block.
        """
        return self.upload_file(block.get_ref(), file_path, mimetype=mimetype)
    
    def download_file(self, id: str):
        """
        Download the asset.
        """
        return self.client.call_download(id)
    
    def _find_mimetype_from_filename(self, filename: str): 
        mimetype = mimetypes.guess_type(filename)[0]        
        if mimetype is None:            
            return "text/plain"
        return mimetype