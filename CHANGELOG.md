## [0.1.18]
 - fix: a processing task always reaches a terminal status. `CancelledError` and other `BaseException` no longer escape unreported, terminal writes are retried, and a last-resort `finally` fails the form rather than leaving it `RUNNING`
 - fix: the first terminal status wins. A completion can no longer overwrite a cancellation, nor an `update()` reset a reported error
 - fix: `Task.cancel()` schedules the asyncio cancellation through the owning loop instead of touching the task from the FastAPI thread pool, and no longer raises when the work has not started yet
 - fix: `TaskPool` keeps a strong reference to the tasks it schedules, so the garbage collector cannot drop one mid-execution
 - fix: a failing `ProcessingClient.start()` marks the form `ERROR` instead of leaving it `PENDING`, a state it could never be started or cancelled out of
 - fix: `ProcessingClient.cancel()` no longer writes `PENDING`; a failed cancel leaves the status untouched
 - feat: a task function declared `def` is run off the event loop, so blocking work no longer freezes the server. It used to raise `TypeError: a coroutine was expected`
 - feat: add `Task.done(message)` to terminate a task explicitly, and `Task.run_blocking(fn, ...)` to offload a blocking call from an `async def` task function
 - feat: add `ProcessingTasks.reconcile(pids, older_than, apply)` to recover forms stranded by a killed process, reporting without writing by default
 - feat: stopping the server finalises every in-flight task as `CANCELED`
 - test: add the pytest test suite (`make test`), no backend required
 - fix: the distribution no longer ships a top-level `tests` package, which would land in site-packages and shadow another project's `tests`
 - fix: FormsRes is now iterable, which unlocks JsonDump.res_to_str/res_to_file and MdDump.res_to_str
 - fix: FormBlock.set_value stores a datetime in milliseconds, so the timestamp round-trip is correct

## [0.1.17]
 - feat: add support for query nodes
 - feat: CE_FORMS_TASK_TOKEN used to auth processing tasks
 - feat: add save roots examples

## [0.1.16]
 - feat: add form copy
 - feat: add form readonly on all blocks

## [0.1.15]
 - feat: support for old deprecated project
 - feat: support for json dump

## [0.1.14]
 - feat: retrieve assets with some originalname value

## [0.1.13]
 - fix: error when asset has no value
 - feat: add delete single form

## [0.1.12]
 - fix: missing await for fastpi route processing

## [0.1.11]
 - Add local storage for assets

## [0.1.10]
 - Add delete asset array

## [0.1.9]
 - Add processing tasks to simplify the processing calls and provide a processing sync

## [0.1.8]
 - Get block root

## [0.1.7]
 - Add support for str and BufferedStream in upload
 - Add form roots 
 - Add cli

## [0.1.6]
 - Add support for AssetElt
 - Add processing run awaitable to call process task from command line
 - Add support for assets array

## [0.1.5]
 - FIX : manage correctly cancelled task in processing
 - FIX : better error messages and exception handling in processing

## [0.1.4]
 - Requirements : Python 3.10
