import asyncio
from ..client import CeFormsClient
from .task_pool import TaskPool

class ProcessingTasks():
    """
    This is the entry point used when you need to perform a
    long/async processing task
    """
    
    def __init__(self, client: CeFormsClient, func) -> None:        
        self.tasks = TaskPool(client, func, 10)                               
    
    async def do_processing(self, pid: str):                                    
        
        self._check_task_avaibility(pid)
                   
        form = self.tasks.run(pid)            
        
        return form
    
    def do_processing_sync(self, pid: str):
        
        self._check_task_avaibility(pid)
             
        form = asyncio.run(self.tasks.run_awaitable(pid))                                           
        
        return form
        
    
    def cancel(self, pid: str):
        
        if not self.tasks.have_processing(pid):
            raise Exception(f"Unknown processing {pid}")
                
        return self.tasks.cancel(pid)   
    
    def _check_task_avaibility(self, pid: str):
        if self.tasks.have_processing(pid):
            raise Exception(f"A processing is already running {pid}.")
        
        if not self.tasks.have_free_slot():
            raise Exception('Too much processing, no more free slot available')