from .api.client import APIClient
from .query import FormsQuery, FormMutate
from .accounts.accounts import Accounts
from .assets.assets import Assets
from .processing.processing import Processing
from .projects.projects import Projects
from .forms.forms import Forms

class CeFormsClient:
    """
    A client form communication with a CeForms server.
    
    This wraps the creation of an APIClient see :doc:`api documentation <api>` for full details.
    By default when no argument was used, the following environment variables used are :
    
    .. envvar:: CE_FORMS_BASE_URL
    
        URL to the CeForms API server
    
    .. envvar:: CE_FORMS_TOKEN
    
        API token provided by a CeForms backend    
    
    Example:
    
        >>> import py_ce_forms_api
        >>> client = py_ce_forms_api.CeFormsClient()
        >>> client.query().with_root('forms-account').with_sub_forms(False).with_limit(1).call()
    
    Args:
        base_url (str): URL to the CeForms API server.
        token (str): API token provided by a CeForms backend.
    
    """
    def __init__(self, *args, **kwargs):
        self.api = APIClient(*args, **kwargs)
    
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
    
    def processing(self, task):
        """
        Returns the module to manage processing.
        see :doc:`processing documentation <processing>` for full details.
        """
        return Processing(self.api, task)

    def projects(self):
        """
        Returns the module to manage CeForms projects.
        see :doc:`projects documentation <projects>` for full details.
        """
        return Projects(self.api)
    
    def forms(self):
        """
        Returns the module to manage CeForms forms.
        see :doc:`forms documentation <forms>` for full details.
        """
        return Forms(self.api)
        

    
    