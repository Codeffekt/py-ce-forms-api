import asyncio
from datetime import datetime, timedelta
from ..client import CeFormsClient
from ..form import Form
from .task_pool import TaskPool

class ProcessingTasks():
    """
    This is the entry point used when you need to perform a
    long/async processing task
    """

    #: Root holding the processing forms.
    PROCESSING_ROOT = "forms-processing"

    #: Statuses a task can be stranded in when its process died.
    STRANDED_STATUSES = ("RUNNING", "PENDING")

    #: Upper bound of the reconciliation query. Truncation is reported.
    RECONCILE_LIMIT = 1000

    def __init__(self, client: CeFormsClient, func) -> None:
        self.client = client
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

    def shutdown(self):
        """Finalise every in-flight task as CANCELED.

        Wired to the application shutdown event by :class:`Processing`.
        """
        self.tasks.shutdown()

    def reconcile(self, pids: list[str] | None = None,
                  older_than: timedelta | None = None,
                  apply: bool = False) -> list[Form]:
        """Find processing forms stranded in RUNNING or PENDING, and optionally fail them.

        A process killed by SIGKILL, an OOM or a machine failure cannot write a
        terminal status, so its form stays non terminal forever. This is the only
        way to recover from that, and it is never called by the SDK itself.

        .. warning::

            Several server instances usually share one endpoint, and no query can
            tell a dead task from one running on another instance. Applying a
            reconciliation blindly will fail live tasks. Run it without ``apply``
            first, check the candidates, then apply.

        ``older_than`` filters on the form's ``mtime``, which every progress
        update refreshes — an implicit heartbeat that costs nothing. It is a
        heuristic, not a proof of death: a live task that never calls
        :meth:`Task.update` keeps a stale ``mtime`` and would be reported. Pick a
        threshold well above the slowest update interval of your tasks. Forms
        carrying no ``mtime`` at all are never reported.

        Args:
            pids (list[str]): restrict the scan to these processing ids.
            older_than (timedelta): only report forms untouched for longer than this.
            apply (bool): write the ERROR status. Defaults to reporting only.

        Returns:
            list[Form]: the candidate forms, as they were before any write.

        Example:

            >>> candidates = processing.reconcile(older_than=timedelta(hours=2))
            >>> [form.id() for form in candidates]
            ['proc-17']
            >>> processing.reconcile(pids=['proc-17'], apply=True)
        """
        candidates = [
            form for form in self.__query_stranded_forms()
            if self.__is_candidate(form, pids, older_than)
        ]

        if apply:
            for form in candidates:
                print(f'[ProcessingTasks]: reconciling {form.id()}')
                form.set_value("status", "ERROR")
                self.client.mutation().update_single(form.form)

        return candidates

    def _check_task_avaibility(self, pid: str):
        if self.tasks.have_processing(pid):
            raise Exception(f"A processing is already running {pid}.")

        if not self.tasks.have_free_slot():
            raise Exception('Too much processing, no more free slot available')

    def __query_stranded_forms(self):
        for status in self.STRANDED_STATUSES:
            res = (self.client.query()
                   .with_root(self.PROCESSING_ROOT)
                   .where("status", status)
                   .with_limit(self.RECONCILE_LIMIT)
                   .call())

            if res.total() > len(res):
                print(f'[ProcessingTasks]: {res.total()} forms in {status}, '
                      f'only the first {len(res)} are reported')

            yield from res.forms()

    def __is_candidate(self, form: Form, pids, older_than) -> bool:
        if pids is not None and form.id() not in pids:
            return False

        # A task held by this pool is alive by definition.
        if self.tasks.have_processing(form.id()):
            return False

        if older_than is None:
            return True

        mtime = form.mtime()
        if mtime is None:
            # No modification time means no evidence of death.
            return False

        return mtime < datetime.now() - older_than
