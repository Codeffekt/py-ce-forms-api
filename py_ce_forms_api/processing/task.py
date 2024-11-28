import asyncio
from ..client import CeFormsClient
from ..form import Form

class Task():
    """
    Thread encapsulation to perform async operation
    using processing api
    """
    
    def __init__(self, client: CeFormsClient, function, form: Form) -> None:
        self.client = client
        self.function = function
        self.form = form
        self.task = None        
    
    def is_current_processing(self, pid) -> bool:
        return self.form.id() == pid
    
    def id(self) -> str:
        return self.form.id()
    
    async def run(self):
        try:
            self.__start()
            self.task = asyncio.create_task(self.function(self))
            print(f'[Task]: run task {self.id()}')
            await self.task
            print(f'[Task]: task {self.id()} finished')            
            self.__finished()        
        except Exception as err:
            print(f'[Task]: error from {self.id()}', err)
            self.__error(err)
        
    def cancel(self):
        self.__update_processing_status("CANCELED")
        return self.task.cancel()
    
    def status(self):
        return self.form
    
    def get_client(self) -> CeFormsClient:
        return self.client
    
    def update(self, message: str):
        self.__update_message(message)
        self.__update_processing_status("RUNNING")                
    
    def error(self, message: str):
        self.__update_message(message)
        self.__update_processing_status("ERROR")   
        
    def on_exception(self, exception: Exception):
        self.__error(exception)
    
    def get_form(self):
        return self.form
    
    def __start(self) -> None:
        self.form.set_value("message", "")
        self.__update_processing_status("RUNNING")    
    
    def __finished(self) -> None:
        self.__update_processing_status("DONE")  
    
    def __failed(self) -> None:
        self.__update_processing_status("ERROR") 
    
    def __error(self, err: Exception):
        self.__update_message(str(err))
        self.__update_processing_status("ERROR") 
    
    def __update_processing_status(self, status: str) -> None:        
        self.form.set_value("status", status)
        self.client.mutation().update_single(self.form.form)
        
    def __update_message(self, message: str):
        current_message = self.form.get_value("message")
        next_message = f'{current_message}\n{message}'
        self.form.set_value("message", next_message)
        print(f'[Task]: new message from {self.id()} {next_message}')
            
        
    