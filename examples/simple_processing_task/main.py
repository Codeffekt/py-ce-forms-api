import asyncio
from py_ce_forms_api import *

async def my_long_task(task: Task):
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




