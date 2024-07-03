"""Test the OpenAPI codegen"""
from pathlib import Path
from typing import Dict, Union

# pylint: disable=protected-access
import pytest
from pydantic import TypeAdapter

from llamazure.azrest.openapi import IR_T, IR_List, IRDef, IRTransformer, OADef, OAEnum, OARef, PathLookupError, Reader, RefCache


class TestResolveReference:
	"""Test resolving references"""

	def test_get_from_object_at_path_valid_path(self):
		data = {"a": {"b": {"c": 42}}}
		result = Reader._get_from_object_at_path(data, "a/b/c")
		assert result == 42

	def test_get_from_object_at_path_invalid_path(self):
		data = {"a": {"b": {"c": 42}}}
		with pytest.raises(PathLookupError) as exc_info:
			Reader._get_from_object_at_path(data, "a/b/d")

	def test_get_from_object_at_path_invalid_object(self):
		data = {"a": {"b": {"c": 42}}}
		with pytest.raises(PathLookupError) as exc_info:
			Reader._get_from_object_at_path(data, "a/b/c/d")

	def test_get_from_object_at_path_empty_path(self):
		data = {"a": {"b": {"c": 42}}}
		result = Reader._get_from_object_at_path(data, "")
		assert result == data

	def test_get_from_object_at_path_path_with_slash_prefix(self):
		data = {"a": {"b": {"c": 42}}}
		result = Reader._get_from_object_at_path(data, "/a/b/c")
		assert result == 42


class TestClassifyRelative:
	@staticmethod
	def test_definition():
		result = Reader.classify_relative("#/definitions/PermissionGetResult")
		assert result == (None, "definitions", "/definitions/PermissionGetResult")

	@staticmethod
	def test_long_path():
		result = Reader.classify_relative("../../../../../common-types/resource-management/v2/types.json#/parameters/SubscriptionIdParameter")
		assert result == (Path("../../../../../common-types/resource-management/v2/types.json"), "parameters", "/parameters/SubscriptionIdParameter")

	@staticmethod
	def test_with_current_directory():
		result = Reader.classify_relative("./common-types.json#/parameters/ResourceProviderNamespaceParameter")
		assert result == (Path("./common-types.json"), "parameters", "/parameters/ResourceProviderNamespaceParameter")

	# Add more tests to cover edge cases

	@staticmethod
	def test_invalid_input():
		with pytest.raises(IndexError):
			Reader.classify_relative("#invalid_input")

	@staticmethod
	def test_empty_input():
		with pytest.raises(ValueError):
			Reader.classify_relative("")

	@staticmethod
	def test_no_object_path():
		with pytest.raises(IndexError):
			Reader.classify_relative("file_path#")


class TestExamples:
	parser = TypeAdapter(Dict[str, Union[OAEnum, OADef]])

	def _load(self, raw):
		return self.parser.validate_python(raw)

	def test_rel(self):
		v = {
			"Workbook": {
				"description": "A workbook definition.",
				"type": "object",
				"allOf": [{"$ref": "#/definitions/WorkbookResource"}],
				"properties": {
					"properties": {"x-ms-client-flatten": True, "description": "Metadata describing a workbook for an Azure resource.", "$ref": "#/definitions/WorkbookProperties"},
					"systemData": {"$ref": "../../../../../common-types/resource-management/v1/types.json#/definitions/systemData", "readOnly": True},
				},
			}
		}
		t = self._load(v)
		assert t == {
			"Workbook": OADef(
				properties={
					"properties": OARef(ref="#/definitions/WorkbookProperties", description="Metadata describing a workbook for an Azure resource."),
					"systemData": OARef(ref="../../../../../common-types/resource-management/v1/types.json#/definitions/systemData", description=None),
				},
				type="object",
				description="A workbook definition.",
				allOf=[OARef(ref="#/definitions/WorkbookResource", description=None)],
				additionalProperties=False,
				required=None,
			)
		}


class TestIRTransformerResolveIRTStr:
	@staticmethod
	def test_basic():
		ir_t = IR_T(t=str)
		result = IRTransformer.resolve_ir_t_str(ir_t)
		assert result == "str"

	@staticmethod
	def test_ir_def():
		ir_def = IRDef(name="ExampleDefinition", properties={})
		ir_t = IR_T(t=ir_def)
		result = IRTransformer.resolve_ir_t_str(ir_t)
		assert result == "ExampleDefinition"

	@staticmethod
	def test_ir_list():
		ir_list = IR_List(items=IR_T(t=int))
		ir_t = IR_T(t=ir_list)
		result = IRTransformer.resolve_ir_t_str(ir_t)
		assert result == "List[int]"

	@staticmethod
	def test_ir_t():
		ir_t = IR_T(t="CustomType")
		result = IRTransformer.resolve_ir_t_str(ir_t)
		assert result == "CustomType"

	@staticmethod
	def test_none():
		ir_t = None
		result = IRTransformer.resolve_ir_t_str(ir_t)
		assert result == "None"


class TestIRTransformerResolveIRTStrReadOnlyAndRequired:
	@staticmethod
	def test_readonly():
		ir_t = IR_T(t=int, readonly=True)
		result = IRTransformer.resolve_ir_t_str(ir_t)
		assert result == "ReadOnly[int]"

	@staticmethod
	def test_optional():
		ir_t = IR_T(t=float, required=False)
		result = IRTransformer.resolve_ir_t_str(ir_t)
		assert result == "Optional[float]"

	@staticmethod
	def test_priority_readonly_greaterthan_optional():
		ir_t = IR_T(t=float, readonly=True, required=False)
		result = IRTransformer.resolve_ir_t_str(ir_t)
		assert result == "ReadOnly[float]"

	@staticmethod
	def test_no_modifiers():
		ir_t = IR_T(t=bool, readonly=False, required=True)
		result = IRTransformer.resolve_ir_t_str(ir_t)
		assert result == "bool"


class TestTransformPrimitives:
	def test_string(self):
		p = OADef.Property(type="string", description="description0")
		assert IRTransformer({}, None, RefCache()).resolve_type(p.t) == str


class TestIRTransformerUnifyIRT:
	@staticmethod
	def test_empty_list():
		ir_ts = []
		result = IRTransformer.unify_ir_t(ir_ts)
		assert result is None

	@staticmethod
	def test_single_type():
		ir_ts = [IR_T(t=str)]
		result = IRTransformer.unify_ir_t(ir_ts)
		assert result == IR_T(t="str", required=True)

	@staticmethod
	def test_multiple_types():
		ir_ts = [IR_T(t=int), IR_T(t=str)]
		result = IRTransformer.unify_ir_t(ir_ts)
		assert result == IR_T(t="Union[str, int]", required=True) or result == IR_T(t="Union[int, str]", required=True)

	@staticmethod
	def test_optional_type():
		ir_ts = [IR_T(t=int), IR_T(t="None")]
		result = IRTransformer.unify_ir_t(ir_ts)
		assert result == IR_T(t="int", required=False)

	@staticmethod
	def test_all_optional_types():
		ir_ts = [IR_T(t="None"), IR_T(t="None")]
		result = IRTransformer.unify_ir_t(ir_ts)
		assert result is None
