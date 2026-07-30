import asyncio
import threading
from datetime import timedelta

import pytest

from py_ce_forms_api import Form, FormsRes, Task, TaskPool

from .conftest import MTIME, make_block, make_form_dict


async def drain_pending_tasks():
    """Wait for the tasks `TaskPool.run` scheduled behind our back."""
    pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    await asyncio.gather(*pending, return_exceptions=True)


def processing_form(id="proc-1", status="PENDING", **extra):
    return make_form_dict(id=id, root="forms-processing", blocks=[
        make_block("status", "text", status),
        make_block("message", "text", ""),
    ], **extra)


class FakeMutation:
    def __init__(self, failures=0):
        self.updates = []
        self.attempts = 0
        #: How many leading attempts raise before the mutation starts working.
        self.failures = failures

    def update_single(self, form):
        self.attempts += 1
        if self.attempts <= self.failures:
            raise RuntimeError(f"mutation failed (attempt {self.attempts})")
        self.updates.append(
            {"id": form["id"], "status": form["content"]["status"]["value"],
             "message": form["content"]["message"]["value"]}
        )
        return form


class FakeQuery:
    """`FormsQuery` look-alike covering both the pool and the reconcile paths."""

    def __init__(self, client):
        self.client = client
        self.root = None
        self.filters = {}

    def with_sub_forms(self, value=True):
        return self

    def with_limit(self, limit):
        return self

    def with_root(self, root):
        self.root = root
        return self

    def where(self, field, value, op="="):
        self.filters[field] = value
        return self

    def call_single(self, pid):
        return self.client.forms[pid]

    def call(self):
        elts = [
            form for form in self.client.forms.values()
            if form["root"] == self.root
            and form["content"]["status"]["value"] == self.filters.get("status")
        ]
        return FormsRes({"elts": elts, "total": len(elts), "limit": 10, "offset": 0})


class FakeCeFormsClient:
    """`CeFormsClient` look-alike for the processing layer."""

    def __init__(self, forms=None, mutation_failures=0):
        self.forms = forms or {}
        self.mutations = FakeMutation(failures=mutation_failures)

    def mutation(self):
        return self.mutations

    def query(self):
        return FakeQuery(self)

    @property
    def statuses(self):
        return [u["status"] for u in self.mutations.updates]


@pytest.fixture(autouse=True)
def instant_retries(monkeypatch):
    """Keep the retry backoff out of the suite's wall clock."""
    monkeypatch.setattr(Task, "RETRY_DELAYS", (0, 0, 0))


class TestTask:
    @pytest.fixture
    def client(self):
        return FakeCeFormsClient()

    def test_identity(self, client):
        task = Task(client, None, Form(processing_form()))
        assert task.id() == "proc-1"
        assert task.is_current_processing("proc-1") is True
        assert task.is_current_processing("other") is False
        assert task.is_terminal() is False

    def test_successful_run_goes_running_then_done(self, client):
        async def work(task):
            task.update("halfway")

        task = Task(client, work, Form(processing_form()))
        asyncio.run(task.run())

        assert client.statuses == ["RUNNING", "RUNNING", "DONE"]
        assert client.mutations.updates[1]["message"] == "\nhalfway"

    def test_failing_run_reports_the_error(self, client):
        async def work(task):
            raise ValueError("boom")

        task = Task(client, work, Form(processing_form()))
        asyncio.run(task.run())

        assert client.statuses == ["RUNNING", "ERROR"]
        assert "boom" in client.mutations.updates[-1]["message"]

    def test_error_helper(self, client):
        task = Task(client, None, Form(processing_form()))
        task.error("bad input")

        assert client.statuses == ["ERROR"]
        assert "bad input" in client.mutations.updates[-1]["message"]

    def test_on_exception(self, client):
        task = Task(client, None, Form(processing_form()))
        task.on_exception(RuntimeError("nope"))

        assert client.statuses == ["ERROR"]

    def test_get_client_and_form(self, client):
        form = Form(processing_form())
        task = Task(client, None, form)
        assert task.get_client() is client
        assert task.get_form() is form
        assert task.status() is form


class TestTerminalStatusIsGuaranteed:
    """`Task.run()` never returns without a terminal status."""

    @pytest.fixture
    def client(self):
        return FakeCeFormsClient()

    def test_a_base_exception_ends_in_error(self, client):
        class Boom(BaseException):
            """Not an `Exception`, so `except Exception` would miss it."""

        async def work(task):
            raise Boom("boom from a BaseException")

        task = Task(client, work, Form(processing_form()))
        asyncio.run(task.run())

        assert task.is_terminal() is True
        assert client.statuses[-1] == "ERROR"
        assert "boom from a BaseException" in client.mutations.updates[-1]["message"]

    def test_a_keyboard_interrupt_ends_in_canceled(self, client):
        """asyncio hijacks KeyboardInterrupt and SystemExit.

        It re-raises them into the event loop and hands the awaiter a
        `CancelledError` instead, so the task finalises as CANCELED. The
        invariant still holds — the form is terminal — but the status differs
        from a plain BaseException.
        """
        async def work(task):
            raise KeyboardInterrupt("interrupted")

        task = Task(client, work, Form(processing_form()))

        with pytest.raises(KeyboardInterrupt):
            asyncio.run(task.run())

        assert task.is_terminal() is True
        assert client.statuses[-1] == "CANCELED"

    def test_an_external_cancellation_ends_in_canceled_and_propagates(self, client):
        started = asyncio.Event()

        async def work(task):
            started.set()
            await asyncio.sleep(30)

        task = Task(client, work, Form(processing_form()))

        async def scenario():
            runner = asyncio.create_task(task.run())
            await started.wait()
            runner.cancel()
            with pytest.raises(asyncio.CancelledError):
                await runner

        asyncio.run(scenario())

        assert client.statuses[-1] == "CANCELED"
        assert task.is_terminal() is True

    def test_the_last_resort_writes_error(self, client, monkeypatch):
        """An unforeseen path that skips finalisation is caught by the `finally`."""
        async def work(task):
            pass

        monkeypatch.setattr(Task, "_Task__finished", lambda self: None)

        task = Task(client, work, Form(processing_form()))
        asyncio.run(task.run())

        assert client.statuses[-1] == "ERROR"
        assert "without a final status" in client.mutations.updates[-1]["message"]


class TestFirstTerminalWins:
    @pytest.fixture
    def client(self):
        return FakeCeFormsClient()

    def test_completion_cannot_overwrite_a_cancellation(self, client):
        task = Task(client, None, Form(processing_form()))
        task.cancel()
        task.done("finished anyway")

        assert client.statuses == ["CANCELED"]

    def test_progress_cannot_overwrite_an_error(self, client):
        task = Task(client, None, Form(processing_form()))
        task.error("bad input")
        task.update("still going")

        assert client.statuses == ["ERROR"]

    def test_done_is_idempotent(self, client):
        task = Task(client, None, Form(processing_form()))
        task.done("all good")
        task.done("all good again")

        assert client.statuses == ["DONE"]
        assert client.mutations.attempts == 1

    def test_done_after_error_does_not_mask_the_failure(self, client):
        task = Task(client, None, Form(processing_form()))
        task.error("bad input")
        task.done()

        assert client.statuses == ["ERROR"]

    def test_update_after_done_is_ignored(self, client):
        async def work(task):
            task.done("early")
            task.update("more work")

        task = Task(client, work, Form(processing_form()))
        asyncio.run(task.run())

        assert client.statuses == ["RUNNING", "DONE"]

    def test_done_replaces_the_automatic_completion(self, client):
        async def work(task):
            task.done("End of processing")

        task = Task(client, work, Form(processing_form()))
        asyncio.run(task.run())

        assert client.statuses == ["RUNNING", "DONE"]
        assert "End of processing" in client.mutations.updates[-1]["message"]


class TestTerminalWriteRetries:
    def test_a_terminal_write_is_retried(self):
        client = FakeCeFormsClient(mutation_failures=1)
        task = Task(client, None, Form(processing_form()))

        task.done()

        assert client.mutations.attempts == 2
        assert client.statuses == ["DONE"]

    def test_a_terminal_write_gives_up_without_raising(self):
        client = FakeCeFormsClient(mutation_failures=99)

        async def work(task):
            pass

        task = Task(client, work, Form(processing_form()))
        asyncio.run(task.run())  # must not raise

        assert client.mutations.updates == []
        # One attempt for RUNNING, then the full retry budget for DONE.
        assert client.mutations.attempts == 1 + len(Task.RETRY_DELAYS) + 1

    def test_a_progress_write_is_not_retried(self):
        client = FakeCeFormsClient(mutation_failures=99)
        task = Task(client, None, Form(processing_form()))

        task.update("halfway")

        assert client.mutations.attempts == 1


class TestCancellation:
    def test_cancel_before_the_work_started(self):
        """`cancel()` in the window where the asyncio task does not exist yet."""
        client = FakeCeFormsClient()
        task = Task(client, None, Form(processing_form()))

        assert task.cancel() is False
        assert client.statuses == ["CANCELED"]

    def test_a_later_completion_cannot_undo_it(self):
        client = FakeCeFormsClient()

        async def work(task):
            pass

        task = Task(client, work, Form(processing_form()))
        task.cancel()
        asyncio.run(task.run())

        assert client.statuses == ["CANCELED"]

    def test_cancel_schedules_the_cancellation_on_the_owning_loop(self):
        client = FakeCeFormsClient({"proc-1": processing_form()})
        started = asyncio.Event()

        async def work(task):
            started.set()
            await asyncio.sleep(30)

        task = Task(client, work, Form(processing_form()))

        async def scenario():
            runner = asyncio.create_task(task.run())
            await started.wait()
            assert task.cancel() is True
            with pytest.raises(asyncio.CancelledError):
                await runner

        asyncio.run(scenario())

        assert client.statuses[-1] == "CANCELED"


class TestSynchronousTaskFunctions:
    def test_a_plain_function_reaches_done(self):
        client = FakeCeFormsClient()
        seen = []

        def work(task):
            seen.append(task.id())

        task = Task(client, work, Form(processing_form()))
        asyncio.run(task.run())

        assert seen == ["proc-1"]
        assert client.statuses == ["RUNNING", "DONE"]

    def test_a_plain_function_that_raises_reaches_error(self):
        client = FakeCeFormsClient()

        def work(task):
            raise RuntimeError("boom")

        task = Task(client, work, Form(processing_form()))
        asyncio.run(task.run())

        assert client.statuses == ["RUNNING", "ERROR"]
        assert "boom" in client.mutations.updates[-1]["message"]

    def test_a_callable_returning_an_awaitable_is_reported(self):
        """A misdetected coroutine would otherwise silently do nothing."""
        client = FakeCeFormsClient()

        class AsyncCallable:
            async def __call__(self, task):
                pass

        task = Task(client, AsyncCallable(), Form(processing_form()))
        asyncio.run(task.run())

        assert client.statuses == ["RUNNING", "ERROR"]
        assert "async def" in client.mutations.updates[-1]["message"]

    def test_a_blocking_function_does_not_freeze_the_event_loop(self):
        client = FakeCeFormsClient({"proc-1": processing_form()})
        order = []
        release = threading.Event()

        def work(task):
            order.append("work-started")
            release.wait(2)
            order.append("work-done")

        async def scenario():
            pool = TaskPool(client, work, 2)
            pool.run("proc-1")
            for _ in range(5):
                await asyncio.sleep(0.01)
            order.append("loop-alive")
            release.set()
            await drain_pending_tasks()

        asyncio.run(scenario())

        assert order.index("loop-alive") < order.index("work-done"), \
            "the event loop must keep running while a blocking task function is in flight"

    def test_cancelling_a_synchronous_task_neutralises_the_surviving_thread(self):
        client = FakeCeFormsClient({"proc-1": processing_form()})
        started, release, finished = (threading.Event() for _ in range(3))

        def work(task):
            started.set()
            release.wait(2)
            task.update("too late")  # the thread outlives the cancellation
            finished.set()

        async def scenario():
            pool = TaskPool(client, work, 2)
            pool.run("proc-1")
            await asyncio.to_thread(started.wait, 2)
            pool.cancel("proc-1")
            await drain_pending_tasks()
            release.set()

        asyncio.run(scenario())
        assert finished.wait(2), "the thread should have run to completion"

        assert client.statuses[-1] == "CANCELED"
        assert "too late" not in client.mutations.updates[-1]["message"]


class TestRunBlocking:
    def test_it_returns_the_result(self):
        client = FakeCeFormsClient()
        results = []

        async def work(task):
            results.append(await task.run_blocking(lambda a, b: a + b, 2, b=3))

        task = Task(client, work, Form(processing_form()))
        asyncio.run(task.run())

        assert results == [5]
        assert client.statuses[-1] == "DONE"

    def test_it_propagates_the_exception(self):
        client = FakeCeFormsClient()

        def boom():
            raise ValueError("blocking boom")

        async def work(task):
            await task.run_blocking(boom)

        task = Task(client, work, Form(processing_form()))
        asyncio.run(task.run())

        assert client.statuses[-1] == "ERROR"
        assert "blocking boom" in client.mutations.updates[-1]["message"]


class TestTaskPool:
    def test_status_reports_capacity(self):
        pool = TaskPool(FakeCeFormsClient(), None, 3)
        assert pool.status() == {"length": 0, "maxLength": 3}
        assert pool.have_free_slot() is True

    def test_unknown_processing(self):
        pool = TaskPool(FakeCeFormsClient(), None, 3)
        assert pool.have_processing("proc-1") is False
        with pytest.raises(StopIteration):
            pool.find_task("proc-1")

    def test_run_awaitable_executes_and_frees_the_slot(self):
        client = FakeCeFormsClient({"proc-1": processing_form()})
        seen = []

        async def work(task):
            seen.append(task.id())

        pool = TaskPool(client, work, 2)
        form = asyncio.run(pool.run_awaitable("proc-1"))

        assert isinstance(form, Form)
        assert seen == ["proc-1"]
        assert pool.status()["length"] == 0, "the task must be removed once finished"
        assert client.statuses[-1] == "DONE"

    def test_a_failing_task_still_frees_the_slot(self):
        client = FakeCeFormsClient({"proc-1": processing_form()})

        async def work(task):
            raise RuntimeError("boom")

        pool = TaskPool(client, work, 2)
        asyncio.run(pool.run_awaitable("proc-1"))

        assert pool.status()["length"] == 0
        assert client.statuses[-1] == "ERROR"

    def test_run_schedules_the_task_in_the_background(self):
        client = FakeCeFormsClient({"proc-1": processing_form()})
        seen = []

        async def work(task):
            seen.append(task.id())

        pool = TaskPool(client, work, 2)

        async def scenario():
            form = pool.run("proc-1")
            await drain_pending_tasks()
            return form

        form = asyncio.run(scenario())

        assert form.id() == "proc-1"
        assert seen == ["proc-1"]
        assert pool.status()["length"] == 0

    def test_run_keeps_a_strong_reference_to_the_scheduled_task(self):
        client = FakeCeFormsClient({"proc-1": processing_form()})
        release = asyncio.Event()

        async def work(task):
            await release.wait()

        pool = TaskPool(client, work, 2)

        async def scenario():
            pool.run("proc-1")
            await asyncio.sleep(0)
            assert len(pool._scheduled) == 1, "a detached task could be garbage collected"
            release.set()
            await drain_pending_tasks()
            assert pool._scheduled == set(), "the reference must be released once done"

        asyncio.run(scenario())

    def test_a_task_that_cannot_be_built_frees_the_slot(self, monkeypatch):
        client = FakeCeFormsClient({"proc-1": processing_form()})

        def boom(*args, **kwargs):
            raise RuntimeError("cannot build the task")

        monkeypatch.setattr("py_ce_forms_api.processing.task_pool.Task", boom)

        pool = TaskPool(client, None, 2)
        asyncio.run(pool.run_awaitable("proc-1"))  # must not raise UnboundLocalError

        assert pool.status()["length"] == 0

    def test_cancel_a_running_task(self):
        client = FakeCeFormsClient({"proc-1": processing_form()})
        started = asyncio.Event()

        async def work(task):
            started.set()
            await asyncio.sleep(30)

        pool = TaskPool(client, work, 2)

        async def scenario():
            pool.run("proc-1")
            await started.wait()
            assert pool.status()["length"] == 1
            form = pool.cancel("proc-1")
            await drain_pending_tasks()
            return form

        form = asyncio.run(scenario())

        assert form["id"] == "proc-1"
        assert "CANCELED" in client.statuses
        assert pool.status()["length"] == 0, "a cancelled task must free its slot"

    def test_pool_is_full(self):
        pool = TaskPool(FakeCeFormsClient(), None, 1)
        pool.tasks.append(Task(pool.client, None, Form(processing_form())))

        assert pool.have_free_slot() is False
        assert pool.have_processing("proc-1") is True
        assert pool.find_task("proc-1").id() == "proc-1"


class TestShutdown:
    def test_in_flight_tasks_are_cancelled(self):
        client = FakeCeFormsClient({
            "proc-1": processing_form(id="proc-1"),
            "proc-2": processing_form(id="proc-2"),
        })
        started = []

        async def work(task):
            started.append(task.id())
            await asyncio.sleep(30)

        pool = TaskPool(client, work, 4)

        async def scenario():
            pool.run("proc-1")
            pool.run("proc-2")
            while len(started) < 2:
                await asyncio.sleep(0)
            pool.shutdown()
            await drain_pending_tasks()

        asyncio.run(scenario())

        cancelled = [u for u in client.mutations.updates if u["status"] == "CANCELED"]
        assert sorted(u["id"] for u in cancelled) == ["proc-1", "proc-2"]
        assert all("server shutdown" in u["message"] for u in cancelled)

    def test_a_finished_task_is_left_alone(self):
        client = FakeCeFormsClient({"proc-1": processing_form()})

        async def work(task):
            pass

        pool = TaskPool(client, work, 2)
        asyncio.run(pool.run_awaitable("proc-1"))

        pool.shutdown()

        assert client.statuses == ["RUNNING", "DONE"]


class TestProcessingTasks:
    @pytest.fixture
    def tasks(self):
        from py_ce_forms_api import ProcessingTasks

        client = FakeCeFormsClient({"proc-1": processing_form()})

        async def work(task):
            pass

        return ProcessingTasks(client, work)

    def test_rejects_a_duplicate_processing(self, tasks):
        tasks.tasks.tasks.append(Task(None, None, Form(processing_form())))

        with pytest.raises(Exception, match="already running"):
            tasks._check_task_avaibility("proc-1")

    def test_rejects_when_no_slot_is_free(self, tasks):
        tasks.tasks.maxLength = 0

        with pytest.raises(Exception, match="no more free slot"):
            tasks._check_task_avaibility("proc-1")

    def test_cancel_unknown_processing(self, tasks):
        with pytest.raises(Exception, match="Unknown processing"):
            tasks.cancel("proc-1")

    def test_do_processing_sync(self, tasks):
        form = tasks.do_processing_sync("proc-1")
        assert form.id() == "proc-1"
        assert tasks.tasks.status()["length"] == 0


class TestReconcile:
    """Recovering forms stranded by a process that died without reporting."""

    @pytest.fixture
    def make_tasks(self):
        from py_ce_forms_api import ProcessingTasks

        def factory(forms):
            async def work(task):
                pass

            client = FakeCeFormsClient({f["id"]: f for f in forms})
            return ProcessingTasks(client, work), client

        return factory

    def test_reports_stranded_forms_without_writing(self, make_tasks):
        tasks, client = make_tasks([
            processing_form(id="proc-1", status="RUNNING"),
            processing_form(id="proc-2", status="PENDING"),
            processing_form(id="proc-3", status="DONE"),
        ])

        candidates = tasks.reconcile()

        assert sorted(form.id() for form in candidates) == ["proc-1", "proc-2"]
        assert client.mutations.updates == [], "a dry run must not write"

    def test_apply_marks_them_as_errors(self, make_tasks):
        tasks, client = make_tasks([processing_form(id="proc-1", status="RUNNING")])

        tasks.reconcile(apply=True)

        assert client.statuses == ["ERROR"]

    def test_locally_running_tasks_are_protected(self, make_tasks):
        tasks, client = make_tasks([processing_form(id="proc-1", status="RUNNING")])
        tasks.tasks.tasks.append(Task(None, None, Form(processing_form(id="proc-1"))))

        assert tasks.reconcile(apply=True) == []
        assert client.mutations.updates == []

    def test_targeting_specific_ids(self, make_tasks):
        tasks, client = make_tasks([
            processing_form(id="proc-1", status="RUNNING"),
            processing_form(id="proc-2", status="RUNNING"),
        ])

        candidates = tasks.reconcile(pids=["proc-1"], apply=True)

        assert [form.id() for form in candidates] == ["proc-1"]
        assert [u["id"] for u in client.mutations.updates] == ["proc-1"]

    def test_recently_touched_forms_are_filtered_out(self, make_tasks):
        from datetime import datetime

        recent = int(datetime.now().timestamp() * 1000)
        tasks, _ = make_tasks([
            processing_form(id="proc-old", status="RUNNING", mtime=MTIME),
            processing_form(id="proc-fresh", status="RUNNING", mtime=recent),
        ])

        candidates = tasks.reconcile(older_than=timedelta(hours=1))

        assert [form.id() for form in candidates] == ["proc-old"]

    def test_a_form_without_mtime_is_never_reported(self, make_tasks):
        stale = processing_form(id="proc-1", status="RUNNING")
        del stale["mtime"]
        tasks, _ = make_tasks([stale])

        assert tasks.reconcile(older_than=timedelta(hours=1)) == []
        assert [form.id() for form in tasks.reconcile()] == ["proc-1"]


class TestProcessingApp:
    """The FastAPI wrapper: routes and bearer-token protection."""

    @pytest.fixture
    def make_app(self, monkeypatch):
        def factory(token=None):
            if token is None:
                monkeypatch.delenv("CE_FORMS_TASK_TOKEN", raising=False)
            else:
                monkeypatch.setenv("CE_FORMS_TASK_TOKEN", token)

            # `Processing` mounts its router on a module-level FastAPI app, so a
            # fresh import is required for each configuration under test.
            import importlib

            import py_ce_forms_api.processing.processing as processing_module

            processing_module = importlib.reload(processing_module)

            async def work(task):
                pass

            return processing_module.Processing(
                FakeCeFormsClient({"proc-1": processing_form()}), work
            )

        return factory

    def test_status_route_is_open_without_a_token(self, make_app):
        from fastapi.testclient import TestClient

        processing = make_app()
        response = TestClient(processing.get_app()).get("/")

        assert response.status_code == 200
        assert response.json() == {"length": 0, "maxLength": 10}

    def test_token_is_enforced_when_configured(self, make_app):
        from fastapi.testclient import TestClient

        processing = make_app(token="secret")
        http = TestClient(processing.get_app())

        assert http.get("/").status_code == 403  # no Authorization header
        assert http.get("/", headers={"Authorization": "Bearer wrong"}).status_code == 401
        assert http.get("/", headers={"Authorization": "Bearer secret"}).status_code == 200

    def test_startup_does_not_reconcile(self, make_app):
        """Several instances share one endpoint: an automatic sweep would kill them."""
        from fastapi.testclient import TestClient

        processing = make_app()
        client = processing.tasks.client

        with TestClient(processing.get_app()):
            pass

        assert client.mutations.updates == []
