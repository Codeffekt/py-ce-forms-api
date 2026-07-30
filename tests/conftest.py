"""Shared fixtures for the py_ce_forms_api test suite.

No test in this suite reaches the network: HTTP is intercepted with `responses`,
and anything above the transport layer talks to `FakeAPIClient` (see below).
"""

import pytest
import responses as responses_lib

from py_ce_forms_api import APIClient

BASE_URL = "https://ceforms.test/api-root"
TOKEN = "test-token"

CE_FORMS_ENV_VARS = (
    "CE_FORMS_BASE_URL",
    "CE_FORMS_TOKEN",
    "CE_FORMS_DIR_PATH",
    "CE_FORMS_TASK_PORT",
    "CE_FORMS_TASK_TOKEN",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Keep a developer's real CE_FORMS_* environment out of the tests."""
    for var in CE_FORMS_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def mocked_responses():
    """`responses` request mock, asserting every registered mock was used."""
    with responses_lib.RequestsMock() as rsps:
        yield rsps


@pytest.fixture
def api_client(tmp_path):
    return APIClient(base_url=BASE_URL, token=TOKEN, dir_path=str(tmp_path / "assets"))


class FakeAPIClient:
    """Stand-in for `APIClient` that records calls and replays canned answers.

    Higher level classes (queries, mutations, assets, ...) only ever reach the
    backend through the `call_*` methods, so recording them is enough to assert
    the payload a given fluent API produces.
    """

    def __init__(self, dir_path=None, **replies):
        self.calls = []
        self.replies = replies
        self.dir_path = dir_path

    def _record(self, name, **kwargs):
        self.calls.append({"call": name, **kwargs})
        reply = self.replies.get(name)
        if callable(reply):
            return reply(**kwargs)
        return reply

    @property
    def last_call(self):
        return self.calls[-1]

    # --- APIClient surface used by the library -------------------------------

    def get_dir_path(self):
        return self.dir_path

    def set_dir_path(self, dir_path):
        self.dir_path = dir_path

    def call_module(self, func, params, module_name):
        return self._record("call_module", func=func, params=params, module_name=module_name)

    def call_forms_query(self, params, module_name="Forms"):
        return self._record("call_forms_query", params=params, module_name=module_name)

    def call_forms_root_query(self, params, module_name="Forms"):
        return self._record("call_forms_root_query", params=params, module_name=module_name)

    def call_get_root(self, params, module_name="Forms"):
        return self._record("call_get_root", params=params, module_name=module_name)

    def call_form_query(self, id, query, module_name="Forms"):
        return self._record("call_form_query", id=id, query=query, module_name=module_name)

    def call_forms_query_array(self, id, field, query, module_name="Forms"):
        return self._record(
            "call_forms_query_array", id=id, field=field, query=query, module_name=module_name
        )

    def call_mutation(self, mutation, module_name="Forms"):
        return self._record("call_mutation", mutation=mutation, module_name=module_name)

    def call_upload(self, bucket_id, file_path, mimetype="text/plain"):
        return self._record(
            "call_upload", bucket_id=bucket_id, file_path=file_path, mimetype=mimetype
        )

    def call_upload_files(self, bucket_id, files):
        return self._record("call_upload_files", bucket_id=bucket_id, files=files)

    def call_download(self, id):
        return self._record("call_download", id=id)

    def self(self):
        return self._record("self")


@pytest.fixture
def fake_client():
    return FakeAPIClient


# --- form payloads -----------------------------------------------------------

CTIME = 1700000000000  # 2023-11-14 22:13:20 UTC
MTIME = 1700003600000


def make_block(field, type_, value=None, **extra):
    block = {"field": field, "type": type_, "value": value}
    block.update(extra)
    return block


def make_form_dict(id="form-1", root="test-root", blocks=None, **extra):
    """Build a raw form payload as returned by the CeForms backend."""
    content = {}
    for block in blocks or [make_block("name", "text", "hello")]:
        content[block["field"]] = block
    form = {
        "id": id,
        "root": root,
        "type": "form",
        "ctime": CTIME,
        "mtime": MTIME,
        "content": content,
    }
    form.update(extra)
    return form


@pytest.fixture
def block_factory():
    return make_block


@pytest.fixture
def form_factory():
    return make_form_dict


@pytest.fixture
def form_dict():
    """A form exercising every block type understood by `FormBlock`."""
    return make_form_dict(
        id="form-1",
        root="test-root",
        blocks=[
            make_block("name", "text", "hello"),
            make_block("count", "number", "42"),
            make_block("enabled", "boolean", "true"),
            make_block("date", "timestamp", CTIME),
            make_block("position", "coordinates", ["1.5", "2.5"]),
            make_block("photos", "assetArray", "photos-{$id}"),
            make_block("doc", "asset", {"id": "asset-1", "mimetype": "text/plain",
                                        "name": "doc.txt", "originalname": "original.txt",
                                        "ref": "bucket-1"}),
            make_block("parent", "form", None, root="other-root", ref="parent-ref"),
        ],
    )


@pytest.fixture
def forms_res_payload():
    """A `getFormsQuery` response body."""
    return {
        "elts": [make_form_dict(id="form-1"), make_form_dict(id="form-2")],
        "total": 2,
        "limit": 10,
        "offset": 0,
    }
