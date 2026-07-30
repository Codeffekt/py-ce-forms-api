from datetime import datetime

import pytest

from py_ce_forms_api import Form, FormBlock, FormUtils

from .conftest import CTIME, make_block, make_form_dict


def block_of(type_, value, **extra):
    """A `FormBlock` bound to a one-field form."""
    form = Form(make_form_dict(blocks=[make_block("f", type_, value, **extra)]))
    return form.get_block("f")


class TestAttributes:
    def test_reads_block_metadata(self):
        block = block_of("form", None, root="other-root", readonly=False)
        assert block.get_type() == "form"
        assert block.get_field() == "f"
        assert block.get_root() == "other-root"
        assert block.get_block_attr("readonly") is False

    def test_missing_attribute_raises(self):
        with pytest.raises(KeyError):
            block_of("text", "x").get_block_attr("nope")

    def test_set_readonly(self):
        block = block_of("text", "x")
        block.set_readonly(True)
        assert block.get_block_attr("readonly") is True

    @pytest.mark.parametrize("type_,expected", [("asset", True), ("assetArray", False),
                                                ("text", False)])
    def test_is_type_asset(self, type_, expected):
        assert block_of(type_, None).is_type_asset() is expected


class TestGetValue:
    def test_missing_value_key(self):
        form = Form(make_form_dict(blocks=[{"field": "f", "type": "text"}]))
        assert form.get_block("f").get_value() is None

    @pytest.mark.parametrize("type_", ["text", "number", "boolean", "timestamp", "coordinates"])
    def test_none_value_short_circuits_every_type(self, type_):
        assert block_of(type_, None).get_value() is None

    def test_text_is_returned_verbatim(self):
        assert block_of("text", "hello").get_value() == "hello"

    def test_unknown_type_is_returned_verbatim(self):
        assert block_of("whatever", {"a": 1}).get_value() == {"a": 1}

    @pytest.mark.parametrize("raw,expected", [("42", 42.0), (42, 42.0), ("3.5", 3.5), (-1, -1.0)])
    def test_number_is_coerced_to_float(self, raw, expected):
        assert block_of("number", raw).get_value() == expected

    def test_unparsable_number_is_none(self):
        assert block_of("number", "not-a-number").get_value() is None

    @pytest.mark.parametrize("raw,expected", [
        ("true", True), ("false", False), (True, True), (False, False), ("anything", True),
    ])
    def test_boolean(self, raw, expected):
        assert block_of("boolean", raw).get_value() is expected

    def test_timestamp_is_converted_from_milliseconds(self):
        assert block_of("timestamp", CTIME).get_value() == datetime.fromtimestamp(CTIME / 1000)

    @pytest.mark.parametrize("raw", ["not-a-date", "nan"], ids=["garbage", "nan"])
    def test_invalid_timestamp_is_none(self, raw):
        assert block_of("timestamp", raw).get_value() is None

    def test_out_of_range_timestamp_is_none(self):
        assert block_of("timestamp", 1e17).get_value() is None

    def test_coordinates_are_floats(self):
        assert list(block_of("coordinates", ["1.5", "2.5"]).get_value()) == [1.5, 2.5]

    def test_coordinates_from_non_list_is_none(self):
        assert block_of("coordinates", "1.5,2.5").get_value() is None

    def test_asset_array_value_is_templated(self):
        assert block_of("assetArray", "bucket-{$id}").get_value() == "bucket-form-1"


class TestSetValue:
    def test_set_none(self):
        block = block_of("text", "hello")
        block.set_value(None)
        assert block.get_value() is None

    def test_set_plain_value(self):
        block = block_of("text", "hello")
        block.set_value("world")
        assert block.get_value() == "world"

    def test_datetime_on_a_timestamp_block_is_stored_in_milliseconds(self):
        block = block_of("timestamp", None)
        moment = datetime(2024, 1, 2, 3, 4, 5)

        block.set_value(moment)

        assert block.get_block_attr("value") == int(moment.timestamp() * 1000)

    def test_timestamp_round_trip(self):
        block = block_of("timestamp", None)
        moment = datetime(2024, 1, 2, 3, 4, 5)

        block.set_value(moment)

        assert block.get_value() == moment

    def test_a_numeric_timestamp_is_stored_untouched(self):
        """Only `datetime` values are converted; raw millisecond values pass through."""
        block = block_of("timestamp", None)

        block.set_value(CTIME)

        assert block.get_block_attr("value") == CTIME
        assert block.get_value() == datetime.fromtimestamp(CTIME / 1000)

    def test_datetime_on_a_non_timestamp_block_is_stored_as_is(self):
        block = block_of("text", None)
        moment = datetime(2024, 1, 2)
        block.set_value(moment)
        assert block.get_block_attr("value") is moment


class TestFormUtils:
    @pytest.fixture
    def form(self):
        return Form(make_form_dict(id="form-9", root="my-root", blocks=[
            make_block("name", "text", "widget"),
            make_block("empty", "text", None),
        ]))

    @pytest.mark.parametrize("template,expected", [
        ("plain", "plain"),
        ("{name}", "widget"),
        ("prefix-{name}-suffix", "prefix-widget-suffix"),
        ("{name}/{name}", "widget/widget"),
        ("{$id}", "form-9"),
        ("{$root}/{name}", "my-root/widget"),
        ("{empty}!", "!"),
    ])
    def test_eval(self, form, template, expected):
        assert FormUtils.eval(form, template) == expected

    def test_unknown_field_raises(self, form):
        with pytest.raises(KeyError):
            FormUtils.eval(form, "{nope}")


def test_block_type_constants_are_stable():
    """These strings come from the backend schema; changing one is a breaking change."""
    assert (FormBlock.TEXT_TYPE, FormBlock.NUMBER_TYPE, FormBlock.BOOLEAN_TYPE,
            FormBlock.TIMESTAMP_TYPE, FormBlock.COORDINATES_TYPE, FormBlock.FORM_ARRAY_TYPE,
            FormBlock.ASSET_ARRAY_TYPE, FormBlock.ASSET_TYPE) == (
        "text", "number", "boolean", "timestamp", "coordinates", "formArray",
        "assetArray", "asset")
