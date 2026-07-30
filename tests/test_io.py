import json

import pytest

from py_ce_forms_api import Form, FormsRes, JsonDump, MdDump

from .conftest import make_block, make_form_dict


@pytest.fixture
def form():
    return Form(make_form_dict(id="form-1", root="my-root", blocks=[
        make_block("name", "text", "hello"),
        make_block("count", "number", "42"),
    ]))


@pytest.fixture
def forms(form):
    return [form, Form(make_form_dict(id="form-2", root="my-root"))]


class FakeIter:
    """Minimal `FormsResIterable` look-alike yielding pages of `FormsRes`."""

    def __init__(self, pages):
        self.pages = pages

    def __iter__(self):
        for page in self.pages:
            yield FormsRes(page)


class TestJsonDump:
    def test_form_to_str_round_trips(self, form):
        assert json.loads(JsonDump.form_to_str(form)) == form.get_form()

    def test_form_to_str_is_indented(self, form):
        assert "\n    " in JsonDump.form_to_str(form)

    def test_form_to_file(self, form, tmp_path):
        target = tmp_path / "form.json"
        with open(target, "w") as fh:
            JsonDump.form_to_file(form, fh)

        assert json.loads(target.read_text()) == form.get_form()

    def test_list_to_str(self, forms):
        assert [f["id"] for f in json.loads(JsonDump.list_to_str(forms))] == ["form-1", "form-2"]

    def test_list_to_file(self, forms, tmp_path):
        target = tmp_path / "forms.json"
        with open(target, "w") as fh:
            JsonDump.list_to_file(forms, fh)

        assert len(json.loads(target.read_text())) == 2

    def test_iter_to_str_flattens_pages(self):
        pages = [
            {"elts": [make_form_dict(id="a")], "total": 2, "limit": 1, "offset": 0},
            {"elts": [make_form_dict(id="b")], "total": 2, "limit": 1, "offset": 1},
        ]

        dumped = json.loads(JsonDump.iter_to_str(FakeIter(pages)))

        assert [f["id"] for f in dumped] == ["a", "b"]

    def test_iter_to_file(self, tmp_path):
        pages = [{"elts": [make_form_dict(id="a")], "total": 1, "limit": 1, "offset": 0}]
        target = tmp_path / "iter.json"
        with open(target, "w") as fh:
            JsonDump.iter_to_file(FakeIter(pages), fh)

        assert [f["id"] for f in json.loads(target.read_text())] == ["a"]

    def test_res_to_str(self, forms_res_payload):
        dumped = json.loads(JsonDump.res_to_str(FormsRes(forms_res_payload)))

        assert [f["id"] for f in dumped] == ["form-1", "form-2"]

    def test_res_to_file(self, forms_res_payload, tmp_path):
        target = tmp_path / "res.json"
        with open(target, "w") as fh:
            JsonDump.res_to_file(FormsRes(forms_res_payload), fh)

        assert [f["id"] for f in json.loads(target.read_text())] == ["form-1", "form-2"]


class TestMdDump:
    def test_form_to_str_lists_root_id_and_fields(self, form):
        dumped = MdDump.form_to_str(form)

        assert dumped.splitlines() == [
            "Form my-root (form-1)",
            "Fields name (text),count (number)",
            "Nodes ",
        ]

    def test_nodes_are_listed(self):
        form = Form(make_form_dict(id="form-1", root="my-root",
                                   nodes={"child": make_form_dict(id="node-1",
                                                                  root="child-root")}))

        assert "Nodes Form child-root (node-1)" in MdDump.form_to_str(form)

    def test_list_to_str_joins_forms(self, forms):
        dumped = MdDump.list_to_str(forms)
        assert "form-1" in dumped
        assert "form-2" in dumped

    def test_iter_to_str_flattens_pages(self):
        pages = [
            {"elts": [make_form_dict(id="a")], "total": 2, "limit": 1, "offset": 0},
            {"elts": [make_form_dict(id="b")], "total": 2, "limit": 1, "offset": 1},
        ]

        dumped = MdDump.iter_to_str(FakeIter(pages))

        assert "(a)" in dumped
        assert "(b)" in dumped

    def test_res_to_str(self, forms_res_payload):
        dumped = MdDump.res_to_str(FormsRes(forms_res_payload))

        assert len(dumped) == 2
        assert dumped[0].startswith("Form test-root (form-1)")
