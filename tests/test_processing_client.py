import pytest
import responses as responses_lib

from py_ce_forms_api import Form, ProcessingClient

from .conftest import make_block, make_form_dict

SERVER = "http://worker.test:8000"


def processing_payload(status="IDLE", root="forms-processing", server=SERVER):
    return make_form_dict(
        id="proc-1",
        root=root,
        blocks=[make_block("status", "text", status), make_block("message", "text", "")],
        fields={"endpoint": make_form_dict(
            id="endpoint-1", root="forms-endpoint",
            blocks=[make_block("server", "text", server)],
        )},
    )


@pytest.fixture
def api(fake_client):
    def factory(status="IDLE", **kwargs):
        return fake_client(
            call_form_query=processing_payload(status=status, **kwargs),
            call_mutation=processing_payload(status=status, **kwargs),
        )

    return factory


class TestRetrieval:
    def test_loads_the_processing_form_with_sub_forms(self, api):
        client = api()

        processing = ProcessingClient(client, "proc-1")

        assert isinstance(processing.processing_data, Form)
        assert client.last_call["id"] == "proc-1"
        assert client.last_call["query"]["extMode"] is True

    def test_rejects_a_form_from_another_root(self, api):
        with pytest.raises(Exception, match="instead of forms-processing"):
            ProcessingClient(api(root="other-root"), "proc-1")

    def test_missing_endpoint_sub_form_raises(self, fake_client):
        payload = processing_payload()
        del payload["fields"]

        with pytest.raises(Exception, match="has no subform endpoint"):
            ProcessingClient(fake_client(call_form_query=payload), "proc-1")


class TestIsStarted:
    @pytest.mark.parametrize("status,expected", [
        ("PENDING", True), ("RUNNING", True), ("DONE", False), ("ERROR", False), ("IDLE", False),
    ])
    def test_is_started(self, api, status, expected):
        assert ProcessingClient(api(status=status), "proc-1").is_started() is expected


class TestStart:
    def test_start_marks_pending_and_calls_the_worker(self, api, mocked_responses):
        client = api(status="DONE")
        mocked_responses.get(f"{SERVER}/processing/proc-1", body=b"started", status=200)

        result = ProcessingClient(client, "proc-1").start()

        assert result == b"started"
        assert client.last_call["call"] == "call_mutation"
        mutated = client.last_call["mutation"]["elts"][0]
        assert mutated["content"]["status"]["value"] == "PENDING"

    def test_start_is_a_no_op_when_already_running(self, api, mocked_responses):
        client = api(status="RUNNING")

        processing = ProcessingClient(client, "proc-1")
        assert processing.start() is processing.processing_data
        assert [c["call"] for c in client.calls] == ["call_form_query"]

    def test_worker_error_is_reported(self, api, mocked_responses):
        mocked_responses.get(f"{SERVER}/processing/proc-1", status=500, body=b"nope")

        with pytest.raises(Exception, match="Call api error"):
            ProcessingClient(api(status="DONE"), "proc-1").start()

    def test_pending_is_written_before_the_call(self, api, mocked_responses):
        """The endpoint may already have written RUNNING when it returns."""
        client = api(status="DONE")
        processing = ProcessingClient(client, "proc-1")
        seen = {}

        def observe(request):
            seen["status"] = processing.processing_data.get_value("status")
            return (200, {}, "started")

        mocked_responses.add_callback(
            responses_lib.GET, f"{SERVER}/processing/proc-1", callback=observe)

        processing.start()

        assert seen["status"] == "PENDING"

    def test_a_failed_start_rolls_the_form_forward_to_error(self, api, mocked_responses):
        client = api(status="DONE")
        mocked_responses.get(f"{SERVER}/processing/proc-1", status=500, body=b"nope")

        processing = ProcessingClient(client, "proc-1")
        with pytest.raises(Exception, match="Call api error"):
            processing.start()

        mutations = [c for c in client.calls if c["call"] == "call_mutation"]
        assert len(mutations) == 2, "PENDING then the rollback"
        assert processing.processing_data.get_value("status") == "ERROR"
        assert "failed to start" in processing.processing_data.get_value("message")

    def test_the_form_can_be_started_again_after_a_failure(self, api, mocked_responses):
        client = api(status="DONE")
        mocked_responses.get(f"{SERVER}/processing/proc-1", status=500, body=b"nope")

        processing = ProcessingClient(client, "proc-1")
        with pytest.raises(Exception):
            processing.start()

        assert processing.is_started() is False, \
            "a form stuck in PENDING could never be started again"

    def test_a_successful_start_writes_nothing_after_the_call(self, api, mocked_responses):
        client = api(status="DONE")
        mocked_responses.get(f"{SERVER}/processing/proc-1", body=b"started", status=200)

        ProcessingClient(client, "proc-1").start()

        # The endpoint returns as soon as the task is scheduled; the server may
        # already have written RUNNING, which a late write would overwrite.
        assert [c["call"] for c in client.calls] == ["call_form_query", "call_mutation"]


class TestCancel:
    def test_cancel_calls_the_worker_when_running(self, api, mocked_responses):
        mocked_responses.get(f"{SERVER}/cancel/proc-1", body=b"cancelled", status=200)

        assert ProcessingClient(api(status="RUNNING"), "proc-1").cancel() == b"cancelled"

    def test_cancel_is_a_no_op_when_not_running(self, api):
        client = api(status="DONE")

        processing = ProcessingClient(client, "proc-1")
        assert processing.cancel() is processing.processing_data
        assert [c["call"] for c in client.calls] == ["call_form_query"]

    def test_cancel_never_writes_pending(self, api, mocked_responses):
        client = api(status="RUNNING")
        mocked_responses.get(f"{SERVER}/cancel/proc-1", body=b"cancelled", status=200)

        ProcessingClient(client, "proc-1").cancel()

        # The server owns the CANCELED transition.
        assert [c["call"] for c in client.calls] == ["call_form_query"]

    def test_a_failed_cancel_leaves_the_status_untouched(self, api, mocked_responses):
        client = api(status="RUNNING")
        mocked_responses.get(f"{SERVER}/cancel/proc-1", status=500, body=b"unknown")

        processing = ProcessingClient(client, "proc-1")
        with pytest.raises(Exception, match="Call api error"):
            processing.cancel()

        assert [c["call"] for c in client.calls] == ["call_form_query"], \
            "a failed cancel must not degrade the form to an unrecoverable PENDING"
        assert processing.processing_data.get_value("status") == "RUNNING"


class TestStatus:
    def test_status_pings_the_worker_root(self, api, mocked_responses):
        mocked_responses.get(f"{SERVER}/", body=b"{}", status=200)

        processing = ProcessingClient(api(status="RUNNING"), "proc-1")

        assert processing.status() is processing.processing_data
        assert mocked_responses.calls[0].request.url.startswith(SERVER)
