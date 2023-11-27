import pytest

from llamazure.azrest.openapi import IR_T, IR_List, IRDef, IRTransformer, OADef, PathLookupError, Reader


class TestResolveReference:
	def test_get_from_object_at_path_valid_path(self):
		data = {"a": {"b": {"c": 42}}}
		result = Reader._get_from_object_at_path(data, "a/b/c")
		assert result == 42

	def test_get_from_object_at_path_invalid_path(self):
		data = {"a": {"b": {"c": 42}}}
		with pytest.raises(PathLookupError) as exc_info:
			Reader._get_from_object_at_path(data, "a/b/d")

		expected_error_message = "Error while looking up path: a/b/d"
		assert str(exc_info.value) == expected_error_message

	def test_get_from_object_at_path_invalid_object(self):
		data = {"a": {"b": {"c": 42}}}
		with pytest.raises(PathLookupError) as exc_info:
			Reader._get_from_object_at_path(data, "a/b/c/d")

		expected_error_message = "Error while looking up path: a/b/c/d"
		assert str(exc_info.value) == expected_error_message

	def test_get_from_object_at_path_empty_path(self):
		data = {"a": {"b": {"c": 42}}}
		result = Reader._get_from_object_at_path(data, "")
		assert result == data

	def test_get_from_object_at_path_path_with_slash_prefix(self):
		data = {"a": {"b": {"c": 42}}}
		result = Reader._get_from_object_at_path(data, "/a/b/c")
		assert result == 42


class TestTransformPrimitives:
	def test_string(self):
		p = OADef.Property(type="string", description="description0")
		assert IRTransformer({}, None).resolve_type(p.t) == str


class TestTransformArray:
	def test_string_array(self):
		p = OADef.Array(
			items=OADef.Property(type="string", description="d0"),
			description="d1",
		)
		assert IRTransformer({}, None).ir_array(p) == IR_T(t=IR_List(items=IR_T(t=str)))


class TestTransformDef:
	def test_bag_of_props(self):
		p = OADef(
			type="t0",
			description="d0",
			properties={
				"p0": OADef.Property(type="t.p0"),
				"p1": OADef.Property(type="t.p1"),
			},
			required={"p0", "p1"},
		)
		result = IRTransformer({}, None).transform_def("n0", p)
		expected = IRDef(
			name="n0",
			description="d0",
			properties={
				"p0": IR_T(t="t.p0"),
				"p1": IR_T(t="t.p1"),
			},
		)
		assert result == expected
