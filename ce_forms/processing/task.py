import asyncio
from ..api.client import APIClient
from ..query import FormMutate
from ..form import Form

class Task():
    """
    Thread encapsulation to perform async operation
    using processing api
    """
    
    def __init__(self, client: APIClient, function, form: Form) -> None:
        self.client = client
        self.function = function
        self.form = form
        self.task = None        
    
    def is_current_processing(self, pid) -> bool:
        return self.form.id() == pid
    
    async def run(self):
        try:
            self.__start()
            self.task = asyncio.create_task(self.function(self))
            await self.task
            self.__finished()
        except Exception:
            self.__failed()      
        
    def cancel(self):
        self.__update_processing_status("CANCELED")
        self.task.cancel()
    
    def status(self):
        return self.form
    
    def update(self, message: str):
        self.form.set_value("message", message)
        self.__update_processing_status("RUNNING")                
    
    def get_form(self):
        return self.form
    
    def __start(self) -> None:
        self.__update_processing_status("RUNNING")    
    
    def __finished(self) -> None:
        self.__update_processing_status("DONE")  
    
    def __failed(self) -> None:
        self.__update_processing_status("ERROR") 
    
    def __update_processing_status(self, status: str) -> None:        
        self.form.set_value("status", status)
        FormMutate(self.client).update_single(self.form.form)
            
        
    