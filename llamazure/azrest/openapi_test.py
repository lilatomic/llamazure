"""Test the OpenAPI codegen"""
from pathlib import Path
from typing import Dict, Optional, Union

# pylint: disable=protected-access
import pytest
from pydantic import TypeAdapter

from llamazure.azrest.openapi import (
	IR_T,
	AZImport,
	IR_Dict,
	IR_Enum,
	IR_List,
	IR_Union,
	IRDef,
	IRParam,
	IRTransformer,
	JSONSchemaSubparser,
	OADef,
	OAEnum,
	OAParam,
	OARef,
	OAResponse,
	ParamPosition,
	PathLookupError,
	Reader,
	RefCache,
)


def empty_jsp() -> JSONSchemaSubparser:
	return JSONSchemaSubparser(Reader("", Path(), {}, {}), RefCache())


class TestResolveReference:
	"""Test resolving references"""

	def test_get_from_object_at_path_valid_path(self):
		data = {"a": {"b": {"c": 42}}}
		result = Reader._get_from_object_at_path(data, "a/b/c")
		assert result == 42

	def test_get_from_object_at_path_invalid_path(self):
		data = {"a": {"b": {"c": 42}}}
		with pytest.raises(PathLookupError):
			Reader._get_from_object_at_path(data, "a/b/d")

	def test_get_from_object_at_path_invalid_object(self):
		data = {"a": {"b": {"c": 42}}}
		with pytest.raises(PathLookupError):
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
		assert empty_jsp().resolve_type(p.t) == str

	def test_nonhandled(self):
		tgt = "whatever"
		p = OADef.Property(type=tgt, description="description0")
		assert empty_jsp().resolve_type(p.t) == tgt


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
		assert result == IR_T(t=str, required=True)

	@staticmethod
	def test_multiple_types():
		ir_ts = [IR_T(t=int), IR_T(t=str)]
		result = IRTransformer.unify_ir_t(ir_ts)
		assert result == IR_T(t=IR_Union(items=[IR_T(t=str), IR_T(t=int)]), required=True) or result == IR_T(t=IR_Union(items=[IR_T(t=int), IR_T(t=str)]), required=True)

	@staticmethod
	def test_optional_type():
		ir_ts = [IR_T(t=int), IR_T(t="None")]
		result = IRTransformer.unify_ir_t(ir_ts)
		assert result == IR_T(t=int, required=False)

	@staticmethod
	def test_all_optional_types():
		ir_ts = [IR_T(t="None"), IR_T(t="None")]
		result = IRTransformer.unify_ir_t(ir_ts)
		assert result is None


class TestIRTransformerImports:
	tgt_path = Path("other/place")
	ir_import = IRDef(name="Import", properties={}, src=tgt_path)
	az_import = AZImport(path=tgt_path, names={"Import"})

	def empty_irtransformer(self) -> IRTransformer:
		return IRTransformer({}, {}, Reader("", Path(), {}, {}), RefCache())

	local_path = Path("path/to/src")
	simple_cases = [
		("IR_T", IR_T(t=ir_import), [az_import]),
		("IR_Enum", IR_Enum(name="name0", values=[]), []),
		("IR_List", IR_List(items=IR_T(t=ir_import)), [az_import]),
		("IR_Dict", IR_Dict(keys=IR_T(t="str"), values=IR_T(t=ir_import)), [az_import]),
		("str", "some string", []),
		("type", int, []),
	]

	@pytest.mark.parametrize("type_name,ir,expected", simple_cases, ids=[case[0] for case in simple_cases])
	def test_find_imports(self, type_name, ir, expected):
		self._do_test(ir, expected)

	def _do_test(self, ir, expected):
		irt = self.empty_irtransformer()
		result = irt._find_imports(ir, "path/to/src")
		assert result == expected

		without_local = irt._remove_local_imports(self.local_path, result)
		assert not any(e.path == self.local_path for e in without_local)

	def test_find_import_transitive_not_explored(self):
		"""Test that we don't transitively include everything"""
		ir = IRDef(properties={"prop1": IR_T(t=self.ir_import)}, src=self.local_path, name="DefName")
		expected = [AZImport(path=Path("path/to/src"), names={"DefName"})]
		self._do_test(ir, expected)


class TestJSONSchemaParams:
	def do_test(self, parameter, expected, additional_params: Optional[Dict[str, Union[OAParam, OARef]]] = None):
		openapi = {}
		if additional_params:
			openapi["parameters"] = additional_params

		reader = Reader("", Path(), openapi, {})
		j = JSONSchemaSubparser(reader, RefCache())

		actual = j.ir_param(parameter)
		assert actual == expected

	def test_list_param(self):
		p = OAParam(
			**{
				"name": "tags",
				"in": "query",
				"required": False,
				"type": "array",
				"items": {"type": "string"},
				"collectionFormat": "csv",
				"description": "Tags presents on each workbook returned.",
				"x-ms-parameter-location": "method",
			}
		)
		self.do_test(
			p,
			IRParam(t=IR_T(t=IR_List(items=IR_T(t=str)), required=False), name="tags", position=ParamPosition.query),
		)

	def test_ref(self):
		name = "SubscriptionIdParameter"
		p = OARef(ref=f"#/parameters/{name}")
		resolved_name = "subscriptionId"
		resolved = OAParam(**{"name": resolved_name, "in": "path", "required": True, "type": "string", "description": "The ID of the target subscription.", "minLength": 1})
		self.do_test(p, IRParam(t=IR_T(t=str), name="subscriptionId", position=ParamPosition.path), additional_params={name: resolved})


class TestJSONSchemaDefs:
	def do_test(self, definitions, target_def, expected):
		reader = Reader("", Path(), {"definitions": definitions, "paths": {}}, {})
		ir = IRTransformer.from_reader(reader)

		target = ir.oa_defs[target_def]

		result = ir.jsonparser.transform(target_def, target, required_properties=[])
		assert result == expected
		return result

	openapi_Resource = {
		"title": "Resource",
		"description": "Common fields that are returned in the response for all Azure Resource Manager resources",
		"type": "object",
		"properties": {
			"id": {
				"readOnly": True,
				"type": "string",
				"description": "Fully qualified resource ID for the resource. Ex - /subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/{resourceProviderNamespace}/{resourceType}/{resourceName}",
			},
			"name": {"readOnly": True, "type": "string", "description": "The name of the resource"},
			"type": {
				"readOnly": True,
				"type": "string",
				"description": 'The type of the resource. E.g. "Microsoft.Compute/virtualMachines" or "Microsoft.Storage/storageAccounts"',
			},
		},
		"x-ms-azure-resource": True,
	}

	def test_enum_sample(self):
		name = "SystemAssignedServiceIdentityType"
		d = {
			name: {
				"description": "Type of managed service identity (either system assigned, or none).",
				"enum": ["None", "SystemAssigned"],
				"type": "string",
				"x-ms-enum": {"name": "SystemAssignedServiceIdentityType", "modelAsString": False},
			}
		}
		self.do_test(d, "SystemAssignedServiceIdentityType", IR_T(t=IR_Enum(name=name, values=d[name]["enum"], description=d[name]["description"]), required=False))

	def test_full_inherit(self):
		name = "ProxyResource"
		d = {
			name: {
				"title": "Proxy Resource",
				"description": "The resource model definition for a Azure Resource Manager proxy resource. It will not have tags and a location",
				"type": "object",
				"allOf": [{"$ref": "#/definitions/Resource"}],
			},
			"Resource": self.openapi_Resource,
		}
		self.do_test(
			d,
			name,
			IR_T(
				t=IRDef(
					name="Resource",
					properties={
						"id": IR_T(t=str, readonly=True, required=False),
						"name": IR_T(t=str, readonly=True, required=False),
						"type": IR_T(t=str, readonly=True, required=False),
					},
					description="Common fields that are returned in the response for all Azure Resource Manager resources",
					src=Path("."),
				),
				readonly=False,
				required=False,
			),
		)

	def test_dict(self):
		name = "DashboardPartMetadata"
		d = {
			name: {
				"type": "object",
				"required": ["type"],
				"description": "A dashboard part metadata.",
				"additionalProperties": True,
				"properties": {"type": {"type": "string", "description": "The type of dashboard part."}},
				"discriminator": "type",
			},
		}
		self.do_test(d, name, IR_T(t=IR_Dict(keys=IR_T(t=str), values=IR_T(t=str)), required=False))

	def test_dict__typed(self):
		"""Test for a dict whose values are typed."""
		name = "TrackedResource"
		d = {
			name: {
				"title": "Tracked Resource",
				"type": "object",
				"properties": {
					"tags": {"type": "object", "additionalProperties": {"type": "string"}, "description": "Resource tags."},
				},
				"required": ["location"],
			},
		}

		tags_ir_t = IR_T(t=IR_Dict(keys=IR_T(t=str), values=IR_T(t=str)), required=False)
		self.do_test(d, name, IR_T(t=IRDef(name=name, properties={"tags": tags_ir_t}, src="."), required=False))

	def test_allof_ref_and_properties(self):
		name = "TrackedResource"
		d = {
			name: {
				"title": "Tracked Resource",
				"description": "The resource model definition for an Azure Resource Manager tracked top level resource which has 'tags' and a 'location'",
				"type": "object",
				"properties": {
					"tags": {"type": "object", "additionalProperties": {"type": "string"}, "x-ms-mutability": ["read", "create", "update"], "description": "Resource tags."},
					"location": {"type": "string", "x-ms-mutability": ["read", "create"], "description": "The geo-location where the resource lives"},
				},
				"required": ["location"],
				"allOf": [{"$ref": "#/definitions/Resource"}],
			},
			"Resource": self.openapi_Resource,
		}

		tags_ir_t = IR_T(t=IR_Dict(keys=IR_T(t=str), values=IR_T(t=str)), required=False)
		self.do_test(
			d,
			name,
			IR_T(
				t=IRDef(
					name="TrackedResource",
					properties={
						"tags": tags_ir_t,
						"location": IR_T(t=str),
						"id": IR_T(t=str, readonly=True, required=False),
						"name": IR_T(t=str, readonly=True, required=False),
						"type": IR_T(t=str, readonly=True, required=False),
					},
					description="The resource model definition for an Azure Resource Manager tracked top level resource which has 'tags' and a 'location'",
					src=Path("."),
				),
				required=False,
			),
		)

	def test_self_referential(self):
		name = "ErrorDefinition"
		d = {
			name: {
				"type": "object",
				"description": "Error definition.",
				"properties": {
					"code": {
						"description": "Service specific error code which serves as the substatus for the HTTP error code.",
						"type": "integer",
						"format": "int32",
						"readOnly": True,
					},
					"message": {"description": "Description of the error.", "type": "string", "readOnly": True},
					"details": {
						"description": "Internal error details.",
						"type": "array",
						"items": {"$ref": "#/definitions/ErrorDefinition"},
						"x-ms-identifiers": ["code"],
						"readOnly": True,
					},
				},
			}
		}
		self.do_test(
			d,
			name,
			IR_T(
				t=IRDef(
					name="ErrorDefinition",
					properties={
						"code": IR_T(t=int, readonly=True, required=False),
						"message": IR_T(t=str, readonly=True, required=False),
						"details": IR_T(t=IR_List(items=IR_T(t="ErrorDefinition"))),
					},
					description="Error definition.",
					src=Path("."),
				),
				readonly=False,
				required=False,
			),
		)


class TestJSONSchemaResponse:

	oa_response = OAResponse

	def jsp(self) -> JSONSchemaSubparser:
		openapi = {
			"definitions": {
				"Dashboard": {
					"type": "object",
					"description": "The shared dashboard resource definition.",
					"required": ["location"],
					"properties": {
						"id": {"readOnly": True, "type": "string", "description": "Resource Id"},
					},
				},
				"VirtualMachineExtensionImage": {
					"type": "object",
					"description": "description0",
					"properties": {
						"id": {"type": "string", "description": "Resource Id"},
					},
				},
				"ServiceBusManagementError": {
					"description": "The error response from Service Bus.",
					"type": "object",
					"properties": {
						"code": {"description": "The service error code.", "type": "integer", "format": "int32", "xml": {"name": "Code"}},
						"detail": {"description": "The service error message.", "type": "string", "xml": {"name": "Detail"}},
					},
				},
			},
			"responses": {
				"ServiceBusManagementErrorResponse": {
					"description": "An error occurred. The possible HTTP status, code, and message strings are listed below",
					"headers": {
						"x-ms-request-id": {
							"description": "A server-generated UUID recorded in the analytics logs for troubleshooting and correlation.",
							"pattern": "^[{(]?[0-9a-f]{8}[-]?([0-9a-f]{4}[-]?){3}[0-9a-f]{12}[)}]?$",
							"type": "string",
						},
						"x-ms-version": {"description": "The version of the REST protocol used to process the request.", "type": "string"},
					},
					"schema": {"$ref": "#/definitions/ServiceBusManagementError"},
				}
			},
		}
		return JSONSchemaSubparser(openapi=Reader("", Path(), openapi, {}), refcache=RefCache())

	def test_schema_reference(self):
		actual = self.jsp().ir_response(OAResponse(**{"description": "OK response definition.", "schema": OARef(ref="#/definitions/Dashboard")}))
		assert actual == IR_T(
			t=IRDef(name="Dashboard", properties={"id": IR_T(t=str, readonly=True, required=False)}, description="The shared dashboard resource definition.", src=Path("."))
		)

	def test_reference(self):
		actual = self.jsp().ir_response(OARef(ref="#/responses/ServiceBusManagementErrorResponse"))
		assert actual == IR_T(
			t=IRDef(
				name="ServiceBusManagementError",
				properties={"code": IR_T(t=int, required=False), "detail": IR_T(t=str, required=False)},
				description="The error response from Service Bus.",
				src=Path("."),
			)
		)

	def test_inline(self):
		actual = self.jsp().ir_response(
			OAResponse.model_validate({"description": "OK", "schema": {"type": "array", "items": {"$ref": "#/definitions/VirtualMachineExtensionImage"}}})
		)
		assert actual == IR_T(
			t=IR_List(items=IR_T(t=IRDef(name="VirtualMachineExtensionImage", properties={"id": IR_T(t=str, required=False)}, description="description0", src=Path("."))))
		)
