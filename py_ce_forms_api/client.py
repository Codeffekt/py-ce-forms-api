from .api.client import APIClient
from .query import FormsQuery, FormMutate
from .accounts.accounts import Accounts
from .assets.assets import Assets
from .processing.processing import Processing
class CeFormsClient:
    """
    A client form communication with a CeForms server.
    
    Example:
    
        >>> import py_ce_forms_api
        >>> client = py_ce_forms_api.CeFormsClient()
        >>> client.query().with_root('forms-account').with_sub_forms(False).with_limit(1).call()
    """
    def __init__(self, *args, **kwargs):
        self.api = APIClient(*args, **kwargs)
    
    def self(self):
        return self.api.self()
    
    def query(self):
        return FormsQuery(self.api)
    
    def mutation(self):
        return FormMutate(self.api)
    
    def accounts(self):
        return Accounts(self.api)
    
    def assets(self):
        return Assets(self.api)
    
    def processing(self, task):
        return Processing(self.api, task)

    
    