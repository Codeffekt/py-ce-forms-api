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
        # asyncio only keeps a weak reference to a running task, so a detached
        # one can be garbage collected mid-execution unless we hold it here.
        self._scheduled = set()

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
        scheduled = asyncio.create_task(self.__handle_processing(form))
        self._scheduled.add(scheduled)
        scheduled.add_done_callback(self._scheduled.discard)
        return form

    async def run_awaitable(self, pid: str):
        form = self.__retrieve_processing(pid)
        await asyncio.create_task(self.__handle_processing(form))
        return form

    def cancel(self, pid):
        task = self.find_task(pid)
        print(f'[TaskPool]: cancel task {task.id()}')
        task.cancel()
        return task.get_form().form

    def shutdown(self):
        """Finalise every in-flight task as CANCELED.

        Called on the application shutdown event: without it, the forms of the
        tasks the server was running stay RUNNING forever.
        """
        for task in list(self.tasks):
            print(f'[TaskPool]: shutdown, cancelling task {task.id()}')
            task.cancel("server shutdown")

    def __retrieve_processing(self, pid: str):
        return Form(self.client.query().with_sub_forms().call_single(pid))

    async def __handle_processing(self, form: Form):
        task = None
        try:
            task = Task(self.client, self.function, form)
            self.tasks.append(task)
            print(f'[TaskPool]: run task {task.id()}')
            await task.run()
            print(f'[TaskPool]: task {task.id()} finished')
        except asyncio.CancelledError:
            print(f'[TaskPool]: task {self.__describe(task)} cancelled')
            # Swallowing a cancellation stalls the shutdown of the loop that
            # requested it.
            raise
        except Exception as err:
            print(f'[TaskPool]: error from task {self.__describe(task)}', err)
        finally:
            if task is not None:
                # Second net: Task guarantees its own terminal status, but the
                # steps above can fail before that guarantee comes into play.
                if not task.is_terminal():
                    task.error("processing failed before the task could report")
                self.__remove_task(task)

    def __describe(self, task: Task | None) -> str:
        return task.id() if task is not None else "<not created>"

    def __remove_task(self, task: Task):
        self.tasks = list(filter(lambda t: not t.is_current_processing(task.id()), self.tasks))


