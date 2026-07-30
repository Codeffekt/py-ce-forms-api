## ADDED Requirements

### Requirement: Terminal status is guaranteed

`Task.run()` SHALL NOT return without having attempted to write a terminal status (`DONE`, `ERROR` or `CANCELED`) to the processing form. This holds for every exit path, including exits by `BaseException`.

#### Scenario: The user function completes normally
- **WHEN** the function passed to the task returns without raising
- **THEN** the form status is `DONE`

#### Scenario: The user function raises
- **WHEN** the function raises any `Exception`
- **THEN** the form status is `ERROR` and the exception message is appended to the form message

#### Scenario: The task is cancelled from outside
- **WHEN** the asyncio task running `Task.run()` receives a `CancelledError` it did not originate
- **THEN** the form status is `CANCELED`
- **AND** the `CancelledError` is re-raised so the cancellation is not suppressed

#### Scenario: The user function raises a BaseException
- **WHEN** the function raises a `BaseException` that is neither `CancelledError` nor one of the interpreter-level interrupts below
- **THEN** the form status is `ERROR`

#### Scenario: The user function raises KeyboardInterrupt or SystemExit
- **WHEN** the function raises `KeyboardInterrupt` or `SystemExit`
- **THEN** the form status is `CANCELED`, because asyncio re-raises those into the event loop and hands the awaiting task a `CancelledError` instead of the original exception
- **AND** the original exception still propagates out of the event loop

#### Scenario: No terminal status was reached by any known path
- **WHEN** `Task.run()` is about to return and no terminal status has been recorded
- **THEN** the status `ERROR` is written with a message stating the task terminated without a final status

### Requirement: The first terminal status is final

Once a terminal status has been recorded for a task, the system SHALL ignore every subsequent status write, terminal or not. Ignored writes SHALL be logged and SHALL NOT raise.

#### Scenario: Completion cannot overwrite a cancellation
- **WHEN** a task is cancelled while running a function that does not yield to the event loop, and that function later runs to completion
- **THEN** the form status remains `CANCELED` and is not overwritten by `DONE`

#### Scenario: Progress cannot overwrite an error
- **WHEN** `Task.update()` is called after `Task.error()`
- **THEN** the form status remains `ERROR` and is not reset to `RUNNING`

#### Scenario: Concurrent terminal writes from two threads
- **WHEN** a cancellation issued from the FastAPI thread pool and a completion issued from the event loop race to write a terminal status
- **THEN** exactly one terminal status reaches the API and the other write is ignored

### Requirement: Terminal status writes are retried

Writing a terminal status SHALL be retried with backoff when the underlying API call fails. Non-terminal progress writes SHALL NOT be retried. The finalisation path SHALL contain no `await`, so that it completes even while the surrounding task is being cancelled.

#### Scenario: A transient API failure at completion time
- **WHEN** the mutation writing `DONE` fails once and then succeeds
- **THEN** the form status ends as `DONE`

#### Scenario: The API stays unavailable
- **WHEN** every retry attempt of a terminal status write fails
- **THEN** the failure is logged and no exception escapes `Task.run()`

#### Scenario: A progress write fails
- **WHEN** the mutation writing a `RUNNING` progress update fails
- **THEN** it is not retried and the task continues

### Requirement: Explicit completion via `done()`

`Task` SHALL expose `done(message: str | None = None)`, which records `DONE` as the terminal status and appends `message` to the form message when provided. The method SHALL be idempotent and SHALL NOT be mandatory: a function returning without calling it still ends as `DONE`.

#### Scenario: The function completes explicitly
- **WHEN** the function calls `task.done("all records processed")` and then returns
- **THEN** the form status is `DONE` and the message contains `all records processed`
- **AND** the automatic completion at the end of `run()` writes nothing further

#### Scenario: `done()` is called twice
- **WHEN** `task.done()` is called a second time
- **THEN** the second call is ignored and no additional mutation is sent

#### Scenario: `done()` after an error
- **WHEN** `task.done()` is called after `task.error("bad input")`
- **THEN** the form status remains `ERROR`

#### Scenario: Work continues after `done()`
- **WHEN** the function calls `task.done()` and then calls `task.update("more")`
- **THEN** the update is ignored and the status remains `DONE`

### Requirement: Cancellation crosses the thread boundary safely

`Task.cancel()` is invoked from the FastAPI thread pool while the task runs on the event loop. It SHALL record `CANCELED` and SHALL request the asyncio cancellation through the event loop rather than calling `cancel()` directly on the task object.

#### Scenario: Cancelling a running task
- **WHEN** `Task.cancel()` is called on a task whose asyncio task exists
- **THEN** the form status is `CANCELED`
- **AND** the asyncio cancellation is scheduled on the event loop that owns the task

#### Scenario: Cancelling before the work has started
- **WHEN** `Task.cancel()` is called in the window between the task being registered in the pool and its asyncio task being created
- **THEN** the form status is `CANCELED` and no `AttributeError` is raised
- **AND** the subsequent completion of the work does not overwrite `CANCELED`

### Requirement: The pool never loses a task

`TaskPool` SHALL keep a strong reference to every asyncio task it schedules, and SHALL free the slot for every task regardless of how it ended.

#### Scenario: A detached task is not garbage collected
- **WHEN** `TaskPool.run()` schedules a background task
- **THEN** a strong reference to it is held until it completes

#### Scenario: The `Task` object cannot be constructed
- **WHEN** constructing the `Task` raises
- **THEN** the error is reported without raising `UnboundLocalError` and the slot is freed

#### Scenario: A cancelled task frees its slot and propagates
- **WHEN** a scheduled task ends with `CancelledError`
- **THEN** the slot is freed
- **AND** the `CancelledError` is re-raised so the cancellation is not suppressed

### Requirement: A synchronous task function runs off the event loop

`TaskPool` SHALL inspect the task function it was given. A coroutine function SHALL be scheduled on the event loop as today. A plain function SHALL be scheduled through `asyncio.to_thread`, so that blocking work never freezes the event loop and the server keeps serving requests, including `/cancel`.

#### Scenario: A blocking task function does not freeze the server
- **WHEN** the processing is configured with a plain `def` function that blocks without yielding
- **THEN** the function runs off the event loop
- **AND** the server keeps answering requests while it runs

#### Scenario: A coroutine task function is unaffected
- **WHEN** the processing is configured with an `async def` function
- **THEN** it is scheduled on the event loop exactly as before

#### Scenario: A synchronous function reaches a terminal status
- **WHEN** a plain `def` task function returns
- **THEN** the form status is `DONE`

#### Scenario: A synchronous function that raises
- **WHEN** a plain `def` task function raises
- **THEN** the form status is `ERROR` and the exception message is reported

#### Scenario: Cancelling a synchronous task
- **WHEN** `cancel()` is called on a task running a plain `def` function
- **THEN** the form status is `CANCELED` and the pool slot is freed
- **AND** any status write attempted by the still-running thread afterwards is ignored

### Requirement: Blocking work can be offloaded from a coroutine

`Task` SHALL expose `run_blocking(fn, *args, **kwargs)`, an awaitable helper that runs `fn` off the event loop and returns its result, so that a coroutine task function can offload a one-off blocking call without the caller needing to know `asyncio`.

#### Scenario: Offloading a blocking call
- **WHEN** an `async def` task function awaits `task.run_blocking(blocking_fn, arg)`
- **THEN** `blocking_fn` runs off the event loop and its return value is produced by the await

#### Scenario: The offloaded call raises
- **WHEN** the offloaded function raises
- **THEN** the exception propagates to the awaiting task function, which may handle it or let the task end in `ERROR`

### Requirement: Server shutdown finalises in-flight tasks

`TaskPool` SHALL expose `shutdown()`, which writes `CANCELED` to every task still in flight with a message identifying a server shutdown. `Processing` SHALL invoke it on the application shutdown event.

#### Scenario: Shutdown with running tasks
- **WHEN** the application shutdown event fires while two tasks are in flight
- **THEN** both forms end with status `CANCELED` and a message identifying the shutdown

#### Scenario: Shutdown with an already finished task
- **WHEN** the shutdown event fires and a task has already reached `DONE`
- **THEN** that form's status is unchanged

### Requirement: Explicit reconciliation of stranded forms

`ProcessingTasks` SHALL expose `reconcile(pids=None, older_than=None, apply=False)`, which finds processing forms left in `RUNNING` or `PENDING` and can mark them `ERROR`. It SHALL default to reporting without writing, SHALL exclude forms currently held by the local pool, and SHALL NEVER be called automatically by the SDK.

Because several server instances share one endpoint, `older_than` SHALL filter candidates on the form's `mtime` meta field, which every progress update refreshes. This is a heuristic and not a proof of death: a live task that never reports progress keeps a stale `mtime`.

#### Scenario: Inspecting stranded forms
- **WHEN** `reconcile()` is called with default arguments
- **THEN** the candidate forms in `RUNNING` or `PENDING` are returned
- **AND** no mutation is sent

#### Scenario: Applying the reconciliation
- **WHEN** `reconcile(apply=True)` is called
- **THEN** every candidate form is set to `ERROR` with a message stating it was interrupted by a restart

#### Scenario: Locally running tasks are protected
- **WHEN** a candidate form's id matches a task held by the local pool
- **THEN** it is excluded from the candidates whatever the value of `apply`

#### Scenario: Targeting specific forms
- **WHEN** `reconcile(pids=["proc-1"], apply=True)` is called
- **THEN** only `proc-1` is considered

#### Scenario: Recently active forms are filtered out
- **WHEN** `reconcile(older_than=<duration>)` is called and a candidate form's `mtime` is more recent than the duration
- **THEN** that form is excluded from the candidates

#### Scenario: A form with no modification time
- **WHEN** a candidate form has no `mtime` and `older_than` is set
- **THEN** the form is excluded from the candidates rather than assumed dead

#### Scenario: Reconciliation is never automatic
- **WHEN** a `Processing` server starts up
- **THEN** no reconciliation is performed
