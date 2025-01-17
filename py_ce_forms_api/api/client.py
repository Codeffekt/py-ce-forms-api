from io import BufferedReader
import os
import requests
from .bearer_auth import BearerAuth
from .modules import *
from .exceptions import *

class APIClient():
    """
    A low-level client for the CeForms API.    
    
    Example:
    
        >>> import ce_forms
        >>> client = ce_forms.APIClient(base_url='', token='')
        
    Args:
        base_url (str): URL to the CeForms API server.
        token (str): API token provided by a CeForms backend.
    
    """
    
    def __init__(self, base_url=None, token=None):
        super().__init__()
        
        if base_url is None:
            self.base_url = os.environ.get("CE_FORMS_BASE_URL")
        else:     
            self.base_url = base_url
            
        if token is None:
            self.token = os.environ.get("CE_FORMS_TOKEN")
        else:    
            self.token = token            
        
        if self.base_url is None or self.token is None:
            raise TypeError("Invalid base_url or token None value")
        
    def self(self):
        response = requests.get(f'{self.base_url}/self', auth=BearerAuth(self.token))
        return response.json()
    
    def call_module(self, func, params, module_name):
        return self.call(f'Public{module_name}', func_name=func, func_params=params)
    
    def call_forms_query(self, params, module_name = FORMS_MODULE_NAME):        
        return self.call_module(
            func="getFormsQuery",
            params=params,
            module_name=module_name
        )           
    
    def call_forms_root_query(self, params, module_name = FORMS_MODULE_NAME):        
        return self.call_module(
            func="getFormsRootQuery",
            params=params,
            module_name=module_name
        )
    
    def call_get_root(self, params, module_name = FORMS_MODULE_NAME):
        return self.call_module(
            func="getRoot",
            params=params,
            module_name=module_name
        )
    
    def call_form_query(self, id: str, query, module_name = FORMS_MODULE_NAME):
        return self.call_module(
            func="getFormQuery",
            params=[id, query],
            module_name=module_name
        )
    
    def call_forms_query_array(self, id: str, field: str, query, module_name = FORMS_MODULE_NAME):
        return self.call_module(
            func="getFormsQueryArray",
            params=[id, field, query],
            module_name=module_name
        )
    
    def call(self, class_name, func_name, func_params):
        return self._call(self._create_call_post(class_name, func_name, func_params))
    
    def call_upload(self, bucket_id: str, file_path, mimetype = "text/plain"):  
        files = {'file': (os.path.basename(file_path), open(file_path, 'rb'), mimetype)}                      
        return self.call_upload_files(bucket_id, files)
    
    def call_upload_files(self, bucket_id: str, files: dict):
        response = requests.post(
            self._get_api(f'assets/upload/{bucket_id}'),
            files=files,
            auth=BearerAuth(self.token)            
        )        
        return response.json()
    
    def call_download(self, id: str):
        response = requests.get(
            self._get_api(f'assets/download/{id}'),
            auth=BearerAuth(self.token)
        )
        if response.status_code == 200:
            return response.content
        else:
            self._handle_api_error(response)        
    
    def call_mutation(self, mutation, module_name = FORMS_MODULE_NAME):
        return self.call_module(
            func="formMutation",
            params=[mutation],
            module_name=module_name
        )
    
    def _call(self, data, endpoint = 'api'):                
        
        response = requests.post(
            self._get_api(endpoint),
            json=data,
            auth=BearerAuth(self.token)            
        )     
        
        if response.status_code == 200:
            return response.json()
        else:
            self._handle_api_error(response)
    
    def _get_api(self, endpoint = 'api'):
        return f'{self.base_url}/{endpoint}'
    
    def _create_call_post(self, class_name, func_name, func_params):
        post = {
            "__class": class_name,
            "call": {
                "function": func_name
            }
        }
        
        if func_params:
            post['call']['params'] = func_params
        
        return post
    
    def _handle_api_error(self, response: requests.Response):
        raise APIError(response.json())
    
        