import asyncio
import inspect
import threading
import time
from ..client import CeFormsClient
from ..form import Form

class Task():
    """
    Thread encapsulation to perform async operation
    using processing api
    """

    #: Statuses that end the life of a task. The first one written wins.
    TERMINAL_STATUSES = ("DONE", "ERROR", "CANCELED")

    #: Delays between the retries of a terminal status write, in seconds.
    #: Worst case is the sum of these, spent blocking the event loop.
    RETRY_DELAYS = (0.5, 1.0, 2.0)

    def __init__(self, client: CeFormsClient, function, form: Form) -> None:
        self.client = client
        self.function = function
        self.form = form
        self.task = None
        self._loop = None
        self._terminal = None
        self._lock = threading.Lock()

    def is_current_processing(self, pid) -> bool:
        return self.form.id() == pid

    def id(self) -> str:
        return self.form.id()

    def is_terminal(self) -> bool:
        """Whether a terminal status has already been recorded for this task."""
        return self._terminal is not None

    async def run(self):
        """Run the task function and guarantee a terminal status on every exit path.

        The function may be declared ``async def`` (scheduled on the event loop)
        or ``def`` (run off the event loop through :func:`asyncio.to_thread`, so
        that blocking work never freezes the server).
        """
        self._loop = asyncio.get_running_loop()
        try:
            self.__start()
            self.task = self.__create_work_task()
            print(f'[Task]: run task {self.id()}')
            await self.task
            print(f'[Task]: task {self.id()} finished')
            self.__finished()
        except asyncio.CancelledError:
            print(f'[Task]: task {self.id()} cancelled')
            self.__set_status("CANCELED")
            # Never swallow a cancellation: suppressing it stalls the shutdown
            # of the event loop that requested it.
            raise
        except BaseException as err:
            print(f'[Task]: error from {self.id()}', err)
            self.__error(err)
        finally:
            if self._terminal is None:
                try:
                    self.__set_status("ERROR", "task terminated without a final status")
                except Exception as err:
                    # The last resort must never raise: doing so would replace
                    # whatever exception was already on its way out.
                    print(f'[Task]: could not finalize {self.id()}', err)

    def cancel(self, message: str = "task cancelled"):
        """Record ``CANCELED`` and ask the event loop to cancel the work.

        Called from the FastAPI thread pool, so the asyncio cancellation is
        scheduled through the owning loop rather than requested directly.

        Cancelling a task whose function is synchronous marks the form and frees
        the slot, but the thread itself keeps running: Python cannot interrupt
        it. Any status it writes afterwards is ignored.
        """
        self.__set_status("CANCELED", message)

        task, loop = self.task, self._loop
        if task is None or loop is None:
            # Cancelled before the work was scheduled; the status stands and the
            # guard keeps a later completion from overwriting it.
            return False

        loop.call_soon_threadsafe(task.cancel)
        return True

    async def run_blocking(self, fn, *args, **kwargs):
        """Run a blocking callable off the event loop and return its result.

        Use it inside an ``async def`` task function to offload a one-off
        blocking call (a synchronous HTTP request, a heavy computation) that
        would otherwise freeze the server for its whole duration::

            async def my_task(task):
                rows = await task.run_blocking(pandas.read_csv, path)
                task.update(f"{len(rows)} rows")

        A task function declared ``def`` is already run off the loop and does
        not need this.
        """
        return await asyncio.to_thread(fn, *args, **kwargs)

    def status(self):
        return self.form

    def get_client(self) -> CeFormsClient:
        return self.client

    def update(self, message: str):
        self.__set_status("RUNNING", message)

    def done(self, message: str | None = None):
        """Terminate the task with the ``DONE`` status.

        Optional: a task function that returns without calling it still ends as
        ``DONE``. Use it to close explicitly with a final message.

        The call is idempotent, and has no effect once another terminal status
        has been recorded — in particular after :meth:`error`, so that a
        reported failure is never masked. Work may continue after it, but any
        further :meth:`update` is ignored.
        """
        self.__set_status("DONE", message)

    def error(self, message: str):
        self.__set_status("ERROR", message)

    def on_exception(self, exception: Exception):
        self.__error(exception)

    def get_form(self):
        return self.form

    def __create_work_task(self):
        if inspect.iscoroutinefunction(self.function):
            return asyncio.create_task(self.function(self))
        return asyncio.create_task(asyncio.to_thread(self.__call_sync_function))

    def __call_sync_function(self):
        result = self.function(self)
        if inspect.isawaitable(result):
            # A callable whose __call__ is async is reported as synchronous by
            # inspect, and would silently do nothing here. Fail loudly instead.
            result.close()
            raise TypeError(
                f"task function {self.function!r} returned an awaitable but was "
                "not detected as a coroutine function; declare it with 'async def'"
            )
        return result

    def __start(self) -> None:
        self.form.set_value("message", "")
        self.__set_status("RUNNING")

    def __finished(self) -> None:
        self.__set_status("DONE")

    def __error(self, err: BaseException):
        self.__set_status("ERROR", str(err))

    def __set_status(self, status: str, message: str | None = None) -> bool:
        """Single point of truth for every status write.

        The first terminal status recorded is final: any later write, terminal
        or not, is ignored. The lock is held for the whole write, so that two
        concurrent terminal writes cannot both reach the API and let arrival
        order decide the outcome.
        """
        with self._lock:
            if self._terminal is not None:
                print(f'[Task]: ignored {status} on {self.id()}, already {self._terminal}')
                return False

            terminal = status in self.TERMINAL_STATUSES
            if terminal:
                self._terminal = status

            if message is not None:
                self.__append_message(message)

            self.form.set_value("status", status)
            return self.__write(status, retry=terminal)

    def __write(self, status: str, retry: bool) -> bool:
        """Push the form to the API, retrying terminal statuses.

        Deliberately free of ``await``: a synchronous finalisation runs to
        completion even inside a ``finally`` executed under cancellation, which
        an awaited one would not. Progress writes are not retried — losing one
        is harmless, losing a terminal status is the bug this guards against.
        """
        delays = self.RETRY_DELAYS if retry else ()

        for attempt in range(len(delays) + 1):
            try:
                self.client.mutation().update_single(self.form.form)
                return True
            except Exception as err:
                if attempt == len(delays):
                    print(f'[Task]: giving up writing {status} on {self.id()}', err)
                    return False
                print(f'[Task]: retrying {status} on {self.id()} after error', err)
                time.sleep(delays[attempt])

        return False

    def __append_message(self, message: str):
        current_message = self.form.get_value("message")
        next_message = f'{current_message}\n{message}'
        self.form.set_value("message", next_message)
        print(f'[Task]: new message from {self.id()} {next_message}')
