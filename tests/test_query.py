import pytest

from py_ce_forms_api import (
    Form,
    FormQueryNode,
    FormsQuery,
    FormsQueryArray,
    FormsRes,
    FormsResIterable,
)

from .conftest import make_form_dict


def raw_query(query: FormsQuery):
    """The query body the client would send."""
    return query._create_raw_query()


class TestRawQuery:
    def test_defaults(self, fake_client):
        assert raw_query(FormsQuery(fake_client())) == {
            "extMode": False,
            "limit": 10,
            "offset": 0,
            "queryFields": [],
            "nodes": [],
            "ref": None,
        }

    def test_builders_are_chainable(self, fake_client):
        query = FormsQuery(fake_client())
        assert (
            query.with_root("r").with_limit(1).with_offset(2).with_sub_forms()
            .with_ref("ref").where("a", "b").with_module_name("Assets")
            .with_func("f").with_args([1]).with_extra({})
        ) is query

    def test_with_root_and_with_id_target_metadata(self, fake_client):
        query = FormsQuery(fake_client()).with_root("my-root").with_id("form-1")

        assert raw_query(query)["queryFields"] == [
            {"field": "root", "value": "my-root", "onMeta": True},
            {"field": "id", "value": "form-1", "onMeta": True},
        ]

    def test_where_defaults_to_equality(self, fake_client):
        query = FormsQuery(fake_client()).where("name", "widget")
        assert raw_query(query)["queryFields"] == [{"field": "name", "value": "widget", "op": "="}]

    def test_where_with_operator(self, fake_client):
        query = FormsQuery(fake_client()).where("count", "3", op=">")
        assert raw_query(query)["queryFields"][0]["op"] == ">"

    def test_pagination_and_sub_forms(self, fake_client):
        query = FormsQuery(fake_client()).with_limit(50).with_offset(100).with_sub_forms()
        body = raw_query(query)
        assert (body["limit"], body["offset"], body["extMode"]) == (50, 100, True)

    def test_sub_forms_can_be_disabled(self, fake_client):
        assert raw_query(FormsQuery(fake_client()).with_sub_forms(False))["extMode"] is False

    def test_extra_is_merged_into_the_body(self, fake_client):
        body = raw_query(FormsQuery(fake_client()).with_extra({"sort": "ctime", "limit": 99}))
        assert body["sort"] == "ctime"
        assert body["limit"] == 99, "extra must override the base body"

    def test_str_is_debuggable(self, fake_client):
        rendered = str(FormsQuery(fake_client()).with_root("r").with_module_name("Assets"))
        assert "Assets" in rendered
        assert "my-root" not in rendered
        assert "'value': 'r'" in rendered


class TestQueryNodes:
    def test_node_as_dict(self):
        node = FormQueryNode(field="items", root="child-root", name="Items")
        assert node.asDict() == {
            "field": "items", "root": "child-root", "name": "Items", "type": "formArray",
        }

    def test_node_type_override(self):
        assert FormQueryNode("f", "r", "n", type="assoc").asDict()["type"] == "assoc"

    def test_with_node(self, fake_client):
        query = FormsQuery(fake_client()).with_node(FormQueryNode("items", "r", "Items"))
        assert raw_query(query)["nodes"] == [{"field": "items", "root": "r",
                                              "name": "Items", "type": "formArray"}]

    def test_with_nodes(self, fake_client):
        nodes = [FormQueryNode("a", "r", "A"), FormQueryNode("b", "r", "B")]
        query = FormsQuery(fake_client()).with_nodes(nodes)
        assert [n["field"] for n in raw_query(query)["nodes"]] == ["a", "b"]


class TestQueryCall:
    def test_call_uses_get_forms_query(self, fake_client, forms_res_payload):
        client = fake_client(call_forms_query=forms_res_payload)

        res = FormsQuery(client).with_root("test-root").call()

        assert isinstance(res, FormsRes)
        assert client.last_call["call"] == "call_forms_query"
        assert client.last_call["module_name"] == "Forms"
        assert client.last_call["params"] == [raw_query(FormsQuery(client).with_root("test-root"))]

    def test_call_with_func_uses_call_module(self, fake_client, forms_res_payload):
        client = fake_client(call_module=forms_res_payload)

        FormsQuery(client).with_func("getAssetsArrayQuery").with_module_name("Assets") \
            .with_args(["form-1", "photos"]).call()

        call = client.last_call
        assert call["call"] == "call_module"
        assert call["func"] == "getAssetsArrayQuery"
        assert call["module_name"] == "Assets"
        assert call["params"][:2] == ["form-1", "photos"]
        assert call["params"][2]["limit"] == 10

    def test_call_single(self, fake_client):
        client = fake_client(call_form_query=make_form_dict())

        result = FormsQuery(client).with_sub_forms().call_single("form-1")

        assert result["id"] == "form-1"
        assert client.last_call["id"] == "form-1"
        assert client.last_call["query"]["extMode"] is True


class TestQueryArray:
    def test_call_targets_the_array_block(self, fake_client, forms_res_payload):
        client = fake_client(call_forms_query_array=forms_res_payload)

        res = FormsQueryArray(client).with_array("form-1", "items").with_limit(5).call()

        assert isinstance(res, FormsRes)
        call = client.last_call
        assert (call["id"], call["field"]) == ("form-1", "items")
        assert call["query"][-1]["limit"] == 5

    def test_with_array_is_chainable(self, fake_client):
        query = FormsQueryArray(fake_client())
        assert query.with_array("form-1", "items") is query


class TestFormsRes:
    def test_rejects_none(self):
        with pytest.raises(TypeError):
            FormsRes(None)

    def test_accessors(self, forms_res_payload):
        res = FormsRes(forms_res_payload)
        assert res.total() == 2
        assert res.limit() == 10
        assert res.offset() == 0
        assert len(res) == 2
        assert res.elts() == forms_res_payload["elts"]

    def test_total_is_coerced_to_int(self, forms_res_payload):
        forms_res_payload["total"] = "17"
        assert FormsRes(forms_res_payload).total() == 17

    def test_forms_wraps_elements(self, forms_res_payload):
        forms = list(FormsRes(forms_res_payload).forms())
        assert [f.id() for f in forms] == ["form-1", "form-2"]
        assert all(isinstance(f, Form) for f in forms)

    def test_forms_can_be_consumed_several_times(self, forms_res_payload):
        """Each call returns a fresh iterator over the result page."""
        res = FormsRes(forms_res_payload)
        assert [f.id() for f in res.forms()] == ["form-1", "form-2"]
        assert [f.id() for f in res.forms()] == ["form-1", "form-2"]

    def test_res_is_directly_iterable(self, forms_res_payload):
        res = FormsRes(forms_res_payload)

        assert [f.id() for f in res] == ["form-1", "form-2"]
        assert all(isinstance(f, Form) for f in res)

    def test_iterating_twice_restarts_from_the_first_element(self, forms_res_payload):
        res = FormsRes(forms_res_payload)
        assert len(list(res)) == 2
        assert len(list(res)) == 2

    def test_iteration_reflects_the_underlying_payload(self, forms_res_payload):
        res = FormsRes(forms_res_payload)
        forms_res_payload["elts"].append(make_form_dict(id="form-3"))

        assert [f.id() for f in res] == ["form-1", "form-2", "form-3"]


class FakeQuery:
    """A `FormsQuery` look-alike returning canned pages."""

    def __init__(self, pages):
        self.pages = pages
        self.offsets = []
        self.index = 0

    def with_offset(self, offset):
        self.offsets.append(offset)
        return self

    def call(self):
        page = self.pages[self.index]
        self.index += 1
        return FormsRes(page)


def page(ids, total, limit, offset):
    return {
        "elts": [make_form_dict(id=i) for i in ids],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


class TestFormsResIterable:
    def test_single_page(self):
        query = FakeQuery([page(["a", "b"], total=2, limit=10, offset=0)])

        pages = list(FormsResIterable(query))

        assert len(pages) == 1
        assert query.offsets == []

    def test_paginates_until_total_is_reached(self):
        query = FakeQuery([
            page(["a", "b"], total=5, limit=2, offset=0),
            page(["c", "d"], total=5, limit=2, offset=2),
            page(["e"], total=5, limit=2, offset=4),
        ])

        ids = [form.id() for res in FormsResIterable(query) for form in res.forms()]

        assert ids == ["a", "b", "c", "d", "e"]
        assert query.offsets == [2, 4]

    def test_stops_on_a_short_page(self):
        query = FakeQuery([
            page(["a", "b"], total=100, limit=2, offset=0),
            page(["c"], total=100, limit=2, offset=2),
        ])

        assert len(list(FormsResIterable(query))) == 2

    def test_zero_limit_stops_immediately(self):
        query = FakeQuery([page([], total=0, limit=0, offset=0)])

        assert len(list(FormsResIterable(query))) == 1
        assert query.offsets == []

    def test_empty_result(self):
        query = FakeQuery([page([], total=0, limit=10, offset=0)])

        assert [form for res in FormsResIterable(query) for form in res.forms()] == []
