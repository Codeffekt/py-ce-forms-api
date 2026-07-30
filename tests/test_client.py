import pytest

from py_ce_forms_api import (
    Accounts,
    Assets,
    CeFormsClient,
    Form,
    FormMutate,
    Forms,
    FormsQuery,
    FormsQueryArray,
    FormsResIterable,
    OldProject,
    OldProjects,
    Root,
    Roots,
)

from py_ce_forms_api.api.modules import PROJECTS_MODULE_NAME

from .conftest import BASE_URL, TOKEN, make_block, make_form_dict


@pytest.fixture
def client():
    return CeFormsClient(base_url=BASE_URL, token=TOKEN)


class TestClientWiring:
    @pytest.mark.parametrize("factory,expected", [
        ("query", FormsQuery),
        ("query_array", FormsQueryArray),
        ("mutation", FormMutate),
        ("accounts", Accounts),
        ("assets", Assets),
        ("forms", Forms),
        ("roots", Roots),
        ("old_projects", OldProjects),
    ])
    def test_module_factories(self, client, factory, expected):
        module = getattr(client, factory)()
        assert isinstance(module, expected)
        assert module.client is client.api

    def test_each_call_returns_a_fresh_module(self, client):
        assert client.query() is not client.query()

    def test_with_dir_path_is_chainable(self, client, tmp_path):
        assert client.with_dir_path(str(tmp_path)) is client
        assert client.api.get_dir_path() == str(tmp_path)

    def test_self_delegates_to_the_api(self, client, mocked_responses):
        mocked_responses.get(f"{BASE_URL}/self", json={"user": "bob"}, status=200)
        assert client.self() == {"user": "bob"}

    def test_constructor_forwards_to_the_api_client(self, monkeypatch):
        monkeypatch.setenv("CE_FORMS_BASE_URL", "https://env.test")
        monkeypatch.setenv("CE_FORMS_TOKEN", "env-token")
        assert CeFormsClient().api.base_url == "https://env.test"


class TestForms:
    def test_get_form(self, fake_client):
        api = fake_client(call_form_query=make_form_dict(id="form-1"))

        form = Forms(api).get_form("form-1")

        assert isinstance(form, Form)
        assert form.id() == "form-1"
        assert api.last_call["id"] == "form-1"

    def test_get_form_missing_raises(self, fake_client):
        with pytest.raises(TypeError):
            Forms(fake_client(call_form_query=None)).get_form("nope")

    def test_get_form_assoc_queries_by_ref(self, fake_client, form_dict):
        api = fake_client(call_forms_query={"elts": [], "total": 0, "limit": 10, "offset": 0})
        assoc = Form(form_dict).get_assoc("parent")

        iterable = Forms(api).get_form_assoc(assoc)
        assert isinstance(iterable, FormsResIterable)

        list(iterable)
        assert api.last_call["params"][0]["ref"] == "parent-ref"


class TestRoots:
    def test_get_form_returns_a_root(self, fake_client):
        api = fake_client(call_get_root=make_form_dict(id="my-root"))

        root = Roots(api).get_form("my-root")

        assert isinstance(root, Root)
        assert root.id() == "my-root"

    def test_root_blocks(self):
        root = Root(make_form_dict(id="my-root", blocks=[
            make_block("a", "text", "1"), make_block("b", "number", "2"),
        ]))

        assert [b.get_field() for b in root.get_blocks()] == ["a", "b"]
        assert root.get_block("b").get_value() == 2.0

    @pytest.mark.parametrize("payload", [None, {}])
    def test_root_rejects_empty_payload(self, payload):
        with pytest.raises(TypeError):
            Root(payload)

    def test_root_str(self):
        root = Root(make_form_dict(id="my-root"))
        assert "my-root" in str(root)
        assert "created at" in str(root)

    def test_root_mtime_is_optional(self):
        payload = make_form_dict(id="my-root")
        del payload["mtime"]
        assert Root(payload).mtime() is None


class TestAccounts:
    def test_get_account_from_login_builds_a_scoped_query(self, fake_client):
        api = fake_client(call_forms_query={"elts": [], "total": 0, "limit": 10, "offset": 0})

        query = Accounts(api).get_account_from_login("bob")
        assert api.calls == [], "the query must stay lazy until .call()"

        query.call()
        body = api.last_call["params"][0]
        assert body["queryFields"] == [
            {"field": "root", "value": Accounts.root, "onMeta": True},
            {"field": "login", "value": "bob", "op": "="},
        ]
        assert body["limit"] == 1


OLD_PROJECT = {
    "id": "project-1",
    "name": "My project",
    "ctime": 1700000000000,
    "mtime": 1700003600000,
    "forms": [
        {"id": "block-1", "ref": "ref-1", "root": "root-1"},
        {"id": "block-2", "ref": "ref-2", "root": "root-2"},
    ],
}


class TestOldProject:
    def test_accessors(self):
        project = OldProject(OLD_PROJECT)
        assert project.id() == "project-1"
        assert project.get_form() is OLD_PROJECT
        assert "My project" in str(project)

    def test_get_block(self):
        block = OldProject(OLD_PROJECT).get_block("block-2")
        assert (block.id(), block.ref(), block.root()) == ("block-2", "ref-2", "root-2")

    def test_unknown_block_raises(self):
        with pytest.raises(StopIteration):
            OldProject(OLD_PROJECT).get_block("nope")

    @pytest.mark.parametrize("payload", [None, {}])
    def test_rejects_empty_payload(self, payload):
        with pytest.raises(TypeError):
            OldProject(payload)

class TestOldProjects:
    def test_get_project(self, fake_client):
        api = fake_client(call_module=OLD_PROJECT)

        project = OldProjects(api).get_project("project-1")

        assert isinstance(project, OldProject)
        assert api.last_call["func"] == "getProject"
        assert api.last_call["params"] == ["project-1"]
        assert api.last_call["module_name"] == PROJECTS_MODULE_NAME

    def test_get_all(self, fake_client):
        api = fake_client(call_module=[OLD_PROJECT, {**OLD_PROJECT, "id": "project-2"}])

        projects = OldProjects(api).get_all()

        assert [p.id() for p in projects] == ["project-1", "project-2"]
        assert api.last_call["params"] == []

    def test_get_project_forms_is_a_lazy_iterable(self, fake_client):
        api = fake_client(call_forms_query={"elts": [], "total": 0, "limit": 10, "offset": 0})

        iterable = OldProjects(api).get_project_forms("project-1", "items")
        assert isinstance(iterable, FormsResIterable)
        assert api.calls == []

        list(iterable)
        assert api.last_call["module_name"] == PROJECTS_MODULE_NAME
        assert api.last_call["params"][:2] == ["project-1", "items"]
