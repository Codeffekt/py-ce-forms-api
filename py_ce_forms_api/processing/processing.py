import os
from fastapi import FastAPI, APIRouter
from ..client import CeFormsClient
from .task_pool import TaskPool

app = FastAPI()

class Processing():
    """
    This is the entry point used when you need to perform a
    long/async processing task
    """
    
    def __init__(self, client: CeFormsClient, func) -> None:
        self.server = "localhost"
        self.port = os.environ.get("CE_FORMS_TASK_PORT")       
        self.app = app   
        self.tasks = TaskPool(client, func, 10)      
        self.router = APIRouter()  
        self.router.add_api_route("/", self.self, methods=["GET"])    
        self.router.add_api_route("/processing/{pid}", self.__do_processing, methods=["GET"])
        self.router.add_api_route("/cancel/{pid}", self.__cancel, methods=["GET"])
        self.app.include_router(self.router)                    

    def get_app(self):
        return self.app        
    
    async def __do_processing(self, pid: str):                            
        
        if self.tasks.have_processing(pid):
            raise Exception(f"A processing is already running {pid}.")
        
        if not self.tasks.have_free_slot():
            raise Exception('Too much processing, no more free slot available')
                   
        form = self.tasks.run(pid)            
        
        return form
    
    def __cancel(self, pid: str):
        
        if not self.tasks.have_processing(pid):
            raise Exception(f"Unknown processing {pid}")
                
        return self.tasks.cancel(pid)                
    
    def self(self):
        return self.tasks.status()