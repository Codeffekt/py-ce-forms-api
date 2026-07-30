# Py Ce Forms Api

## Quickstart

### Introduction

The `py-ce-forms-api` module allows you to interact with the CeForms API for form management. Before getting started, ensure you have obtained the necessary credentials:

- **CE_FORMS_BASE_URL**: The base URL for the CeForms API.
- **CE_FORMS_TOKEN**: Your authentication token for accessing the CeForms API.
 
### Installation

You can install `py-ce-forms-api` via pip:

```bash
pip install py-ce-forms-api
```

### Usage

Once installed, you can start using the module in your Python code:

```python
from py_ce_forms_api import CeFormsClient

# Initialize the client
ce_forms_client = CeFormsClient(base_url=<CE_FORMS_BASE_URL>, token=<CE_FORMS_TOKEN>)

# Example: Retrieve a list of forms
forms = ce_forms_client.query().with_sub_forms(False).with_limit(10).call()
for form in forms:
    print(form)
```

Replace <CE_FORMS_BASE_URL> and <CE_FORMS_TOKEN> with your actual base URL and authentication token, respectively.

## Processing tasks

A processing task reports its progress by writing a status on a `forms-processing`
form: `PENDING` → `RUNNING` → `DONE` | `ERROR` | `CANCELED`.

### Writing a task function

The library adapts to how you declare it:

```python
# Blocking work — declare it `def`, the library runs it off the event loop
def import_csv(task: Task):
    rows = pandas.read_csv(path)          # blocking, would freeze the server
    task.update(f"{len(rows)} rows read")
    task.done("import complete")

# Genuinely asynchronous work — declare it `async def`
async def poll_remote(task: Task):
    async with httpx.AsyncClient() as http:
        await http.get(url)
    task.done()

# Mixed — offload the blocking part with run_blocking()
async def mixed(task: Task):
    rows = await task.run_blocking(pandas.read_csv, path)
    task.update(f"{len(rows)} rows read")
```

Declaring blocking work `async def` is the one thing to avoid: it runs on the
event loop and freezes the whole server for its duration, including the
`/cancel` route that could have stopped it.

`task.done(message)` is optional — a function that simply returns still ends as
`DONE`. Use it to close explicitly with a final message. Once any terminal status
is recorded it is final: a later `update()` is ignored, and a completion can
never overwrite a cancellation.

### Terminal status guarantee

`Task.run()` never returns without writing a terminal status: a raised
exception ends in `ERROR`, a cancellation in `CANCELED`, and terminal writes are
retried when the API call fails. Stopping the server finalises every in-flight
task as `CANCELED`.

Two cases remain uncovered, by design:

- A task function that yields to the loop but never finishes stays `RUNNING`.
  There is no timeout: the server is still alive, so `cancel()` is the recourse.
- A process killed outright (SIGKILL, OOM, hardware failure) writes nothing.
  Use `reconcile()`.

### Recovering stranded forms

```python
processing = ProcessingTasks(client, my_task)

# Report only — nothing is written
candidates = processing.reconcile(older_than=timedelta(hours=2))

# Then fail the ones you checked
processing.reconcile(pids=[form.id() for form in candidates], apply=True)
```

`reconcile()` is never called by the SDK. Several server instances usually share
one endpoint, and no query can tell a dead task from one running elsewhere, so
it reports without writing unless you pass `apply=True`. The `older_than` filter
uses the form's `mtime`, which every `update()` refreshes — a task that never
reports progress keeps a stale `mtime` and would be listed, so pick a threshold
well above your slowest update interval.

See [examples/simple_processing_task](examples/simple_processing_task) and
[examples/reconcile_processing](examples/reconcile_processing).

## SDK Documentation

See *[CeForms SDK for Python](https://py-ce-forms-api.readthedocs.io/en/latest/index.html)*

## Development

 > pip install -e .

### Testing

Set up the environment and run the suite:

```bash
make venv   # python3 -m venv .venv + requirements-dev.txt + pip install -e .
make test   # pytest
make test-cov
```

No test requires a CeForms backend: HTTP is mocked. See [tests/README.md](tests/README.md).

### package building

 > python3 setup.py sdist bdist_wheel

### package publishing

 > python3 -m twine upload --repository <repository> dist/*
