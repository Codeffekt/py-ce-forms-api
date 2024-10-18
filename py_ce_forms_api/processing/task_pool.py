import asyncio

from ..form.form import Form
from ..client import CeFormsClient
from ..query import FormsQuery
from .task import Task

class TaskPool():
    """
    A set of Tasks used to provide multiples async operations using
    processing api
    """
    
    def __init__(self, client: CeFormsClient, function, maxLength) -> None:
        self.client = client
        self.function = function
        self.tasks: list[Task] = []
        self.maxLength = maxLength
    
    def have_processing(self, pid) -> bool:
        try:
            self.find_task(pid)
            return True
        except:
            return False
    
    def have_free_slot(self) -> bool:
        return len(self.tasks) < self.maxLength    
    
    def status(self):
        return {
            "length": len(self.tasks),
            "maxLength": self.maxLength
        }
    
    def find_task(self, pid: str) -> Task:
       return  next(t for t in self.tasks if t.is_current_processing(pid))
    
    def run(self, pid: str):
        form = self.__retrieve_processing(pid)
        asyncio.create_task(self.__handle_processing(form))
        return form
      
    def cancel(self, pid):
        task = self.find_task(pid)
        task.cancel()
        return task.get_form().form
        
    def __retrieve_processing(self, pid: str):
        return Form(self.client.query().with_sub_forms().call_single(pid))  
        
    async def __handle_processing(self, form: Form):         
        task = Task(self.client, self.function, form)
        self.tasks.append(task)
        await task.run()                           
        self.tasks = list(filter(lambda t: not t.is_current_processing(form.id()), self.tasks))
    