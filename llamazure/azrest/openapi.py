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
from collections import defaultdict
from pathlib import Path
from textwrap import dedent, indent
from typing import Dict, List, Literal, Optional, Type, Union

from pydantic import BaseModel, Field, TypeAdapter
from typing_extensions import NotRequired, TypedDict

from llamazure.azrest.models import AzList

logger = logging.getLogger(__name__)


class PathLookupError(Exception):
	def __init__(self, object_path: str):
		self.object_path = object_path
		super().__init__(f"Error while looking up path: {object_path}")


class OARef(BaseModel):
	ref: str = Field(alias="$ref")
	description: Optional[str] = None

	@property
	def name(self) -> str:
		return self.ref.split('/')[-1]


class OADef(BaseModel):
	class Array(BaseModel):
		t: Literal["array"] = Field(alias="type", default="array")
		items: Union[OADef.Property, OARef]
		description: Optional[str] = None

	class Property(BaseModel):
		t: Union[str] = Field(alias="type")
		description: Optional[str] = None
		readOnly: bool = False

	properties: Dict[str, Union[OADef.Array, OADef.Property, OARef]]
	t: str = Field(alias="type")
	description: Optional[str] = None


class OAParam(BaseModel):
	name: str
	in_component: str = Field(alias="in")
	required: bool = True
	type: Optional[str] = None
	description: str
	oa_schema: Optional[OARef] = Field(alias="schema", default=None)


class OAResponse(BaseModel):
	description: str
	oa_schema: Optional[OARef] = Field(alias="schema", default=None)


class OAMSPageable(BaseModel):
	nextLinkName: str


class OAOp(BaseModel):
	tags: List[str]
	operationId: str
	description: str
	parameters: List[Union[OAParam, OARef]]
	responses: Dict[str, OAResponse]
	pageable: Optional[OAMSPageable] = Field(alias="x-ms-pageable", default=None)

	@property
	def body_params(self) -> List[OAParam]:
		# TODO: resolve refs
		return [p for p in self.parameters if isinstance(p, OAParam) and p.in_component == "body"]

	@property
	def url_params(self) -> List[OAParam]:
		# TODO: resolve refs
		return [p for p in self.parameters if isinstance(p, OAParam) and p.in_component == "path"]


class OAPath(TypedDict):
	get: NotRequired[OAOp]
	put: NotRequired[OAOp]
	post: NotRequired[OAOp]
	delete: NotRequired[OAOp]
	options: NotRequired[OAOp]
	head: NotRequired[OAOp]
	patch: NotRequired[OAOp]


class IROp(BaseModel):
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
	name: str
	properties: Dict[str, IR_T]
	description: Optional[str] = None


class IR_T(BaseModel):
	t: Union[Type, IRDef, IR_List, str]  # TODO: upconvert str
	readonly: bool = False


class IR_List(BaseModel):
	items: IR_T


class Reader:
	"""Read Microsoft OpenAPI specifications"""

	def __init__(self, root: Path, path: Path, openapi: dict):
		self.root = root
		self.path = path
		self.doc = openapi

	@classmethod
	def load(cls, root: Path, path: Path) -> Reader:
		"""Load from a path or file-like object"""

		openapi3_file = root / path
		with open(openapi3_file, mode="r", encoding="utf-8") as fp:
			return Reader(root, path, json.load(fp))

	@property
	def paths(self):
		"""Get API paths (standard and ms xtended)"""
		return dict(itertools.chain(self.doc["paths"].items(), self.doc.get("x-ms-paths", {}).items()))

	@property
	def definitions(self):
		return self.doc["definitions"]

	@property
	def apiv(self) -> str:
		return self.doc["info"]["version"]

	@staticmethod
	def classify_relative(relative: str) -> tuple[str, str, str]:
		file_path, object_path = relative.split("#")
		oa_type = object_path.split('/')[0]
		return file_path, oa_type, object_path

	def load_relative(self, relative: str) -> dict:
		file_path, _, object_path = self.classify_relative(relative)

		if file_path:
			file = self._load_file(file_path)
		else:
			file = self.doc

		o = self._get_from_object_at_path(file, object_path)
		return o

	@staticmethod
	def _get_from_object_at_path(file: dict, object_path: str) -> dict:
		try:
			o = file
			for segment in object_path.split("/"):
				if segment:  # escape empty segments
					o = o[segment]
			return o
		except (KeyError, TypeError):
			# Raise a custom exception with a helpful message including the object_path
			raise PathLookupError(object_path)

	def _load_file(self, file_path):
		with (self.root / self.path.parent / file_path).open(mode="r", encoding="utf-8") as fp:
			file = json.load(fp)
		return file


def operations(path_object: dict):
	"""Extract operations from an OpenAPI Path object"""
	return {k: v for k, v in path_object.items() if k in {"get", "put", "post", "delete", "options", "head", "patch", "trace"}}


def definitions(ds: dict):
	"""Extract OpenAPI definitions"""
	parser = TypeAdapter(Dict[str, OADef])
	return parser.validate_python(ds)


def resolve_path(path: str) -> str:
	if path.startswith("#/definitions/"):
		return path[len("#/definitions/") :]
	return path


def dereference_refs(ds: Dict[str, OADef]) -> Dict[str, OADef]:
	"""Inflate refs to their objects"""
	out = {}
	for name, obj in ds.items():
		new_props: Dict[str, Union[OADef.Array, OADef.Property, OARef]] = {}
		for prop_name, prop in obj.properties.items():
			if isinstance(prop, OARef):
				ref_target = resolve_path(prop.ref)
				ref = ds[ref_target]
				new_props[prop_name] = OADef.Property(type=ref, description=prop.description)
			else:
				new_props[prop_name] = prop
		obj.properties = new_props
		out[name] = obj

	return out


class IRTransformer:
	def __init__(self, defs: Dict[str, OADef], openapi: Reader):
		self.oa_defs: Dict[str, OADef] = defs
		self.openapi = openapi

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

		codegened_definitions = [cg.codegen() for cg in output_req]
		reloaded_definitions = [f"{az_definition.name}.model_rebuild()" for az_definition in azs] + [f"{az_list.name}.model_rebuild()" for az_list in ir_azlists.values()]
		return "\n\n".join(codegened_definitions + reloaded_definitions)

	def transform_def(self, name: str, obj: OADef) -> IRDef:
		ir_properties = {p_name: self.transform_oa_field(p) for p_name, p in obj.properties.items()}
		return IRDef(
			name=name,
			properties=ir_properties,
			description=obj.description,
		)

	def _resolve_path(self, ref: OARef):
		obj = self.openapi.load_relative(ref.ref)
		return obj

	def transform_oa_field(self, p: Union[OADef.Array, OADef.Property, OARef]) -> IR_T:
		if isinstance(p, OADef.Property):
			resolved_type = self.resolve_type(p.t)
			return IR_T(t=resolved_type, readonly=p.readOnly)
		elif isinstance(p, OADef.Array):
			return self.ir_array(p)
		elif isinstance(p, OARef):
			return IR_T(t=resolve_path(p.ref))

	def resolve_type(self, t) -> IR_T:
		py_type = {
			"string": str,
			"number": float,
			"integer": int,
			"boolean": bool,
		}.get(t, t)
		return py_type

	def ir_array(self, obj: OADef.Array) -> IR_T:
		if isinstance(obj.items, OADef.Property):
			# Probably a type
			as_list = IR_List(items=IR_T(t=self.resolve_type(obj.items.t)))
		elif isinstance(obj.items, OARef):
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
			n = t.__name__
		elif isinstance(t, IRDef):
			n = t.name
		elif isinstance(t, IR_List):
			n = f"List[%s]" % IRTransformer.resolve_ir_t_str(t.items)
		elif isinstance(t, str):
			n = t
		else:
			raise TypeError(f"Cannot handle {type(t)}")

		if ir_t.readonly:
			return f"ReadOnly[%s]" % n
		else:
			return n

	@staticmethod
	def fieldsIR2AZ(fields: Dict[str, IR_T]) -> List[AZField]:
		az_fields = []

		for f_name, f_type in fields.items():
			if f_name == "properties":
				# assert isinstance(f_type, IRDef)
				v = "Properties"
			else:
				v = IRTransformer.resolve_ir_t_str(f_type)

			if f_type.readonly:
				default = "None"
			else:
				default = None

			az_fields.append(AZField(name=f_name, t=v, default=default))

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

	def paramOA2IR(self, oaparam: OAParam) -> IR_T:
		if oaparam.oa_schema:
			return self.transform_oa_field(oaparam.oa_schema)
		else:
			return IR_T(t=self.resolve_type(oaparam.type))

	def unify_ir_t(self, ts: List[IR_T]) -> Optional[IR_T]:
		ts = list(filter(None, ts))
		if len(ts) == 0:
			return None
		elif len(ts) == 1:
			return ts[0]
		else:
			return IR_T(t=f"Union[{', '.join(self.resolve_ir_t_str(t) for t in ts)}]")

	def deserialise_paths(self, paths, apiv: str) -> str:
		parser = TypeAdapter(Dict[str, OAPath])
		parsed = parser.validate_python(paths)

		resolved: Dict[str, OAPath] = {}
		for path, path_item in parsed.items():
			new_path_item = {}
			for method, op in path_item.items():
				resolved_parameters = self.resolve_oaparam_refs(op)
				new_op = op.model_copy(update={"parameters": resolved_parameters})

				new_path_item[method] = new_op
			resolved[path] = new_path_item


		ops: List[IROp] = []
		for path, path_item in resolved.items():
			for method, op in path_item.items():
				object_name, name = op.operationId.split("_")

				body_types = [self.paramOA2IR(p) for p in op.body_params]
				body_type = self.unify_ir_t(body_types)
				body_name = "body" if len(op.body_params) != 1 else op.body_params[0].name

				params = {p.name: self.paramOA2IR(p) for p in op.url_params}

				rets = op.responses.items()
				rets_ts = [self.transform_oa_field(r[1].oa_schema) for r in rets if r[0] != "default"]
				ret_t = self.unify_ir_t(rets_ts)

				ops.append(
					IROp(
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
				)

		az_objs: Dict[str, List[IROp]] = defaultdict(list)
		for ir_op in ops:
			az_objs[ir_op.object_name].append(ir_op)

		az_ops = []
		for name, ir_ops in az_objs.items():
			o = []
			for x in ir_ops:
				if x.params:
					params = {k: self.resolve_ir_t_str(v) for k, v in x.params.items()}
				else:
					params = None

				if x.body:
					body = self.resolve_ir_t_str(x.body)
					body_name = x.body_name
				else:
					body = None
					body_name = None

				az_op = AZOp(
					name=x.name,
					description=x.description,
					path=x.path,
					method=x.method,
					apiv=x.apiv,
					body=body,
					body_name=body_name,
					params=params,
					ret_t=self.resolve_ir_t_str(x.ret_t),
				)
				o.append(az_op)

			a = AZOps(name=name, ops=o, apiv=apiv)

			az_ops.append(a)

		return "\n\n".join([cg.codegen() for cg in az_ops])

	def resolve_oaparam_refs(self, op: OAOp) -> List[OAParam]:
		params = op.parameters
		resolved_parameters = []
		for param in params:
			if isinstance(param, OAParam):
				resolved_parameters.append(param)
			else:
				resolved_parameters.append(OAParam(**(self.openapi.load_relative(param.ref))))
		return resolved_parameters


class CodeGenable(ABC):
	@abstractmethod
	def codegen(self) -> str:
		...

	@staticmethod
	def quote(s: str) -> str:
		return '"%s"' % s

	@staticmethod
	def fstring(s: str) -> str:
		return 'f"%s"' % s


class AZField(BaseModel, CodeGenable):
	name: str
	t: str
	default: Optional[str] = None

	def codegen(self) -> str:
		if self.name == "id":
			return f'rid: {self.t} = Field(alias="id", default=None)'
		default = f" = {self.default}" if self.default else ""
		return f"{self.name}: {self.t}" + default


class AZDef(BaseModel, CodeGenable):
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
		'''
		).format(name=self.name, description=self.description, property_c_codegen=property_c_codegen, fields=fields)


class AZAlias(BaseModel, CodeGenable):
	name: str
	alias: str

	def codegen(self) -> str:
		return f"{self.name} = {self.alias}"


class AZOp(BaseModel, CodeGenable):
	name: str
	description: Optional[str] = None
	path: str
	method: str
	apiv: Optional[str]
	body: Optional[str]
	body_name: Optional[str] = None
	params: Optional[Dict[str, str]]
	ret_t: Optional[str]

	def codegen(self) -> str:
		params = []  # TODO: add from path
		req_args = {
			"path": self.fstring(self.path),
		}
		if self.apiv:
			req_args["apiv"] = self.quote(self.apiv)
		if self.params:
			params.extend([f"{p_name}: {p_type}" for p_name, p_type in self.params.items()])
		if self.body:
			params.append(f"{self.body_name}: {self.body}")
			req_args["body"] = self.body_name
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


if __name__ == "__main__":
	import sys

	reader = Reader.load(Path(sys.argv[1]), Path(sys.argv[2]))

	oa_defs = definitions(reader.definitions)

	transformer = IRTransformer(oa_defs, reader)

	print(
		dedent(
			"""\
			from __future__ import annotations
			from typing import List, Union
			
			from pydantic import BaseModel, Field
			
			from llamazure.azrest.models import AzList, ReadOnly, Req
			"""
		)
	)
	print(transformer.transform())
	print(transformer.deserialise_paths(reader.paths, reader.apiv))
