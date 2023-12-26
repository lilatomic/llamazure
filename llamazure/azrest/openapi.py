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
# pylint: disable=consider-using-f-string
from __future__ import annotations

import itertools
import json
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from pathlib import Path
from textwrap import dedent, indent
from typing import Dict, List, Literal, Optional, Sequence, Tuple, Type, Union, cast

import requests
from pydantic import BaseModel, Field, TypeAdapter

from llamazure.azrest.models import AzList

logger = logging.getLogger(__name__)


class PathLookupError(Exception):
	"""Could not look up an OpenAPI reference"""

	def __init__(self, object_path: str):
		self.object_path = object_path
		super().__init__(f"Error while looking up path: {object_path}")


class OARef(BaseModel):
	"""An OpenAPI reference"""

	ref: str = Field(alias="$ref")
	description: Optional[str] = None

	class Config:
		allow_population_by_field_name = True

	@property
	def name(self) -> str:
		"""The name of this Definition"""
		return self.ref.split("/")[-1]


class OADef(BaseModel):
	"""An OpenAPI definition"""

	class Array(BaseModel):
		"""An Array field of an OpenAPI definition"""

		t: Literal["array"] = Field(alias="type", default="array")
		items: Union[OADef.Property, OARef]
		description: Optional[str] = None

	class Property(BaseModel):
		"""A normal field of an OpenAPI definition"""

		t: Union[str] = Field(alias="type")
		description: Optional[str] = None
		readOnly: bool = False
		required: bool = False

	properties: Dict[str, Union[OADef.Array, OADef.Property, OARef]]
	t: str = Field(alias="type")
	description: Optional[str] = None


class OAParam(BaseModel):
	"""A Param for an OpenAPI Operation"""

	name: str
	in_component: str = Field(alias="in")
	required: bool = True
	type: Optional[str] = None
	description: str
	oa_schema: Optional[OARef] = Field(alias="schema", default=None)


class OAResponse(BaseModel):
	"""A response for an OpenAPI Operation"""

	description: str
	oa_schema: Optional[OARef] = Field(alias="schema", default=None)


class OAMSPageable(BaseModel):
	"""MS Pageable extension"""

	nextLinkName: str


class OAOp(BaseModel):
	"""An OpenAPI Operation"""

	tags: List[str]
	operationId: str
	description: str
	parameters: List[Union[OAParam, OARef]]
	responses: Dict[str, OAResponse]
	pageable: Optional[OAMSPageable] = Field(alias="x-ms-pageable", default=None)

	@property
	def body_params(self) -> List[OAParam]:
		"""Parameters that belong in the body"""
		return [p for p in self.parameters if isinstance(p, OAParam) and p.in_component == "body"]

	@property
	def url_params(self) -> List[OAParam]:
		"""Parameters that belong in the URL"""
		return [p for p in self.parameters if isinstance(p, OAParam) and p.in_component == "path"]


class OAPath(BaseModel):
	"""An OpenAPI Path item"""

	get: Optional[OAOp] = None
	put: Optional[OAOp] = None
	post: Optional[OAOp] = None
	delete: Optional[OAOp] = None
	options: Optional[OAOp] = None
	head: Optional[OAOp] = None
	patch: Optional[OAOp] = None

	def items(self) -> Sequence[Tuple[str, OAOp]]:
		return [(k, v) for k, v in dict(self).items() if v is not None]


class IROp(BaseModel):
	"""An IR Operation"""

	object_name: str
	name: str
	description: Optional[str]

	path: str
	method: str
	apiv: Optional[str]
	body_name: Optional[str] = None
	body: Optional[IR_T] = None
	params: Optional[Dict[str, IR_T]]
	ret_t: Optional[IR_T] = None


class IRDef(BaseModel):
	"""An IR Definition"""

	name: str
	properties: Dict[str, IR_T]
	description: Optional[str] = None


class IR_T(BaseModel):
	"""An IR Type descriptor"""

	t: Union[Type, IRDef, IR_List, str]  # TODO: upconvert str
	readonly: bool = False
	required: bool = True


class IR_List(BaseModel):
	"""An IR descriptor for a List type"""

	items: IR_T
	required: bool = True


class Reader:
	"""Read Microsoft OpenAPI specifications"""

	def __init__(self, root: str, path: Path, openapi: dict):
		self.root = root
		self.path = path
		self.doc = openapi

	@classmethod
	def load(cls, root: str, path: Path) -> Reader:
		"""Load from a path or file-like object"""
		return Reader(root, path, cls._load_file(root, path))

	@property
	def paths(self):
		"""Get API paths (standard and ms xtended)"""
		return dict(itertools.chain(self.doc["paths"].items(), self.doc.get("x-ms-paths", {}).items()))

	@property
	def definitions(self):
		"""The OpenAPI definition in this doc"""
		return self.doc["definitions"]

	@property
	def apiv(self) -> str:
		"""Azure API version"""
		return self.doc["info"]["version"]

	@staticmethod
	def classify_relative(relative: str) -> tuple[str, str, str]:
		"""Decompose an OpenAPI reference into its filepath, item type, and path inside that document"""
		file_path, object_path = relative.split("#")
		oa_type = object_path.split("/")[1]
		return file_path, oa_type, object_path

	def load_relative(self, relative: str) -> dict:
		"""Load an object from a relative path"""
		file_path, _, object_path = self.classify_relative(relative)

		if file_path:
			file = self._load_file(self.root, self.path.parent / file_path)
		else:
			file = self.doc

		return self._get_from_object_at_path(file, object_path)

	@staticmethod
	def _get_from_object_at_path(file: dict, object_path: str) -> dict:
		"""Load an object from a path in a different file"""
		try:
			o = file
			for segment in object_path.split("/"):
				if segment:  # escape empty segments
					o = o[segment]
			return o
		except (KeyError, TypeError):
			# Raise a custom exception with a helpful message including the object_path
			raise PathLookupError(object_path)

	@staticmethod
	def _load_file(root: str, file_path: Path):
		"""Load the contents of a file"""
		if root.startswith("https://") or root.startswith("http://"):
			content = requests.get(root + file_path.as_posix()).content.decode("utf-8")
		elif root.startswith("file://"):
			file_root = root.split("://")[1]
			with (Path(file_root) / file_path).open(mode="r", encoding="utf-8") as fp:
				content = fp.read()
		else:
			scheme = root.split("://")[0]
			raise ValueError(f"unknown uri scheme scheme={scheme}")
		return json.loads(content)


def resolve_path(path: str) -> str:
	"""Resolve a path in an OpenAPI spec to the OpenAPI definition it references"""
	if path.startswith("#/definitions/"):
		return path[len("#/definitions/") :]
	return path


class IRTransformer:
	"""Transformer to and from the IR"""

	def __init__(self, defs: Dict[str, OADef], openapi: Reader):
		self.oa_defs: Dict[str, OADef] = defs
		self.openapi = openapi

	def transform_definitions(self) -> str:
		"""Transform the OpenAPI objects into their codegened str"""
		ir_definitions = {}
		for name, obj in self.oa_defs.items():
			ir_definitions[name] = self.transform_def(name, obj)

		ir_properties_classes = self.identify_definition_properties_classes(ir_definitions)

		ir_azlists = self.identify_azlists(ir_definitions)

		azs = self.identify_definitions(ir_azlists, ir_definitions, ir_properties_classes)

		output_req: List[CodeGenable] = azs + list(ir_azlists.values())

		return self.codegen_definitions(azs, ir_azlists, output_req)

	@staticmethod
	def identify_definition_properties_classes(ir_definitions: Dict[str, IRDef]):
		"""Identify the classes that are nested Properties classes"""
		ir_properties_classes = {}
		for name, ir in ir_definitions.items():
			if "properties" in ir.properties:
				prop_t = ir.properties["properties"].t
				assert isinstance(prop_t, str)  # TODO: Better checking or coercion
				prop_ref = prop_t
				ir_properties_classes[prop_ref] = ir_definitions[prop_ref]
		return ir_properties_classes

	def identify_azlists(self, ir_definitions):
		ir_azlists: Dict[str, AZAlias] = {}
		for name, ir in ir_definitions.items():
			azlist = self.ir_azarray(ir)
			if azlist:
				ir_azlists[name] = azlist
		return ir_azlists

	def identify_definitions(self, ir_azlists, ir_definitions, ir_props):
		ir_consumed = ir_props.keys() | ir_azlists.keys()
		ir_defs = {}
		for name, ir in ir_definitions.items():
			if name not in ir_consumed:
				ir_defs[name] = ir
		azs = [self.defIR2AZ(ir) for ir in ir_defs.values()]
		return azs

	@staticmethod
	def codegen_definitions(azs: List[AZDef], ir_azlists: Dict[str, AZAlias], output_req: List[CodeGenable]):
		codegened_definitions = [cg.codegen() for cg in output_req]
		reloaded_definitions = [f"{az_definition.name}.model_rebuild()" for az_definition in azs] + [f"{az_list.name}.model_rebuild()" for az_list in ir_azlists.values()]
		return "\n\n".join(codegened_definitions + reloaded_definitions) + "\n\n"

	def transform_def(self, name: str, obj: OADef) -> IRDef:
		"""Transform an OpenAPI definition to IR"""
		ir_properties = {p_name: self.transform_oa_field(p) for p_name, p in obj.properties.items()}
		return IRDef(
			name=name,
			properties=ir_properties,
			description=obj.description,
		)

	@staticmethod
	def transform_oa_field(p: Union[OADef.Array, OADef.Property, OARef, None]) -> IR_T:
		"""Transform an OpenAPI field"""
		if isinstance(p, OADef.Property):
			resolved_type = IRTransformer.resolve_type(p.t)
			return IR_T(t=resolved_type, readonly=p.readOnly, required=p.required)
		elif isinstance(p, OADef.Array):
			return IRTransformer.ir_array(p)
		elif isinstance(p, OARef):
			return IR_T(t=resolve_path(p.ref))
		elif p is None:
			return IR_T(t="None")
		else:
			raise TypeError("unsupported OpenAPI field")

	@staticmethod
	def resolve_type(t: str) -> Union[str, type]:
		"""Resolve OpenAPI types to Python types, if applicable"""
		py_type = {
			"string": str,
			"number": float,
			"integer": int,
			"boolean": bool,
		}.get(t, t)
		return py_type

	@staticmethod
	def ir_array(obj: OADef.Array) -> IR_T:
		"""Transform an OpenAPI array to IR"""
		if isinstance(obj.items, OADef.Property):
			# Probably a type
			as_list = IR_List(items=IR_T(t=IRTransformer.resolve_type(obj.items.t), required=True))
		elif isinstance(obj.items, OARef):
			# TODO: implement actual resolution
			# ref = self.defs[resolve_path(obj.items.ref)]
			# l = IR_List(items=IR_T(t=ref))

			as_list = IR_List(items=IR_T(t=resolve_path(obj.items.ref), required=True))

		else:
			# I think this is blocked by Pydantic type definitions
			raise NotImplementedError("List of List not supported")

		return IR_T(t=as_list, required=True)

	@staticmethod
	def ir_azarray(obj: IRDef) -> Optional[AZAlias]:
		"""Transform a definition representing an array into an alias to the wrapped type"""
		value = obj.properties.get("value")
		if value is not None and isinstance(value.t, IR_List):
			inner = IRTransformer.resolve_ir_t_str(value.t.items)
			return AZAlias(name=obj.name, alias=f"{AzList.__name__}[{inner}]")
		else:
			return None

	@staticmethod
	def resolve_ir_t_str(ir_t: Union[IR_T, None]) -> str:
		"""Resolve the IR type to the stringified Python type"""
		if ir_t is None:
			return "None"

		declared_type = ir_t.t
		if isinstance(declared_type, type):
			type_as_str = declared_type.__name__
		elif isinstance(declared_type, IRDef):
			type_as_str = declared_type.name
		elif isinstance(declared_type, IR_List):
			type_as_str = "List[%s]" % IRTransformer.resolve_ir_t_str(declared_type.items)
		elif isinstance(declared_type, str):
			type_as_str = declared_type
		else:
			raise TypeError(f"Cannot handle {type(declared_type)}")

		if ir_t.readonly:
			return "ReadOnly[%s]" % type_as_str
		elif not ir_t.required:
			return "Optional[%s]" % type_as_str
		else:
			return type_as_str

	@staticmethod
	def fieldsIR2AZ(fields: Dict[str, IR_T]) -> List[AZField]:
		"""Convert IR fields to AZ fields"""
		az_fields = []

		for f_name, f_type in fields.items():
			if f_name == "properties":
				# assert isinstance(f_type, IRDef)
				t = "Properties"
			else:
				t = IRTransformer.resolve_ir_t_str(f_type)

			if isinstance(f_type.t, IR_List):
				v = "[]"
			elif f_type.readonly or not f_type.required:
				v = "None"
			else:
				v = None

			az_fields.append(AZField(name=f_name, t=t, default=v, readonly=f_type.readonly))

		return az_fields

	def defIR2AZ(self, irdef: IRDef) -> AZDef:
		"""Convert IR Defs to AZ Defs"""

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

	@staticmethod
	def paramOA2IR(oaparam: OAParam) -> IR_T:
		"""
		Convert an OpenAPI Parameter to IR Parameter

		If the param belongs in the body, it will have a schema and nothing else
		Otherwise, it will always have a valid type
		"""
		if oaparam.oa_schema:
			return IRTransformer.transform_oa_field(oaparam.oa_schema)
		else:
			assert oaparam.type, "OAParam without schema does not have a type"
			return IR_T(t=IRTransformer.resolve_type(oaparam.type))

	@staticmethod
	def unify_ir_t(ir_ts: List[IR_T]) -> Optional[IR_T]:
		"""Unify IR types, usually for returns"""
		ts = set(IRTransformer.resolve_ir_t_str(t) for t in ir_ts if t)

		is_required = "None" not in ts
		non_none = ts - {"None"}

		if len(non_none) == 0:
			return None
		elif len(non_none) == 1:
			return IR_T(t=non_none.pop(), required=is_required)
		else:
			return IR_T(t=f"Union[{', '.join(non_none)}]", required=is_required)

	def transform_paths(self, paths: dict, apiv: str) -> str:
		"""Transform OpenAPI Paths into the Python code for the Azure objects"""
		parser = TypeAdapter(Dict[str, OAPath])
		parsed = parser.validate_python(paths)

		resolved = self.resolve_parameters_in_oapath(parsed)

		ops: List[IROp] = []
		for path, path_item in resolved.items():
			for method, op in path_item.items():
				ops.append(self.oa2ir_op(apiv, path, method, op))

		az_objs: Dict[str, List[IROp]] = defaultdict(list)
		for ir_op in ops:
			az_objs[ir_op.object_name].append(ir_op)

		az_ops = []
		for name, ir_ops in az_objs.items():
			az_ops.append(
				AZOps(
					name=name,
					ops=[self.ir2az_op(name, x) for x in ir_ops],
					apiv=apiv,
				)
			)

		return "\n\n".join([cg.codegen() for cg in az_ops])

	@staticmethod
	def oa2ir_op(apiv: str, path: str, method: str, op: OAOp):
		object_name, name = op.operationId.split("_")
		body_types = [IRTransformer.paramOA2IR(p) for p in op.body_params]
		body_type = IRTransformer.unify_ir_t(body_types)
		body_name = None if len(op.body_params) != 1 else op.body_params[0].name  # there can only be one body parameter by the spec # TODO: assert
		params = {p.name: IRTransformer.paramOA2IR(p) for p in op.url_params}
		rets_ts = [IRTransformer.transform_oa_field(r.oa_schema) for r_name, r in (op.responses.items()) if r_name != "default"]
		ret_t = IRTransformer.unify_ir_t(rets_ts)
		ir_op = IROp(
			object_name=object_name,
			name=name,
			description=op.description,
			path=path,
			method=method,
			apiv=apiv,
			body=body_type,
			body_name=body_name,
			params=params or None,
			ret_t=ret_t,
		)
		return ir_op

	def resolve_parameters_in_oapath(self, parsed: Dict[str, OAPath]) -> Dict[str, OAPath]:
		"""Resolve params of OAOps (methods) of an OAPath"""
		resolved: Dict[str, OAPath] = {}
		for path, path_item in parsed.items():
			new_path_item = {}
			for method, op in path_item.items():
				op = cast(OAOp, op)
				resolved_parameters = self.resolve_oaparam_refs(op)
				new_op = op.model_copy(update={"parameters": resolved_parameters})

				new_path_item[method] = new_op
			resolved[path] = cast(OAPath, new_path_item)
		return resolved

	@staticmethod
	def ir2az_op(name: str, op: IROp):
		if op.params:
			az_params = {k: IRTransformer.resolve_ir_t_str(v) for k, v in op.params.items()}
		else:
			az_params = {}
		if op.body or op.body_name:
			assert op.body and op.body_name, f"Need to provide both body and body_name {name=} {op.name=} {op.body=} {op.body_name=}"  # TODO: solidify this requirement
			body = AZOp.Body(name=op.body_name, type=IRTransformer.resolve_ir_t_str(op.body))
		else:
			body = None
		az_op = AZOp(
			ops_name=name,
			name=op.name,
			description=op.description,
			path=op.path,
			method=op.method,
			apiv=op.apiv,
			body=body,
			params=az_params,
			ret_t=IRTransformer.resolve_ir_t_str(op.ret_t),
		)
		return az_op

	def resolve_oaparam_refs(self, op: OAOp) -> List[OAParam]:
		"""Resolve OpenAPI parameters which are references to the definition that they reference"""
		params = op.parameters
		resolved_parameters = []
		for param in params:
			if isinstance(param, OAParam):
				resolved_parameters.append(param)
			else:
				resolved_parameters.append(OAParam(**(self.openapi.load_relative(param.ref))))
		return resolved_parameters


class CodeGenable(ABC):
	"""All objects which can be generated into Python code"""

	@abstractmethod
	def codegen(self) -> str:
		"""Dump this object to Python code"""

	@staticmethod
	def quote(s: str) -> str:
		"""Normal quotes"""
		return '"%s"' % s

	@staticmethod
	def fstring(s: str) -> str:
		"""An f-string"""
		return 'f"%s"' % s

	@staticmethod
	def indent(i: int, s: str) -> str:
		"""Indent this block
		:param i: number of indents
		:param s: content
		:return:
		"""
		return indent(s, "\t" * i)


class AZField(BaseModel, CodeGenable):
	"""An Azure field"""

	name: str
	t: str
	default: Optional[str] = None
	readonly: bool

	def codegen(self) -> str:
		if self.name == "id":
			return f'rid: {self.t} = Field(alias="id", default=None)'
		default = f" = {self.default}" if self.default else ""
		return f"{self.name}: {self.t}" + default


class AZDef(BaseModel, CodeGenable):
	"""An Azure Definition"""

	name: str
	description: Optional[str]
	fields: List[AZField]
	property_c: Optional[AZDef] = None

	def codegen(self) -> str:
		if self.property_c:
			property_c_codegen = indent(self.property_c.codegen(), "\t")
		else:
			property_c_codegen = ""

		fields = indent("\n".join(field.codegen() for field in self.fields), "\t")

		return dedent(
			'''\
		class {name}(BaseModel):
			"""{description}"""
		{property_c_codegen}
		{fields}

		{eq}
		'''
		).format(name=self.name, description=self.description, property_c_codegen=property_c_codegen, fields=fields, eq=self.codegen_eq())

	def codegen_eq(self) -> str:
		"""Codegen the `__eq__` method. This is necessary for omitting all the readonly information, which is usually useless for operations like `identity`"""
		conditions = ["isinstance(o, self.__class__)"]
		for field in self.fields:
			if not field.readonly:
				conditions.append(f"self.{field.name} == o.{field.name}")

		conditions_str = self.indent(2, "\nand ".join(conditions))

		return self.indent(
			1,
			dedent(
				"""\
		def __eq__(self, o) -> bool:
			return (
		{conditions_str}
			)
		"""
			).format(conditions_str=conditions_str),
		)


class AZAlias(BaseModel, CodeGenable):
	"""An alias to another AZ object. Useful for having the synthetic FooListResult derefence to `List[Foo]`"""

	name: str
	alias: str

	def codegen(self) -> str:
		return f"{self.name} = {self.alias}"


class AZOp(BaseModel, CodeGenable):
	"""An OpenAPI operation ready for codegen"""

	class Body(BaseModel):
		type: str
		name: str

	ops_name: str
	name: str
	description: Optional[str] = None
	path: str
	method: str
	apiv: Optional[str]
	body: Optional[Body] = None
	params: Dict[str, str] = {}
	ret_t: Optional[str]

	def codegen(self) -> str:
		params = []  # TODO: add from path
		req_args = {
			"name": self.quote(self.ops_name + "." + self.name),
			"path": self.fstring(self.path),
		}
		if self.apiv:
			req_args["apiv"] = self.quote(self.apiv)
		if self.params:
			params.extend([f"{p_name}: {p_type}" for p_name, p_type in self.params.items()])
		if self.body:
			params.append(f"{self.body.name}: {self.body.type}")
			req_args["body"] = self.body.name
		if self.ret_t:
			req_args["ret_t"] = self.ret_t

		return dedent(
			'''\
		@staticmethod
		def {name}({params}) -> Req[{ret_t}]:
			"""{description}"""
			return Req.{method}(
		{req_args}
			)
		'''
		).format(
			name=self.name,
			params=", ".join(params),
			description=self.description,
			ret_t=self.ret_t,
			method=self.method,
			req_args=indent(",\n".join("=".join([k, v]) for k, v in req_args.items()), "\t\t"),
		)


class AZOps(BaseModel, CodeGenable):
	"""All the OpenAPI methods of one area covered by and OpenAPI file"""

	name: str
	apiv: str
	ops: List[AZOp]

	def codegen(self) -> str:
		op_strs = indent("\n".join(op.codegen() for op in self.ops), "\t")

		return dedent(
			"""\
		class Az{name}:
			apiv = {apiv}
		{ops}
		"""
		).format(name=self.name, ops=op_strs, apiv=self.quote(self.apiv))


def main(openapi_root, openapi_file, output_file):
	reader = Reader.load(openapi_root, Path(openapi_file))

	parser = TypeAdapter(Dict[str, OADef])
	oa_defs = parser.validate_python(reader.definitions)

	transformer = IRTransformer(oa_defs, reader)

	with open(output_file, mode="w", encoding="utf-8") as f:
		f.write(
			dedent(
				"""\
				# pylint: disable
				# flake8: noqa
				from __future__ import annotations
				from typing import List, Optional, Union

				from pydantic import BaseModel, Field

				from llamazure.azrest.models import AzList, ReadOnly, Req
				"""
			)
		)
		f.write(transformer.transform_definitions())
		f.write(transformer.transform_paths(reader.paths, reader.apiv))


if __name__ == "__main__":
	import sys

	main(*sys.argv[1:])
