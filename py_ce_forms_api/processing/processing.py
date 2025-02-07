import os
from fastapi import FastAPI, APIRouter
from ..client import CeFormsClient
from .processing_tasks import ProcessingTasks

app = FastAPI()

class Processing(ProcessingTasks):
    """
    This is the entry point used when you need to perform a
    long/async processing task
    """
    
    def __init__(self, client: CeFormsClient, func) -> None:
        ProcessingTasks.__init__(self, client, func)
        self.server = "localhost"
        self.port = os.environ.get("CE_FORMS_TASK_PORT")       
        self.app = app           
        self.router = APIRouter()  
        self.router.add_api_route("/", self.self, methods=["GET"])    
        self.router.add_api_route("/processing/{pid}", self.__do_processing, methods=["GET"])
        self.router.add_api_route("/cancel/{pid}", self.__cancel, methods=["GET"])
        self.app.include_router(self.router)                    

    def get_app(self):
        return self.app        
    
    async def __do_processing(self, pid: str):                            
        return self.do_processing(pid)
            
    def __cancel(self, pid: str):        
        return self.cancel(pid)       
    
    def self(self):
        return self.tasks.status()