from .api.client import APIClient
from .query import FormsQuery, FormMutate, FormsQueryArray
from .accounts.accounts import Accounts
from .assets.assets import Assets
from .processing_client.processing_client import ProcessingClient
from .forms.forms import Forms
from .roots.roots import Roots

class CeFormsClient:
    """
    A client form communication with a CeForms server.
    
    This wraps the creation of an APIClient see :doc:`api documentation <api>` for full details.
    By default when no argument was used, the following environment variables used are :
    
    .. envvar:: CE_FORMS_BASE_URL
    
        URL to the CeForms API server
    
    .. envvar:: CE_FORMS_TOKEN
    
        API token provided by a CeForms backend 
        
    .. envvar:: CE_FORMS_DIR_PATH
    
        Local directory path to manage assets   
    
    Example:
    
        >>> import py_ce_forms_api
        >>> client = py_ce_forms_api.CeFormsClient()
        >>> client.query().with_root('forms-account').with_sub_forms(False).with_limit(1).call()
    
    Args:
        base_url (str): URL to the CeForms API server.
        token (str): API token provided by a CeForms backend.
        dir_path (str): local directory to store assets.
    
    """
    def __init__(self, *args, **kwargs):
        self.api = APIClient(*args, **kwargs)        
    
    def with_dir_path(self, dir_path: str):
        self.api.set_dir_path(dir_path)
        return self
    
    def self(self):
        """
        Call the APIClient self method and return accesses information.
        see :doc:`api documentation <api>` for full details.
        """
        return self.api.self()
    
    def query(self):
        """
        Returns the module to manage forms queries.
        see :doc:`query documentation <query>` for full details.
        """
        return FormsQuery(self.api)
    
    def query_array(self):
        """
        Returns the module to manage forms queries on array.
        see :doc:`query documentation <query_array>` for full details.
        """
        return FormsQueryArray(self.api)
    
    def mutation(self):
        """
        Returns the module to manage forms mutations.
        see :doc:`query documentation <query>` for full details.
        """
        return FormMutate(self.api)
    
    def accounts(self):
        """
        Returns the module to manage CeForms users accounts.
        see :doc:`accounts documentation <accounts>` for full details.
        """
        return Accounts(self.api)
    
    def assets(self):
        """
        Returns the module to manage assets (files, media).
        see :doc:`assets documentation <assets>` for full details.
        """
        return Assets(self.api)        

    def processing_client(self, pid):
        """
        Returns the entry point to remotely/locally call a processing.
        see: :doc:`processing_client documentation <processing_client>` for full details.
        """
        return ProcessingClient(self.api, pid)
    
    def forms(self):
        """
        Returns the module to manage CeForms forms.
        see :doc:`forms documentation <forms>` for full details.
        """
        return Forms(self.api)
    
    def roots(self):
        """
        Returns the module to manage CeForms roots.
        see :doc:`roots documentation <roots>` for full details.
        """
        return Roots(self.api)
    
    
        

    
    