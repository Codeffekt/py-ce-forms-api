from ..api.client import APIClient
from ..form.form import Form
from ..query import FormsQuery
from ..query import FormMutate
import requests

class ProcessingClient():
    """
    This is the entry point used when you need to remotely/locally
    call a processing task
    """
    
    processing_root = "forms-processing"
    
    def __init__(self, client: APIClient, pid: str) -> None:
        self.client = client
        self.pid = pid
        self.__retrieve_processing_data()
    
    def start(self):        
        if not self.is_started():
            self.__update_processing_status("PENDING")
            return self.__api_call(self.__get_api_endpoint(f"processing/{self.processing_data.id()}"))
        return self.processing_data
    
    def cancel(self):
        if self.is_started():
            self.__update_processing_status("PENDING")
            return self.__api_call(self.__get_api_endpoint(f"cancel/{self.processing_data.id()}"))
        return self.processing_data
    
    def status(self):
        self.__api_call(self.__get_api_endpoint(""))
        return self.processing_data
    
    def is_started(self) -> bool:
        status = self.processing_data.get_value("status")
        return status == "PENDING" or status == "RUNNING"
    
    def __retrieve_processing_data(self):
        self.processing_data = Form(FormsQuery(self.client).with_sub_forms().call_single(self.pid))
        if self.processing_data is None:
            raise Exception(f"Processing id {self.pid} not found.") 
        
        if self.processing_data.get_root() != self.processing_root:
            raise Exception(f"Processing id {self.pid} has root {self.processing_data.get_root()} instead of {self.processing_root}")
               
        self.endpoint = self.processing_data.get_sub_form("endpoint")
        
    def __update_processing_status(self, status: str) -> None:        
        self.processing_data.set_value("status", status)
        FormMutate(self.client).update_single(self.processing_data.form)
        
    def __api_call(self, endpoint):
        response = requests.get(
            endpoint
        )
        if response.status_code == 200:
            return response.content
        else:
            self._handle_api_error(endpoint, response)    
    
    def __get_api_endpoint(self, endpoint: str):
        server = self.endpoint.get_value("server")
        return f"{server}/{endpoint}"
    
    def _handle_api_error(self, endpoint: str, response: requests.Response):
        raise Exception(f"Call api error on {endpoint}")
        
    