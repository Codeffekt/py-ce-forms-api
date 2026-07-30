from datetime import datetime

import pytest

from py_ce_forms_api import Form, FormBlock, FormBlockAssetArray, FormBlockAssoc

from .conftest import CTIME, MTIME, make_block, make_form_dict


class TestConstruction:
    @pytest.mark.parametrize("payload", [None, {}], ids=["none", "empty"])
    def test_rejects_empty_payload(self, payload):
        with pytest.raises(TypeError):
            Form(payload)

    def test_exposes_raw_payload(self, form_dict):
        form = Form(form_dict)
        assert form.get_form() is form_dict
        assert form.id() == "form-1"
        assert form.get_root() == "test-root"
        assert form.get_type() == "form"


class TestValues:
    def test_get_value_reads_the_block(self, form_dict):
        assert Form(form_dict).get_value("name") == "hello"

    def test_set_value_mutates_the_underlying_payload(self, form_dict):
        form = Form(form_dict)

        assert form.set_value("name", "world") is form  # chainable

        assert form.get_value("name") == "world"
        assert form_dict["content"]["name"]["value"] == "world"

    def test_unknown_field_raises(self, form_dict):
        with pytest.raises(KeyError):
            Form(form_dict).get_value("missing")


class TestBlocks:
    def test_get_block_wraps_and_back_references_the_form(self, form_dict):
        form = Form(form_dict)
        block = form.get_block("name")

        assert isinstance(block, FormBlock)
        assert block.get_field() == "name"
        assert block.get_form() is form

    def test_get_blocks_returns_every_block(self, form_dict):
        fields = [b.get_field() for b in Form(form_dict).get_blocks()]
        assert fields == list(form_dict["content"].keys())

    def test_get_assoc(self, form_dict):
        assoc = Form(form_dict).get_assoc("parent")
        assert isinstance(assoc, FormBlockAssoc)
        assert assoc.get_root() == "other-root"
        assert assoc.get_ref() == "parent-ref"

    def test_assoc_ref_falls_back_to_field_and_form_id(self, form_factory):
        form = Form(form_factory(blocks=[make_block("parent", "form", None, root="r")]))
        assert form.get_assoc("parent").get_ref() == "parent-form-1"

    def test_get_asset_array(self, form_dict):
        array = Form(form_dict).get_asset_array("photos")
        assert isinstance(array, FormBlockAssetArray)
        assert array.get_form_id() == "form-1"
        assert array.get_field() == "photos"

    def test_get_asset_array_rejects_other_block_types(self, form_dict):
        with pytest.raises(TypeError):
            Form(form_dict).get_asset_array("name")

    def test_apply_on_blocks_visits_all_blocks(self, form_dict):
        seen = []
        Form(form_dict).apply_on_blocks(lambda block: seen.append(block.get_field()))
        assert seen == list(form_dict["content"].keys())

    def test_set_readonly_marks_every_block(self, form_dict):
        Form(form_dict).set_readonly(True)
        assert all(b["readonly"] is True for b in form_dict["content"].values())


class TestSubForms:
    def test_get_sub_form(self, form_factory):
        child = make_form_dict(id="child-1")
        form = Form(form_factory(fields={"endpoint": child}))

        assert form.get_sub_form("endpoint").id() == "child-1"

    def test_get_node_form(self, form_factory):
        child = make_form_dict(id="node-1")
        form = Form(form_factory(nodes={"items": child}))

        assert form.get_node_form("items").id() == "node-1"

    def test_get_nodes_forms_without_nodes_returns_empty(self, form_dict):
        assert Form(form_dict).get_nodes_forms() == []

    def test_get_nodes_forms(self, form_factory):
        form = Form(form_factory(nodes={
            "a": make_form_dict(id="node-a"),
            "b": make_form_dict(id="node-b"),
        }))

        assert [f.id() for f in form.get_nodes_forms()] == ["node-a", "node-b"]

    @pytest.mark.parametrize("getter", ["get_sub_form", "get_node_form"])
    def test_missing_sub_form_raises(self, form_dict, getter):
        with pytest.raises(Exception, match="has no subform"):
            getattr(Form(form_dict), getter)("nope")


class TestTimestamps:
    def test_ctime_and_mtime_convert_from_milliseconds(self, form_dict):
        form = Form(form_dict)
        assert form.ctime() == datetime.fromtimestamp(CTIME / 1000)
        assert form.mtime() == datetime.fromtimestamp(MTIME / 1000)

    def test_mtime_is_none_when_absent(self, form_dict):
        del form_dict["mtime"]
        assert Form(form_dict).mtime() is None

    def test_str_mentions_id_and_root(self, form_dict):
        rendered = str(Form(form_dict))
        assert "form-1" in rendered
        assert "test-root" in rendered
        assert "modified at" in rendered

    def test_str_without_mtime(self, form_dict):
        del form_dict["mtime"]
        assert "modified at" not in str(Form(form_dict))
