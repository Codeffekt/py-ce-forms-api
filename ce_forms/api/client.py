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
        
    def self(self):
        response = requests.get(f'{self.base_url}/self', auth=BearerAuth(self.token))
        return response.json()
    
    def call_module(self, func, params, module_name):
        return self.call(f'Public{module_name}', func_name=func, func_params=params)
    
    def call_forms_query(self, query, module_name = FORMS_MODULE_NAME):
        return self.call_module(
            func="getFormsQuery",
            params=[query],
            module_name=module_name
        )           
    
    def call_form_query(self, id: str, query, module_name = FORMS_MODULE_NAME):
        return self.call_module(
            func="getFormQuery",
            params=[id, query],
            module_name=module_name
        )
    
    def call(self, class_name, func_name, func_params):
        return self._call(self._create_call_post(class_name, func_name, func_params))
    
    def call_upload(self, bucket_id: str, file_path, mimetype = "text/plain"):  
        files = {'file': (os.path.basename(file_path), open(file_path, 'rb'), mimetype)}              
        response = requests.post(
            self._get_api(f'assets/upload/{bucket_id}'),
            files=files,
            auth=BearerAuth(self.token)            
        )        
        return response.json()
    
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
    
        