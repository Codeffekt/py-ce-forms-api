import json

import pytest
import responses

from py_ce_forms_api import APIClient
from py_ce_forms_api.api.bearer_auth import BearerAuth
from py_ce_forms_api.api.exceptions import APIError

from .conftest import BASE_URL, TOKEN


class TestConstruction:
    def test_explicit_arguments_win(self):
        client = APIClient(base_url="https://a.test", token="tok", dir_path="/tmp/x")
        assert client.base_url == "https://a.test"
        assert client.token == "tok"
        assert client.get_dir_path() == "/tmp/x"

    def test_falls_back_to_environment(self, monkeypatch):
        monkeypatch.setenv("CE_FORMS_BASE_URL", "https://env.test")
        monkeypatch.setenv("CE_FORMS_TOKEN", "env-token")
        monkeypatch.setenv("CE_FORMS_DIR_PATH", "/tmp/env")

        client = APIClient()

        assert client.base_url == "https://env.test"
        assert client.token == "env-token"
        assert client.get_dir_path() == "/tmp/env"

    def test_dir_path_is_optional(self):
        assert APIClient(base_url="https://a.test", token="tok").get_dir_path() is None

    @pytest.mark.parametrize(
        "kwargs",
        [{}, {"base_url": "https://a.test"}, {"token": "tok"}],
        ids=["nothing", "no-token", "no-base-url"],
    )
    def test_missing_credentials_raise(self, kwargs):
        with pytest.raises(TypeError):
            APIClient(**kwargs)

    def test_set_dir_path(self, api_client):
        api_client.set_dir_path("/tmp/other")
        assert api_client.get_dir_path() == "/tmp/other"


class TestBearerAuth:
    def test_sets_authorization_header(self):
        class Request:
            headers = {}

        request = BearerAuth("abc")(Request())
        assert request.headers["authorization"] == "Bearer abc"


class TestCallPayload:
    def test_call_posts_expected_envelope(self, api_client, mocked_responses):
        mocked_responses.post(f"{BASE_URL}/api", json={"ok": True}, status=200)

        result = api_client.call("PublicForms", "getFormsQuery", [{"limit": 1}])

        assert result == {"ok": True}
        request = mocked_responses.calls[0].request
        assert json.loads(request.body) == {
            "__class": "PublicForms",
            "call": {"function": "getFormsQuery", "params": [{"limit": 1}]},
        }
        assert request.headers["authorization"] == f"Bearer {TOKEN}"

    def test_empty_params_are_omitted(self, api_client, mocked_responses):
        mocked_responses.post(f"{BASE_URL}/api", json={}, status=200)

        api_client.call("PublicForms", "self", [])

        assert json.loads(mocked_responses.calls[0].request.body) == {
            "__class": "PublicForms",
            "call": {"function": "self"},
        }

    def test_call_module_prefixes_class_with_public(self, api_client, mocked_responses):
        mocked_responses.post(f"{BASE_URL}/api", json={}, status=200)

        api_client.call_module("createBucket", ["ref", {}], "Assets")

        body = json.loads(mocked_responses.calls[0].request.body)
        assert body["__class"] == "PublicAssets"
        assert body["call"]["function"] == "createBucket"

    @pytest.mark.parametrize(
        "method,args,expected_func,expected_params",
        [
            ("call_forms_query", ([{"limit": 1}],), "getFormsQuery", [{"limit": 1}]),
            ("call_forms_root_query", ([{"limit": 1}],), "getFormsRootQuery", [{"limit": 1}]),
            ("call_get_root", (["root-1"],), "getRoot", ["root-1"]),
            ("call_form_query", ("form-1", {"extMode": True}), "getFormQuery",
             ["form-1", {"extMode": True}]),
            ("call_forms_query_array", ("form-1", "items", {"limit": 5}), "getFormsQueryArray",
             ["form-1", "items", {"limit": 5}]),
            ("call_mutation", ({"op": "update"},), "formMutation", [{"op": "update"}]),
        ],
    )
    def test_typed_calls(self, api_client, mocked_responses, method, args,
                         expected_func, expected_params):
        mocked_responses.post(f"{BASE_URL}/api", json={}, status=200)

        getattr(api_client, method)(*args)

        body = json.loads(mocked_responses.calls[0].request.body)
        assert body["__class"] == "PublicForms"
        assert body["call"]["function"] == expected_func
        assert body["call"]["params"] == expected_params

    def test_module_name_override(self, api_client, mocked_responses):
        mocked_responses.post(f"{BASE_URL}/api", json={}, status=200)

        api_client.call_forms_query([{"limit": 1}], module_name="Project")

        assert json.loads(mocked_responses.calls[0].request.body)["__class"] == "PublicProject"


class TestErrorHandling:
    def test_non_200_raises_api_error(self, api_client, mocked_responses):
        mocked_responses.post(f"{BASE_URL}/api", json={"error": "boom"}, status=500)

        with pytest.raises(APIError) as excinfo:
            api_client.call("PublicForms", "getFormsQuery", [])

        assert excinfo.value.args[0] == {"error": "boom"}

    def test_download_error_raises_api_error(self, api_client, mocked_responses):
        mocked_responses.get(f"{BASE_URL}/assets/download/nope", json={"error": "404"}, status=404)

        with pytest.raises(APIError):
            api_client.call_download("nope")


class TestSelfAndAssets:
    def test_self_calls_self_endpoint(self, api_client, mocked_responses):
        mocked_responses.get(f"{BASE_URL}/self", json={"user": "bob"}, status=200)

        assert api_client.self() == {"user": "bob"}
        assert mocked_responses.calls[0].request.headers["authorization"] == f"Bearer {TOKEN}"

    def test_download_returns_raw_content(self, api_client, mocked_responses):
        mocked_responses.get(f"{BASE_URL}/assets/download/asset-1", body=b"binary",
                             status=200, content_type="application/octet-stream")

        assert api_client.call_download("asset-1") == b"binary"

    def test_upload_posts_multipart_to_bucket(self, api_client, mocked_responses, tmp_path):
        source = tmp_path / "doc.txt"
        source.write_text("content")
        mocked_responses.post(f"{BASE_URL}/assets/upload/bucket-1",
                              json={"id": "asset-1"}, status=200)

        assert api_client.call_upload("bucket-1", str(source)) == {"id": "asset-1"}

        request = mocked_responses.calls[0].request
        assert request.headers["Content-Type"].startswith("multipart/form-data")
        assert b"doc.txt" in request.body
        assert b"content" in request.body


class TestUrlBuilding:
    @pytest.mark.parametrize(
        "endpoint,expected",
        [("api", f"{BASE_URL}/api"), ("assets/download/1", f"{BASE_URL}/assets/download/1")],
    )
    def test_get_api(self, api_client, endpoint, expected):
        assert api_client._get_api(endpoint) == expected


@responses.activate
def test_client_is_usable_without_the_fixture():
    """Guard: the package must import and work with plain `responses.activate`."""
    responses.post(f"{BASE_URL}/api", json={"elts": [], "total": 0}, status=200)
    client = APIClient(base_url=BASE_URL, token=TOKEN)
    assert client.call_forms_query([{}]) == {"elts": [], "total": 0}
