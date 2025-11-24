import os

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi import Depends, FastAPI, APIRouter, HTTPException, status
from ..client import CeFormsClient
from .processing_tasks import ProcessingTasks

app = FastAPI()
security = HTTPBearer()

class Processing(ProcessingTasks):
    """
    This is the entry point used when you need to perform a
    long/async processing task
    """
    
    def __init__(self, client: CeFormsClient, func) -> None:
        ProcessingTasks.__init__(self, client, func)
        self.server = "localhost"
        self.port = os.environ.get("CE_FORMS_TASK_PORT")
        self.token = os.environ.get("CE_FORMS_TASK_TOKEN")
        
        if self.token is None:
            print("[Processing] There is no defined token to protect from externals accesses")
        
        self.app = app           
        self.router = APIRouter(
            dependencies= [Depends(self._verify_token)] if self.token is not None else []
        )  
        self.router.add_api_route("/", self.self, methods=["GET"])    
        self.router.add_api_route("/processing/{pid}", self.__do_processing, methods=["GET"])
        self.router.add_api_route("/cancel/{pid}", self.__cancel, methods=["GET"])
        self.app.include_router(self.router)                    

    def get_app(self):
        return self.app        
    
    async def __do_processing(self, pid: str):                        
        res = await self.do_processing(pid)
        return res
            
    def __cancel(self, pid: str):        
        return self.cancel(pid)       
    
    def _verify_token(self, credentials: HTTPAuthorizationCredentials = Depends(security)):                        
        token = credentials.credentials
        if token != self.token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing Bearer token",
            )
        return token
    
    def self(self):
        return self.tasks.status()