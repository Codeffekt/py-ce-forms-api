from py_ce_forms_api import Form, FormMutate

from .conftest import make_block, make_form_dict


def mutate(client):
    return FormMutate(client)


class TestUpdate:
    def test_update_sends_the_whole_form(self, fake_client, form_dict):
        client = fake_client(call_mutation=make_form_dict(id="form-1"))

        result = mutate(client).update(Form(form_dict))

        assert isinstance(result, Form)
        assert client.last_call["mutation"] == {
            "type": "form", "op": "update", "elts": [form_dict],
        }
        assert client.last_call["module_name"] == "Forms"

    def test_update_single_accepts_a_raw_dict(self, fake_client, form_dict):
        client = fake_client(call_mutation=make_form_dict())

        mutate(client).update_single(form_dict)

        assert client.last_call["mutation"]["elts"] == [form_dict]

    def test_update_honours_the_module_name(self, fake_client, form_dict):
        client = fake_client(call_mutation=make_form_dict())
        mutation = mutate(client)
        mutation.module_name = "Project"

        mutation.update_single(form_dict)

        assert client.last_call["module_name"] == "Project"


class TestDelete:
    def test_delete_sends_only_the_id(self, fake_client, form_dict):
        client = fake_client(call_mutation=make_form_dict())

        mutate(client).delete(Form(form_dict))

        assert client.last_call["mutation"] == {
            "type": "form", "op": "delete", "indices": ["form-1"],
        }


class TestCreate:
    def test_create_from_root(self, fake_client):
        client = fake_client(call_module=make_form_dict(id="new-1", root="my-root"))

        form = mutate(client).create("my-root")

        assert form.id() == "new-1"
        assert client.last_call["func"] == "create"
        assert client.last_call["params"] == ["my-root"]

    def test_create_from_array_block(self, fake_client, form_dict):
        client = fake_client(call_mutation=make_form_dict(id="child-1"))
        block = Form(form_dict).get_block("photos")

        form = mutate(client).create_from_array(block)

        assert form.id() == "child-1"
        assert client.last_call["mutation"] == {
            "type": "formArray", "op": "create",
            "indices": ["form-1"], "formArrayField": "photos",
        }

    def test_copy(self, fake_client, form_dict):
        client = fake_client(call_module=make_form_dict(id="copy-1"))

        form = mutate(client).copy(Form(form_dict))

        assert form.id() == "copy-1"
        assert client.last_call["func"] == "copy"
        assert client.last_call["params"] == ["form-1"]


def test_mutation_result_is_wrapped_in_a_form(fake_client):
    """The backend echoes the mutated form back; it must come out as a `Form`."""
    payload = make_form_dict(id="form-1", blocks=[make_block("name", "text", "updated")])
    client = fake_client(call_mutation=payload)

    result = mutate(client).update_single(payload)

    assert result.get_value("name") == "updated"
