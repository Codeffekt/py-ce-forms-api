import pytest

from py_ce_forms_api import AssetElt, AssetLocalFileElt, Assets, Form, FormsResIterable

from .conftest import make_block, make_form_dict

ASSET_VALUE = {
    "id": "asset-1",
    "mimetype": "text/plain",
    "name": "stored.txt",
    "originalname": "original.txt",
    "ref": "bucket-1",
}


class TestAssetElt:
    def test_accessors(self):
        elt = AssetElt(b"data", ASSET_VALUE)
        assert elt.id() == "asset-1"
        assert elt.mimetype() == "text/plain"
        assert elt.name() == "stored.txt"
        assert elt.original_name() == "original.txt"
        assert elt.ref() == "bucket-1"
        assert elt.get_bytes() == b"data"
        assert elt.get_value() == ASSET_VALUE

    @pytest.mark.parametrize("data,expected", [(b"x", True), (b"", True), (None, False)])
    def test_has_data(self, data, expected):
        assert AssetElt(data, ASSET_VALUE).has_data() is expected


class TestBuckets:
    def test_create_bucket(self, fake_client):
        client = fake_client(call_module={"id": "bucket-1"})

        assert Assets(client).create_bucket("my-ref") == {"id": "bucket-1"}
        assert client.last_call["module_name"] == "Assets"
        assert client.last_call["func"] == "createBucket"
        assert client.last_call["params"] == ["my-ref", {}]

    def test_create_bucket_for_an_asset_array(self, fake_client, form_dict):
        client = fake_client(call_module={"id": "bucket-1"})
        block = Form(form_dict).get_asset_array("photos")

        Assets(client).create_bucket_assets_array(block)

        assert client.last_call["func"] == "createBucketAssetsArray"
        assert client.last_call["params"] == ["form-1", "photos", {}]


class TestUpload:
    @pytest.fixture
    def source(self, tmp_path):
        path = tmp_path / "picture.png"
        path.write_bytes(b"\x89PNG")
        return str(path)

    def test_mimetype_is_guessed_from_the_extension(self, fake_client, source):
        client = fake_client(call_upload={"id": "asset-1"})

        Assets(client).upload_file_to_bucket({"id": "bucket-1"}, source)

        assert client.last_call["mimetype"] == "image/png"

    def test_unknown_extension_falls_back_to_text_plain(self, fake_client, tmp_path):
        path = tmp_path / "data.unknown-ext"
        path.write_text("x")
        client = fake_client(call_upload={"id": "asset-1"})

        Assets(client).upload_file_to_bucket({"id": "bucket-1"}, str(path))

        assert client.last_call["mimetype"] == "text/plain"

    def test_explicit_mimetype_is_kept(self, fake_client, source):
        client = fake_client(call_upload={"id": "asset-1"})

        Assets(client).upload_file_to_bucket({"id": "bucket-1"}, source, mimetype="image/jpeg")

        assert client.last_call["mimetype"] == "image/jpeg"

    def test_upload_file_creates_the_bucket_first(self, fake_client, source):
        client = fake_client(call_module={"id": "bucket-9"}, call_upload={"id": "asset-1"})

        Assets(client).upload_file("my-ref", source)

        assert [c["call"] for c in client.calls] == ["call_module", "call_upload"]
        assert client.last_call["bucket_id"] == "bucket-9"

    def test_upload_to_asset_array_returns_an_asset_elt(self, fake_client, source, form_dict):
        client = fake_client(call_module={"id": "bucket-9"}, call_upload=ASSET_VALUE)
        block = Form(form_dict).get_asset_array("photos")

        elt = Assets(client).upload_file_to_asset_array(block, source)

        assert isinstance(elt, AssetElt)
        assert elt.id() == "asset-1"
        assert elt.has_data() is False


class TestDelete:
    def test_delete_asset(self, fake_client):
        client = fake_client(call_module={"ok": True})

        Assets(client).delete_asset("bucket-1", "asset-1")

        assert client.last_call["func"] == "deleteAssets"
        assert client.last_call["params"] == ["bucket-1", ["asset-1"]]

    @pytest.mark.parametrize("delete_file", [True, False])
    def test_delete_from_asset_array(self, fake_client, form_dict, delete_file):
        client = fake_client(call_module={"ok": True})
        block = Form(form_dict).get_asset_array("photos")

        Assets(client).delete_asset_array(block, "asset-1", delete_file=delete_file)

        assert client.last_call["func"] == "deleteAssetsArray"
        assert client.last_call["params"] == ["form-1", "photos", ["asset-1"], delete_file]


class TestCreateAsset:
    def test_downloads_the_referenced_file(self, fake_client, form_dict):
        client = fake_client(call_download=b"file-bytes")
        block = Form(form_dict).get_block("doc")

        elt = Assets(client).create_asset(block)

        assert client.last_call == {"call": "call_download", "id": "asset-1"}
        assert elt.get_bytes() == b"file-bytes"
        assert elt.original_name() == "original.txt"

    def test_empty_asset_block_downloads_nothing(self, fake_client, form_factory):
        client = fake_client()
        block = Form(form_factory(blocks=[make_block("doc", "asset", None)])).get_block("doc")

        elt = Assets(client).create_asset(block)

        assert client.calls == []
        assert elt.has_data() is False

    def test_rejects_non_asset_blocks(self, fake_client, form_dict):
        block = Form(form_dict).get_block("name")

        with pytest.raises(Exception, match="is not of type asset"):
            Assets(fake_client()).create_asset(block)


class TestAssetArrayQueries:
    def test_get_assets_from_array_builds_an_iterable_query(self, fake_client, form_dict):
        client = fake_client(call_module={"elts": [], "total": 0, "limit": 10, "offset": 0})
        block = Form(form_dict).get_asset_array("photos")

        iterable = Assets(client).get_assets_from_array(block)
        assert isinstance(iterable, FormsResIterable)

        list(iterable)  # the query is lazy: nothing is sent before iteration
        call = client.last_call
        assert call["func"] == "getAssetsArrayQuery"
        assert call["module_name"] == "Assets"
        assert call["params"][:2] == ["form-1", "photos"]

    def test_filter_on_original_name(self, fake_client, form_dict):
        client = fake_client(call_module={"elts": [], "total": 0, "limit": 10, "offset": 0})
        block = Form(form_dict).get_asset_array("photos")

        list(Assets(client).get_assets_with_original_name(block, "original.txt"))

        assert client.last_call["params"][2]["queryFields"] == [
            {"field": "originalname", "value": "original.txt", "op": "="}
        ]


class TestLocalStorage:
    def test_requires_a_dir_path(self, fake_client):
        with pytest.raises(TypeError, match="dir_path"):
            Assets(fake_client()).get_local_storage()

    def test_creates_the_directory(self, fake_client, tmp_path):
        target = tmp_path / "assets"
        Assets(fake_client(dir_path=str(target))).get_local_storage()
        assert target.is_dir()

    def test_save_downloads_once(self, fake_client, tmp_path):
        client = fake_client(dir_path=str(tmp_path / "assets"), call_download=b"payload")
        storage = AssetLocalFileElt(client)

        assert storage.save("asset-1") is True
        assert storage.exists("asset-1") is True
        assert storage.save("asset-1") is False, "already cached, must not download again"
        assert [c["call"] for c in client.calls] == ["call_download"]

    def test_file_path_layout(self, fake_client, tmp_path):
        dir_path = str(tmp_path / "assets")
        storage = AssetLocalFileElt(fake_client(dir_path=dir_path))
        assert storage.get_file_path("asset-1") == f"{dir_path}/asset-1"

    def test_load_reads_from_the_cache(self, fake_client, tmp_path):
        client = fake_client(dir_path=str(tmp_path / "assets"), call_download=b"payload")
        storage = AssetLocalFileElt(client)
        storage.save("asset-1")
        client.calls.clear()

        elt = storage.load(ASSET_VALUE)

        assert elt.get_bytes() == b"payload"
        assert client.calls == [], "a cached asset must not be downloaded again"


def test_asset_array_block_accessors(form_dict):
    array = Form(form_dict).get_asset_array("photos")
    assert array.get_form_id() == "form-1"
    assert array.get_field() == "photos"
    assert array.get_ref() == "photos-form-1", "the {$id} placeholder must be resolved"
    assert array.get_block().get_field() == "photos"


def test_assets_module_uses_the_assets_module_name(fake_client):
    from py_ce_forms_api.api.modules import ASSETS_MODULE_NAME

    client = fake_client(call_module={})
    Assets(client).create_bucket("r")
    assert client.last_call["module_name"] == ASSETS_MODULE_NAME
