"""Recover processing forms stranded by a server that died without reporting.

A process killed by SIGKILL, an OOM or a machine failure cannot write a terminal
status, so its form stays RUNNING (or PENDING) forever: it can no longer be
started, nor cancelled. This is the only way out.

Beware: several server instances usually share one endpoint, and no query can
tell a dead task from one running on another instance. Always inspect the
candidates before applying.

    > python main.py report
    > python main.py report 2          # only forms untouched for 2 hours
    > python main.py apply proc-17     # fail these ids for good
"""
import sys
from datetime import timedelta
from py_ce_forms_api import *


async def noop_task(task: Task):
    """Reconciliation never runs a task; the pool just needs a function."""


def report(hours=None):
    processing = ProcessingTasks(CeFormsClient(), noop_task)
    older_than = timedelta(hours=hours) if hours is not None else None

    candidates = processing.reconcile(older_than=older_than)

    if not candidates:
        print("No stranded processing form.")
        return

    print(f"{len(candidates)} stranded form(s) — nothing written:")
    for form in candidates:
        print(f"  {form.id()}  {form.get_value('status')}  last modified {form.mtime()}")
    print("\nCheck none of these runs on another instance, then:")
    print(f"  python main.py apply {' '.join(f.id() for f in candidates)}")


def apply(pids):
    processing = ProcessingTasks(CeFormsClient(), noop_task)

    applied = processing.reconcile(pids=pids, apply=True)

    print(f"{len(applied)} form(s) marked as ERROR:")
    for form in applied:
        print(f"  {form.id()}")


if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) >= 1 and args[0] == "report":
        report(int(args[1]) if len(args) > 1 else None)
    elif len(args) >= 2 and args[0] == "apply":
        apply(args[1:])
    else:
        print('Invalid arguments: report [<hours>] | apply <processing id>...')
