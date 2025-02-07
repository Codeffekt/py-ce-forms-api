import sys
import asyncio
from py_ce_forms_api import *

async def my_long_task(task: Task):  
    print("my_long_task called")  
    await asyncio.sleep(5)
    task.update("Still running")    
    await asyncio.sleep(5)
    task.update("Still still running")    
    await asyncio.sleep(4)
    task.update("End of processing")    

def create_app():
    client = CeFormsClient()
    processing = Processing(client, my_long_task)
    return processing.get_app()

def main(id):
    client = CeFormsClient()
    processing = ProcessingTasks(client, my_long_task)    
    form = processing.do_processing_sync(id)
    print("End of execution", form)

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 1:
        print(processing.__file__)
        main(args[0])
    else:
        print('Invalid number of arguments: <processing id>')


