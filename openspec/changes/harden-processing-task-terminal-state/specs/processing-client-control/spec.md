## ADDED Requirements

### Requirement: A failed start leaves the form restartable

`ProcessingClient.start()` marks the form `PENDING` before calling the processing endpoint, because the server may already have written `RUNNING` by the time the call returns. When the call fails, the client SHALL roll the form forward to `ERROR` carrying the failure message, so that `is_started()` reports `False` and the form can be started again.

#### Scenario: The processing endpoint is unreachable
- **WHEN** `start()` is called and the HTTP call to the processing endpoint fails
- **THEN** the form status is `ERROR` and its message identifies the failed start
- **AND** a subsequent `start()` is accepted rather than refused as already started

#### Scenario: The server refuses the start
- **WHEN** the endpoint answers with an error because a processing is already running or no slot is free
- **THEN** the form status is `ERROR` and the reason is reported to the caller

#### Scenario: A successful start is not overwritten
- **WHEN** `start()` succeeds and the server has already written `RUNNING`
- **THEN** the client writes no status after the call returns, leaving `RUNNING` in place

#### Scenario: Starting an already started processing
- **WHEN** `start()` is called on a form whose status is `PENDING` or `RUNNING`
- **THEN** no call is made and the current processing data is returned

### Requirement: Cancelling does not degrade the form status

`ProcessingClient.cancel()` SHALL NOT write `PENDING`. The server owns the `CANCELED` transition. When the cancel call fails, the form status SHALL be left untouched and the error SHALL be raised to the caller.

#### Scenario: Successful cancellation
- **WHEN** `cancel()` is called on a running processing
- **THEN** the client writes no status itself and the server sets the form to `CANCELED`

#### Scenario: Cancelling an unknown processing
- **WHEN** `cancel()` is called and the endpoint answers with an error because the task is unknown to the server
- **THEN** the form status is unchanged
- **AND** the error is raised to the caller

#### Scenario: Cancelling a processing that is not started
- **WHEN** `cancel()` is called on a form whose status is already terminal
- **THEN** no call is made and the current processing data is returned
