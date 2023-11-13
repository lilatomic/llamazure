"""
OpenAPI explorer for Azure

Naming Conventions:
- OA* : OpenAPI things
- IR* : Intermediate Representation of things
- AZ* : Azure things
OA things are used to parse the OpenAPI spec.
AZ things are used for reasoning about the Azure API.
For example, PermissionGetResult might be an OA object because it is present in the OpenAPI spec.
However, it's just a list of Permission objects.
It won't have an AZ object; instead, it will be transformed into something like an AZList[AZPermission].
"""
from __future__ import annotations

import itertools
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from textwrap import dedent, indent
from typing import Dict, List, Literal, Optional, Type, Union

from pydantic import BaseModel, Field, TypeAdapter

from llamazure.azrest.models import AzList

logger = logging.getLogger(__name__)


class OADef(BaseModel):
	class Array(BaseModel):
		t: Literal["array"] = Field(alias="type", default="array")
		items: Union[OADef.Property, OADef.Ref]
		description: Optional[str] = None

	class Property(BaseModel):
		t: Union[str] = Field(alias="type")
		description: Optional[str] = None

	class Ref(BaseModel):
		ref: str = Field(alias="$ref")
		description: Optional[str] = None

	properties: Dict[str, Union[OADef.Array, OADef.Property, OADef.Ref]]
	t: str = Field(alias="type")
	description: Optional[str] = None


class IRDef(BaseModel):
	name: str
	properties: Dict[str, IR_T]
	description: Optional[str] = None


class IR_T(BaseModel):
	t: Union[Type, IRDef, IR_List, str]  # TODO: upconvert str


class IR_List(BaseModel):
	items: IR_T


any_ir_t = Union[IRDef, IR_T, IR_List]


class Reader:
	"""Read Microsoft OpenAPI specifications"""

	def __init__(self, openapi: dict):
		self.doc = openapi

	@classmethod
	def load(cls, fp) -> Reader:
		"""Load from a path or file-like object"""
		if isinstance(fp, (str, Path)):
			with open(fp, mode="r", encoding="utf-8") as fp:
				return Reader(json.load(fp))
		else:
			return Reader(json.load(fp))

	@property
	def paths(self):
		"""Get API paths (standard and ms xtended)"""
		return list(itertools.chain(self.doc["paths"].items(), self.doc.get("x-ms-paths", {}).items()))

	@property
	def definitions(self):
		return self.doc["definitions"]


def operations(path_object: dict):
	"""Extract operations from an OpenAPI Path object"""
	return {k: v for k, v in path_object.items() if k in {"get", "put", "post", "delete", "options", "head", "patch", "trace"}}


def definitions(ds: dict):
	"""Extract OpenAPI defintions"""
	parser = TypeAdapter(Dict[str, OADef])
	return parser.validate_python(ds)


def resolve_field_type(field: Union[OADef.Array, OADef.Property, OADef.Ref]):
	if isinstance(field, OADef.Array):
		logger.error("NI Array")
		return field
	elif isinstance(field, OADef.Property):
		return field.t
	elif isinstance(field, OADef.Ref):
		return field.ref


def resolve_path(path: str) -> str:
	if path.startswith("#/definitions/"):
		return path[len("#/definitions/") :]
	return path


def dereference_refs(ds: Dict[str, OADef]) -> Dict[str, OADef]:
	"""Inflate refs to their objects"""
	out = {}
	for name, obj in ds.items():
		new_props: Dict[str, Union[OADef.Array, OADef.Property, OADef.Ref]] = {}
		for prop_name, prop in obj.properties.items():
			if isinstance(prop, OADef.Ref):
				ref_target = resolve_path(prop.ref)
				ref = ds[ref_target]
				new_props[prop_name] = OADef.Property(type=ref, description=prop.description)
			else:
				new_props[prop_name] = prop
		obj.properties = new_props
		out[name] = obj

	return out


class IRTransformer:
	def __init__(self, defs: Dict[str, OADef]):
		self.oa_defs: Dict[str, OADef] = defs

	def transform(self) -> str:
		irs = {}
		for name, obj in self.oa_defs.items():
			irs[name] = self.transform_def(name, obj)

		ir_props = {}
		for name, ir in irs.items():
			if "properties" in ir.properties:
				prop_t = ir.properties["properties"].t
				assert isinstance(prop_t, str)  # TODO: Better checking or coercion
				prop_ref = prop_t
				ir_props[prop_ref] = irs[prop_ref]

		ir_azlists: Dict[str, AZAlias] = {}
		for name, ir in irs.items():
			azlist = self.ir_azarray(ir)
			if azlist:
				ir_azlists[name] = azlist

		ir_consumed = ir_props.keys() | ir_azlists.keys()
		ir_defs = {}
		for name, ir in irs.items():
			if name not in ir_consumed:
				ir_defs[name] = ir
		azs = [self.defIR2AZ(ir) for ir in ir_defs.values()]

		output_req: List[CodeGenable] = azs + list(ir_azlists.values())

		return "\n\n".join([cg.codegen() for cg in output_req])

	def transform_def(self, name: str, obj: OADef) -> IRDef:
		ir_properties = {p_name: self.transform_oa_field(p) for p_name, p in obj.properties.items()}
		return IRDef(
			name=name,
			properties=ir_properties,
			description=obj.description,
		)

	def transform_oa_field(self, p: Union[OADef.Array, OADef.Property, OADef.Ref]) -> IR_T:
		if isinstance(p, OADef.Property):
			return self.def_OA2IR(p)
		elif isinstance(p, OADef.Array):
			return self.ir_array(p)
		elif isinstance(p, OADef.Ref):
			return IR_T(t=resolve_path(p.ref))

	def def_OA2IR(self, p: OADef.Property) -> IR_T:
		py_type = {
			"string": str,
		}.get(p.t, p.t)
		return IR_T(t=py_type)

	def ir_array(self, obj: OADef.Array) -> IR_T:
		if isinstance(obj.items, OADef.Property):
			# Probably a type
			as_list = IR_List(items=self.def_OA2IR(obj.items))
		elif isinstance(obj.items, OADef.Ref):
			# TODO: implement actual resolution
			# ref = self.defs[resolve_path(obj.items.ref)]
			# l = IR_List(items=IR_T(t=ref))

			as_list = IR_List(items=IR_T(t=resolve_path(obj.items.ref)))

		else:
			raise NotImplementedError("List of List not supported")

		return IR_T(t=as_list)

	def ir_azarray(self, obj: IRDef) -> Optional[AZAlias]:
		value = obj.properties.get("value")
		if value is not None and isinstance(value.t, IR_List):
			inner = self.resolve_ir_t_str(value.t.items)
			return AZAlias(name=obj.name, alias=f"{AzList.__name__}[{inner}]")
		else:
			return None

	@staticmethod
	def resolve_ir_t_str(ir_t: IR_T) -> str:
		t = ir_t.t
		if isinstance(t, type):
			return t.__name__
		elif isinstance(t, IRDef):
			return t.name
		elif isinstance(t, IR_List):
			inner = IRTransformer.resolve_ir_t_str(t.items)
			return f"List[{inner}]"
		elif isinstance(t, str):
			return t
		else:
			raise ValueError(f"Expected {IR_T} got {type(ir_t)}")

	@staticmethod
	def fieldsIR2AZ(fields: Dict[str, IR_T]) -> Dict[str, str]:
		az_fields = {}

		for f_name, f_type in fields.items():
			if f_name == "properties":
				# assert isinstance(f_type, IRDef)
				v = "Properties"
			else:
				v = IRTransformer.resolve_ir_t_str(f_type)
			az_fields[f_name] = v

		return az_fields

	def defIR2AZ(self, irdef: IRDef) -> AZDef:

		if "properties" in irdef.properties:
			prop_container = irdef.properties["properties"]
			prop_t = prop_container.t
			assert isinstance(prop_t, str)  # TODO: Better checking or coercion
			prop_c_oa = self.oa_defs[prop_t]
			prop_c_ir = self.transform_def(prop_t, prop_c_oa)
			prop_c_az = self.defIR2AZ(prop_c_ir)

			property_c = prop_c_az.model_copy(update={"name": "Properties"})

		else:
			property_c = None

		return AZDef(name=irdef.name, description=irdef.description, fields=IRTransformer.fieldsIR2AZ(irdef.properties), property_c=property_c)


class CodeGenable(ABC):
	@abstractmethod
	def codegen(self) -> str:
		...


class AZDef(BaseModel, CodeGenable):
	name: str
	description: Optional[str]
	fields: Dict[str, str]
	property_c: Optional[AZDef] = None

	def codegen_field(self, f_name, f_type) -> str:
		if f_name == "id":
			return f'rid: {f_type} = Field(alias="id", default=None)'
		return f"{f_name}: {f_type}"

	def codegen(self) -> str:
		if self.property_c:
			property_c_codegen = indent(self.property_c.codegen(), "\t")
		else:
			property_c_codegen = ""

		fields = indent("\n".join(self.codegen_field(f_name, f_type) for f_name, f_type in self.fields.items()), "\t")

		return dedent(
			'''\
		class {name}(BaseModel):
			"""{description}"""
		{property_c_codegen}
		{fields}
		'''
		).format(name=self.name, description=self.description, property_c_codegen=property_c_codegen, fields=fields)


class AZAlias(BaseModel, CodeGenable):
	name: str
	alias: str

	def codegen(self) -> str:
		return f"{self.name} = {self.alias}"


if __name__ == "__main__":
	import sys

	reader = Reader.load(sys.argv[1])

	oa_defs = definitions(reader.definitions)

	transformer = IRTransformer(oa_defs)
	codegen = transformer.transform()

	# out: dict[str, dict[str, Any]] = defaultdict(dict)
	# for path, pathobj in reader.paths:
	# 	for method, operationobj in operations(pathobj).items():
	# 		out[path][method] = {k: operationobj[k] for k in ("description", "operationId")}
	#

	# print(q)
	# print(json.dumps([x.model_dump() for x in q]))
	print(codegen)
