"""End-to-end paths through the real stack, with only the HTTP layer mocked.

These catch wiring regressions that the fake-client tests cannot see: URL
building, payload envelope, auth header and result wrapping, all at once.
"""

import json

import pytest

from py_ce_forms_api import CeFormsClient
from py_ce_forms_api.cli.form_info import FormInfo

from .conftest import BASE_URL, TOKEN, make_block, make_form_dict


@pytest.fixture
def client():
    return CeFormsClient(base_url=BASE_URL, token=TOKEN)


def api_url():
    return f"{BASE_URL}/api"


def bodies(mocked_responses):
    return [json.loads(call.request.body) for call in mocked_responses.calls]


def test_query_a_root_and_read_the_forms(client, mocked_responses):
    mocked_responses.post(api_url(), status=200, json={
        "elts": [make_form_dict(id="form-1", blocks=[make_block("name", "text", "hello")])],
        "total": 1, "limit": 10, "offset": 0,
    })

    res = client.query().with_root("test-root").with_limit(10).call()
    forms = list(res.forms())

    assert res.total() == 1
    assert forms[0].get_value("name") == "hello"

    body = bodies(mocked_responses)[0]
    assert body["__class"] == "PublicForms"
    assert body["call"]["function"] == "getFormsQuery"
    assert body["call"]["params"][0]["queryFields"][0]["value"] == "test-root"


def test_paginated_iteration_issues_one_request_per_page(client, mocked_responses):
    from py_ce_forms_api import FormsResIterable

    for offset, ids in [(0, ["a", "b"]), (2, ["c"])]:
        mocked_responses.post(api_url(), status=200, json={
            "elts": [make_form_dict(id=i) for i in ids],
            "total": 3, "limit": 2, "offset": offset,
        })

    query = client.query().with_root("test-root").with_limit(2)
    ids = [form.id() for res in FormsResIterable(query) for form in res.forms()]

    assert ids == ["a", "b", "c"]
    assert [b["call"]["params"][0]["offset"] for b in bodies(mocked_responses)] == [0, 2]


def test_read_modify_write_round_trip(client, mocked_responses):
    stored = make_form_dict(id="form-1", blocks=[make_block("name", "text", "hello")])
    mocked_responses.post(api_url(), status=200, json=stored)   # getFormQuery
    mocked_responses.post(api_url(), status=200, json=stored)   # formMutation echo

    form = client.forms().get_form("form-1")
    form.set_value("name", "updated")
    client.mutation().update(form)

    get_body, update_body = bodies(mocked_responses)
    assert get_body["call"]["function"] == "getFormQuery"
    assert update_body["call"]["function"] == "formMutation"
    assert update_body["call"]["params"][0]["elts"][0]["content"]["name"]["value"] == "updated"


def test_upload_then_download_an_asset(client, mocked_responses, tmp_path):
    source = tmp_path / "note.txt"
    source.write_text("hello")

    mocked_responses.post(api_url(), status=200, json={"id": "bucket-1"})
    mocked_responses.post(f"{BASE_URL}/assets/upload/bucket-1", status=200,
                          json={"id": "asset-1", "mimetype": "text/plain", "name": "note.txt",
                                "originalname": "note.txt", "ref": "bucket-1"})
    mocked_responses.get(f"{BASE_URL}/assets/download/asset-1", status=200, body=b"hello")

    uploaded = client.assets().upload_file("my-ref", str(source))
    assert uploaded["id"] == "asset-1"

    assert client.assets().download_file("asset-1") == b"hello"
    assert all(c.request.headers["authorization"] == f"Bearer {TOKEN}"
               for c in mocked_responses.calls)


def test_api_errors_surface_as_api_error(client, mocked_responses):
    from py_ce_forms_api.api.exceptions import APIError

    mocked_responses.post(api_url(), status=403, json={"message": "forbidden"})

    with pytest.raises(APIError):
        client.query().with_root("test-root").call()


class TestCli:
    def test_form_info_summary(self, client, mocked_responses):
        mocked_responses.post(api_url(), status=200, json=make_form_dict(id="form-1"))

        summary = FormInfo(client, "form-1").get_summary()

        assert "form-1" in summary
        assert "test-root" in summary

    def test_form_info_root(self, client, mocked_responses):
        mocked_responses.post(api_url(), status=200, json=make_form_dict(id="form-1"))
        mocked_responses.post(api_url(), status=200, json=make_form_dict(
            id="test-root", blocks=[make_block("name", "text", None)]))

        rendered = FormInfo(client, "form-1").get_root()

        assert "test-root" in rendered
        assert "['name']" in rendered
