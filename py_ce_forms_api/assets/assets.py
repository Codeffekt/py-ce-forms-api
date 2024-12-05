import os
import mimetypes

from ..api.client import APIClient
from ..api.modules import ASSETS_MODULE_NAME
from ..form import FormBlockAssetArray, FormBlock
from .asset_elt import AssetElt

class Assets():
    """
    An utility class to manage assets.
    """    
    
    def __init__(self, client: APIClient) -> None:
        self.client = client
    
    def create_bucket(self, ref: str):
        return self.client.call_module(module_name=ASSETS_MODULE_NAME, func="createBucket", params=[ref, {}])
    
    def create_bucket_assets_array(self, block: FormBlockAssetArray):
        return self.client.call_module(module_name=ASSETS_MODULE_NAME, func="createBucketAssetsArray", params=[
            block.get_form_id(), 
            block.get_field(), 
            {}
        ])
    
    def delete_asset(self, ref: str, id: str):
        return self.client.call_module(module_name=ASSETS_MODULE_NAME, func="deleteAssets", params=[ref, [id]])
    
    def upload_file_to_bucket(self, bucket, file_path: str, mimetype: str = None):
        if mimetype is None:
            mimetype = self._find_mimetype_from_filename(os.path.basename(file_path))
        return self.client.call_upload(bucket_id=bucket['id'], file_path=file_path, mimetype=mimetype)
    
    def upload_file(self, ref: str, file_path: str, mimetype: str = None):
        bucket = self.create_bucket(ref)               
        return self.upload_file_to_bucket(bucket=bucket, file_path=file_path, mimetype=mimetype)
    
    def upload_file_to_asset_array(self, block: FormBlockAssetArray, file_path: str, mimetype: str = None):
        """
        Upload a new asset to the specified asset array block.
        """
        bucket = self.create_bucket_assets_array(block)
        asset = self.upload_file_to_bucket(bucket=bucket, file_path=file_path, mimetype=mimetype)
        return AssetElt(None, asset)
    
    def download_file(self, id: str):
        """
        Download the asset.
        """
        return self.client.call_download(id)
    
    def create_asset(self, block: FormBlock) -> AssetElt:
        if block.is_type_asset() == False:
            raise Exception(f'block {block.get_field()} is not of type asset')
        block_value = block.get_value()
        data = None
        if block_value is not None:
            data = self.download_file(block_value["id"])
        return AssetElt(data, block_value)
    
    def _find_mimetype_from_filename(self, filename: str): 
        mimetype = mimetypes.guess_type(filename)[0]        
        if mimetype is None:            
            return "text/plain"
        return mimetype