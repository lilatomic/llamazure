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
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from functools import cached_property
from json import JSONDecodeError
from pathlib import Path
from textwrap import dedent, indent
from typing import ClassVar, Dict, Iterable, List, Literal, Optional, Sequence, Set, Tuple, Type, Union, cast

import pydantic
import requests
from pydantic import BaseModel, Field, TypeAdapter

from llamazure.azrest.models import AzList

l = logging.getLogger(__name__)


def mk_typename(typename: str) -> str:
	return typename[0].capitalize() + typename[1:]


class PathLookupError(Exception):
	"""Could not look up an OpenAPI reference"""

	def __init__(self, object_path: str, segment: str):
		self.object_path = object_path
		super().__init__(f"Error while looking up path={object_path} segment={segment}")


class LoadError(Exception):  # cov: err
	def __init__(self, path, obj):
		self.path = path
		self.obj = obj
		super().__init__(f"Error deserialising {path=}")


class OARef(BaseModel):
	"""An OpenAPI reference"""

	ref: str = Field(alias="$ref")
	description: Optional[str] = None

	class Config:
		populate_by_name = True


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
		items: Optional[Dict[str, str]] = None

	properties: Dict[str, Union[OADef.Array, OARef, OADef, OADef.Property]] = {}
	t: Optional[str] = Field(alias="type", default=None)
	description: Optional[str] = None

	allOf: Optional[List[OAObj]] = None
	# anyOf: Optional[Dict[str, OADef.JSONSchemaProperty]] = None
	additionalProperties: Optional[Union[OADef.Array, OADef.Property, OARef, OADef, bool]] = False
	required: Optional[List[str]] = None


class OAEnum(BaseModel):
	t: Union[str] = Field(alias="type")
	description: Optional[str] = None
	enum: List[str]
	x_ms_enum: Optional[XMSEnum] = Field(alias="x-ms-enum")

	class XMSEnum(BaseModel):
		name: str
		modelAsString: bool
		# TOOD: rest of x-ms-enum?


class ParamPosition(Enum):
	body = "body"
	path = "path"
	query = "query"


class OAParam(BaseModel):
	"""A Param for an OpenAPI Operation"""

	name: str
	in_component: ParamPosition = Field(alias="in")
	required: bool = True
	type: Optional[str] = None
	description: str
	oa_schema: Optional[OARef] = Field(alias="schema", default=None)
	items: Optional[Union[OADef.Array, OADef.Property, OARef]] = None


class OAResponse(BaseModel):
	"""A response for an OpenAPI Operation"""

	description: str
	oa_schema: Optional[Union[OARef, OADef.Array, OADef]] = Field(alias="schema", default=None)


class OAMSPageable(BaseModel):
	"""MS Pageable extension"""

	nextLinkName: str


class OAOp(BaseModel):
	"""An OpenAPI Operation"""

	tags: List[str] = []
	operationId: str
	description: str
	parameters: List[Union[OAParam, OARef]]
	responses: Dict[str, Union[OARef, OAResponse]]
	pageable: Optional[OAMSPageable] = Field(alias="x-ms-pageable", default=None)


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


class IRParam(BaseModel):
	"""Bundle for an operation's parameters"""

	t: IR_T
	name: str
	position: ParamPosition


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
	query_params: Optional[Dict[str, IR_T]]
	ret_t: Optional[IR_T] = None


class IRDef(BaseModel):
	"""An IR Definition"""

	name: str
	properties: Dict[str, IR_T]
	description: Optional[str] = None
	src: Optional[Path] = None


class IR_T(BaseModel):
	"""An IR Type descriptor"""

	t: Union[Type, IR_Union, IRDef, IR_List, IR_Dict, IR_Enum, str]  # TODO: upconvert str
	readonly: bool = False
	required: bool = True


class IR_Union(BaseModel):
	"""An IR descriptor for a Union of types"""

	items: List[IR_T]


class IR_List(BaseModel):
	"""An IR descriptor for a List type"""

	items: IR_T
	required: bool = True


class IR_Dict(BaseModel):
	"""An IR descriptor for a Dictionary type"""

	keys: IR_T
	values: IR_T
	required: bool = True


class IR_Enum(BaseModel):
	"""An IR descriptor for an Enum"""

	name: str
	values: List[str]
	description: Optional[str] = None


@dataclass
class Reader:
	"""Read Microsoft OpenAPI specifications"""

	def __init__(self, root: str, path: Path, openapi: dict, reader_cache: Dict[Path, Reader]):
		self.root = root
		self.path = path
		self.doc = openapi
		self.reader_cache = reader_cache

		self.reader_cache[path] = self

	@classmethod
	def load(cls, root: str, path: Path, reader_cache: Optional[Dict[Path, Reader]] = None) -> Reader:
		"""Load from a path or file-like object"""
		return cls._load_file(root, path, reader_cache or {})

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
	def classify_relative(relative: str) -> tuple[Optional[Path], str, str]:
		"""Decompose an OpenAPI reference into its filepath, item type, and path inside that document"""
		file_path, object_path = relative.split("#")
		oa_type = object_path.split("/")[1]
		return Path(file_path) if file_path else None, oa_type, object_path

	@staticmethod
	def resolve_path(path: Path) -> Path:
		parts: List[str] = []
		for part in path.parts:
			if part == "..":
				if parts:
					parts.pop()
			elif part != ".":
				parts.append(part)
		return Path(*parts)

	def load_relative(self, relative: str) -> Tuple[Reader, dict]:
		"""Load an object from a relative path"""
		file_path, _, object_path = self.classify_relative(relative)

		if file_path:
			tgt = self.resolve_path(self.path.parent / file_path)
			if tgt in self.reader_cache:
				reader = self.reader_cache[tgt]
			else:
				reader = self._load_file(self.root, tgt, self.reader_cache)
				self.reader_cache[tgt] = reader
		else:
			reader = self

		file = reader.doc
		return reader, self._get_from_object_at_path(file, object_path)

	@staticmethod
	def _get_from_object_at_path(file: dict, object_path: str) -> dict:
		"""Load an object from a path in a different file"""
		try:
			o = file
			for segment in object_path.split("/"):
				if segment:  # escape empty segments
					o = o[segment]
			return o
		except KeyError as e:
			# Raise a custom exception with a helpful message including the object_path
			raise PathLookupError(object_path, e.args[0])
		except TypeError:
			raise PathLookupError(object_path, "???")

	@staticmethod
	def extract_remote_object_name(object_path: str) -> str:
		"""Extract the name of a remote object. Useful for registering class references while instantiating."""
		return object_path.split("/")[-1]

	@staticmethod
	def _load_file(root: str, file_path: Path, reader_cache: Dict[Path, Reader]) -> Reader:
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
		try:
			loaded = json.loads(content)
		except JSONDecodeError as e:
			raise RuntimeError(f"Error loading path={file_path}") from e

		return Reader(root, file_path, loaded, reader_cache)


class RefCache:
	ref_initialising = object()

	@dataclass(frozen=True)
	class Ref:
		path: Path
		ref: str

	def __init__(self):
		self.cache = {}

	def __getitem__(self, ref: Ref):
		if ref in self.cache:
			value = self.cache[ref]
			if value is not RefCache.ref_initialising:
				return value
			else:
				return None

	def mark_initialising(self, ref: Ref):
		"""Mark that we've started initialising this reference, so we know if we're in a recursive loop."""
		self.cache[ref] = RefCache.ref_initialising

	def mark_referenceable(self, ref: Ref, value: IR_T):
		"""
		Mark that we have enough information to provide a reference to this class,
		even if we haven't fully resolved it.

		For example, we can provide a class name even if we don't know all of its members
		"""
		self.cache[ref] = value

	def __setitem__(self, ref: Ref, value):
		self.cache[ref] = value


class IRTransformer:
	"""Transformer to and from the IR"""

	def __init__(self, defs: Dict[str, Union[OADef, OAEnum]], paths: Dict[str, OAPath], openapi: Reader, refcache: RefCache):
		self.oa_defs: Dict[str, Union[OADef, OAEnum]] = defs
		self.oa_paths: Dict[str, OAPath] = paths
		self.openapi = openapi

		self.jsonparser = JSONSchemaSubparser(openapi, refcache)

	@cached_property
	def normalised_oadef_names(self) -> set[str]:
		"""OAdef names that have been normalised. Some have improper capitalisation, like `systemData`"""
		return {mk_typename(e) for e in self.oa_defs.keys()}

	@classmethod
	def from_reader(cls, reader: Reader) -> IRTransformer:
		parser_def = TypeAdapter(Dict[str, Union[OAEnum, OADef]])
		parser_paths = TypeAdapter(Dict[str, OAPath])
		try:
			oa_defs = parser_def.validate_python(reader.definitions)
			oa_paths = parser_paths.validate_python(reader.paths)
			return IRTransformer(oa_defs, oa_paths, reader, RefCache())
		except pydantic.ValidationError as e:  # cov: err
			print(e.errors())
			raise LoadError(reader.path, reader.definitions) from e

	def _find_ir_definitions(self) -> Tuple[Dict[str, IRDef], Dict[str, IR_Enum]]:
		ir_definitions = {}
		ir_enums = {}
		for name, obj in self.oa_defs.items():
			parsed = self.jsonparser.transform(name, obj, [])
			if isinstance(parsed.t, IRDef):
				ir_definitions[parsed.t.name] = parsed.t
			elif isinstance(parsed.t, IR_Dict):
				continue  # we don't need to define dicts
			elif isinstance(parsed.t, IR_Enum):
				ir_enums[parsed.t.name] = parsed.t
			elif isinstance(obj, OAEnum) and obj.x_ms_enum and obj.x_ms_enum.modelAsString:
				# modelAsString means no validation is done. We model that as a string, and isn't an IR_Enum here
				continue
			else:  # cov: err
				raise ValueError(f"Type resolved to non-definition {parsed.t}")
		return ir_definitions, ir_enums

	def transform_definitions(self) -> str:
		"""Transform the OpenAPI objects into their codegened str"""
		ir_definitions, ir_enums = self._find_ir_definitions()
		az_lists = self.identify_azlists(ir_definitions)
		az_enums = [AZEnum(name=e.name, values=e.values, description=e.description) for e in ir_enums.values()]

		azs = self.identify_definitions(az_lists, ir_definitions)

		output_req: List[CodeGenable] = azs + list(az_lists.values()) + list(az_enums)

		return self.codegen_definitions(azs, az_lists, output_req)

	def identify_azlists(self, ir_definitions) -> Dict[str, AZAlias]:
		ir_azlists: Dict[str, AZAlias] = {}
		for name, ir in ir_definitions.items():
			azlist = self.ir_azarray(ir)
			if azlist:
				ir_azlists[name] = azlist
		return ir_azlists

	def identify_definitions(self, ir_azlists, ir_definitions):
		ir_consumed = set(ir_azlists.keys())
		r = [self.defIR2AZ(ir) for ir in ir_definitions.values()]
		azs = [e.result for e in r]
		ir_consumed.update([c.name for e in r for c in e.consumed])
		out = []
		for az_class in azs:
			if az_class.name in ir_consumed:
				continue
			if az_class.name.endswith("Properties"):
				continue  # TODO: better way of consuming this. Currently the problem is that the actual consumed class uses its final name, which is just "Properties"
			out.append(az_class)
		return out

	@staticmethod
	def codegen_definitions(azs: List[AZDef], ir_azlists: Dict[str, AZAlias], output_req: List[CodeGenable]):
		codegened_definitions = [cg.codegen() for cg in output_req]
		reloaded_definitions = [f"{az_definition.name}.model_rebuild()" for az_definition in azs] + [f"{az_list.name}.model_rebuild()" for az_list in ir_azlists.values()]
		return "\n\n".join(codegened_definitions + reloaded_definitions) + "\n\n"

	@staticmethod
	def ir_azarray(obj: Union[IRDef, IR_Enum]) -> Optional[AZAlias]:
		"""Transform a definition representing an array into an alias to the wrapped type"""
		if isinstance(obj, IR_Enum):
			return None

		value = obj.properties.get("value", None)
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
		elif isinstance(declared_type, IR_Union):
			type_as_str = f"Union[{', '.join(IRTransformer.resolve_ir_t_str(e) for e in declared_type.items)}]"
		elif isinstance(declared_type, IRDef):
			type_as_str = declared_type.name
		elif isinstance(declared_type, IR_Enum):
			type_as_str = declared_type.name
		elif isinstance(declared_type, IR_List):
			type_as_str = "List[%s]" % IRTransformer.resolve_ir_t_str(declared_type.items)
		elif isinstance(declared_type, IR_Dict):
			type_as_str = "Dict[%s, %s]" % (IRTransformer.resolve_ir_t_str(declared_type.keys), IRTransformer.resolve_ir_t_str(declared_type.values))
		elif isinstance(declared_type, str):
			type_as_str = mk_typename(declared_type)
		else:  # cov: err
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
			elif isinstance(f_type.t, IR_Dict):
				v = "{}"
			elif f_name == "properties":
				v = None
			elif f_type.readonly or not f_type.required:
				v = "None"
			else:
				v = None

			annotations = []
			if isinstance(f_type.t, IR_List):
				annotations.append("default_list")
			elif isinstance(f_type.t, IR_Dict):
				annotations.append("default_dict")

			az_fields.append(AZField(name=f_name, t=t, default=v, annotations=annotations, readonly=f_type.readonly))

		return az_fields

	@dataclass
	class IR2AZResult:
		result: AZDef
		consumed: List[IRDef]

	def defIR2AZ(self, irdef: IRDef) -> IR2AZResult:
		"""Convert IR Defs to AZ Defs"""

		property_c = []
		consumed = []
		for name, prop in irdef.properties.items():
			if name == "properties":
				prop_container = irdef.properties["properties"]
				prop_c_ir = prop_container.t
				assert isinstance(prop_c_ir, IRDef), f"properties class was not of type IRDef type={type(prop_c_ir)}"
				prop_c_az = self.defIR2AZ(prop_c_ir)

				property_c.append(prop_c_az.result.model_copy(update={"name": "Properties"}))
				consumed.append(prop_c_ir)
				consumed.extend(prop_c_az.consumed)

			elif isinstance(prop.t, IRDef):
				# if it's a top-level class we want to reference it
				if mk_typename(prop.t.name) in self.normalised_oadef_names:
					continue

				# do not embed imported classes
				if prop.t.src != irdef.src:
					continue

				prop_c_az = self.defIR2AZ(prop.t)
				property_c.append(prop_c_az.result.model_copy(update={"name": mk_typename(name)}))
				consumed.append(prop.t)
				consumed.extend(prop_c_az.consumed)

		return self.IR2AZResult(
			AZDef(name=irdef.name, description=irdef.description, fields=IRTransformer.fieldsIR2AZ(irdef.properties), subclasses=property_c),
			consumed,
		)

	@staticmethod
	def unify_ir_t(ir_ts: List[IR_T]) -> Optional[IR_T]:
		"""Unify IR types, usually for returns"""
		ts = {IRTransformer.resolve_ir_t_str(t): t for t in ir_ts if t}

		is_required = "None" not in ts  # TODO: doesn't handle generic types like IR_Union
		ts.pop("None", None)

		if len(ts) == 0:
			return None
		elif len(ts) == 1:
			[single] = ts.values()
			if isinstance(single, IR_T):
				return IR_T(t=single.t, required=is_required)
			else:
				return IR_T(t=single, required=is_required)
		else:
			return IR_T(t=IR_Union(items=list(ts.values())), required=is_required)

	def _find_ir_ops(self) -> List[IROp]:
		ops: List[IROp] = []
		for path, path_item in self.oa_paths.items():
			for method, op in path_item.items():
				ops.append(self.jsonparser.ip_op(self.openapi.apiv, path, method, op))
		return ops

	def transform_paths(self) -> str:
		"""Transform OpenAPI Paths into the Python code for the Azure objects"""
		ops = self._find_ir_ops()

		az_objs: Dict[str, List[IROp]] = defaultdict(list)
		for ir_op in ops:
			az_objs[ir_op.object_name].append(ir_op)

		az_ops = []
		for name, ir_ops in az_objs.items():
			az_ops.append(
				AZOps(
					name=name,
					ops=[self.ir2az_op(name, x) for x in ir_ops],
					apiv=self.openapi.apiv,
				)
			)

		return "\n\n".join([cg.codegen() for cg in az_ops])

	@staticmethod
	def ir2az_op(name: str, op: IROp):
		if op.params:
			az_params = {k: IRTransformer.resolve_ir_t_str(v) for k, v in op.params.items()}
		else:
			az_params = {}

		if op.query_params:
			query_params = [AZOp.Param(name=p_name, type=IRTransformer.resolve_ir_t_str(p), required=p.required) for p_name, p in op.query_params.items()]
		else:
			query_params = []
		query_params.sort(key=lambda x: x.required, reverse=True)

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
			query_params=query_params,
			ret_t=IRTransformer.resolve_ir_t_str(op.ret_t),
		)
		return az_op

	def transform_imports(self, base_module_path: Path) -> str:
		definitions, _ = self._find_ir_definitions()
		merged = AZImport.merge(
			(
				*(self._extract_imports(definitions.values())),
				*(self._extract_imports(self._find_ir_ops())),
			)
		)

		def resolve_path(e: AZImport):
			e.path = base_module_path / path2module(e.path)
			return e

		resolved = [resolve_path(e) for e in merged]
		return "\n".join([cg.codegen() for cg in resolved])

	def _extract_imports(self, definitions: Iterable[Union[IRDef, IROp]]) -> List[AZImport]:
		imports = []
		for ir in definitions:
			imports.extend(self._remove_local_imports(self.openapi.path, self._find_imports(ir, parent_src=self.openapi.path)))
		return imports

	def _find_imports(self, ir: Union[IRDef, IROp, IR_T, IR_Union, IR_Enum, IR_List, IR_Dict, str, type], parent_src) -> List[AZImport]:
		if isinstance(ir, (str, type)):
			return []
		elif isinstance(ir, IRDef):
			out = []
			if ir.src:
				out.append(AZImport(path=ir.src, names={ir.name}))
			if ir.src == parent_src:
				out.extend(list(itertools.chain.from_iterable([self._find_imports(t, parent_src) for t in ir.properties.values()])))
			return out
		elif isinstance(ir, IR_T):
			return self._find_imports(ir.t, parent_src)
		elif isinstance(ir, IR_Enum):
			return []
		elif isinstance(ir, IR_List):
			return self._find_imports(ir.items, parent_src)
		elif isinstance(ir, IR_Dict):
			return list(itertools.chain.from_iterable([self._find_imports(ir.keys, parent_src), self._find_imports(ir.values, parent_src)]))
		elif isinstance(ir, IR_Union):
			return list(itertools.chain.from_iterable([self._find_imports(v, parent_src) for v in ir.items]))
		elif isinstance(ir, IROp):
			o = []
			if ir.body:
				o.extend(self._find_imports(ir.body, parent_src))
			if ir.params:
				o.extend(itertools.chain.from_iterable(self._find_imports(v, parent_src) for v in ir.params.values()))
			if ir.query_params:
				o.extend(itertools.chain.from_iterable(self._find_imports(v, parent_src) for v in ir.query_params.values()))
			if ir.ret_t:
				o.extend(self._find_imports(ir.ret_t, parent_src))
			return o
		else:  # cov: err
			raise TypeError(f"Cannot find imports for unexpected type {type(ir)}")

	@staticmethod
	def _remove_local_imports(local: Path, imports: List[AZImport]) -> List[AZImport]:
		return [e for e in imports if e.path != local]


OAObj = Union[OARef, OADef.Array, OADef.Property, OADef, OAEnum]


class JSONSchemaSubparser:
	oaparser: ClassVar[TypeAdapter] = TypeAdapter(Union[OARef, OAEnum, OADef])

	def __init__(self, openapi: Reader, refcache: RefCache):
		self.openapi = openapi
		self.refcache = refcache

	@staticmethod
	def resolve_type(t: Optional[str]) -> Union[str, type]:
		"""Resolve OpenAPI types to Python types, if applicable"""
		py_type = {
			"string": str,
			"number": float,
			"integer": int,
			"boolean": bool,
			"object": dict,
			None: "None",
		}.get(t, t)
		return py_type  # type: ignore  # I'm not going to convince mypy of this

	def _is_full_inherit(self, obj: OADef) -> Optional[OARef]:
		if not obj.properties and obj.allOf is not None and len(obj.allOf) == 1 and isinstance(obj.allOf[0], OARef):
			return obj.allOf[0]
		return None

	def _is_dict(self, obj: OADef) -> bool:
		if obj.additionalProperties is True:  # additionalProperties is wide open
			return True

		if not obj.t == "object":  # not an object
			return False

		if obj.properties or obj.allOf:  # has properties
			return False

		if isinstance(obj.additionalProperties, OADef.Property) and not obj.additionalProperties.items:  # additionalProperties has nothing specified
			return True

		return False

	def resolve_reference(self, name, ref: OARef, required_properties: List[str]) -> IR_T:
		relname = self.openapi.extract_remote_object_name(ref.ref)
		cache_ref = RefCache.Ref(self.openapi.path, relname)
		if self.refcache[cache_ref]:
			return self.refcache[cache_ref]
		self.refcache.mark_referenceable(cache_ref, IR_T(t=relname))

		reader, resolved = self.openapi.load_relative(ref.ref)
		relative_transformer = JSONSchemaSubparser(reader, self.refcache)
		resolved_loaded = self.oaparser.validate_python(resolved)

		transformed = relative_transformer.transform(relname, resolved_loaded, required_properties)
		self.refcache[cache_ref] = transformed
		return transformed

	def ir_array(self, name, obj: OADef.Array, required_properties: List[str]) -> IR_T:
		"""Transform an OpenAPI array to IR"""
		item_t = self.transform(name, obj.items, [name])
		item_t.required = True
		return IR_T(t=IR_List(items=item_t), required=True)  # defaults to empty list, so we can mark it as required

	def ir_dict(self, name, obj: OADef, required_properties: List[str]) -> IR_T:
		required = name in required_properties

		if obj.additionalProperties is True:
			# is this explicitly a dict without constraints on values
			has_type = obj.properties.get("type", None)
			if has_type:
				if isinstance(has_type, OARef):
					resolved = self.resolve_reference(name, has_type, required_properties)
					values_t = resolved
				else:
					values_t = IR_T(t=self.resolve_type(has_type.t), required=True)
			else:
				values_t = IR_T(t="Any", required=True)  # Optional[Any] is a little silly
		elif isinstance(obj.additionalProperties, (OARef, OADef.Array, OADef.Property, OADef, OAEnum)):
			values_t = self.transform(name, obj.additionalProperties, [name])
		else:
			raise TypeError(f"dict has unknown additionalProperties type={type(obj.additionalProperties)}")
		return IR_T(t=IR_Dict(keys=IR_T(t=str, required=True), values=values_t), required=required)

	def transform(self, name: str, obj: OAObj, required_properties: Optional[List[str]]) -> IR_T:
		"""When we're in JSONSchema mode, we can only contain more jsonschema items"""
		l.info(f"Transforming {name}")
		required_properties = required_properties or []

		typename = mk_typename(name)  # references will often be properties and will not have a typename as their name. Eg `"myProp": { "$ref": "..." }`

		if isinstance(obj, OARef):
			return self.resolve_reference(name, obj, required_properties)

		elif isinstance(obj, OADef):
			cache_ref = RefCache.Ref(self.openapi.path, name)
			self.refcache.mark_referenceable(cache_ref, IR_T(t=name))

			if not obj.properties and not obj.allOf and not obj.additionalProperties:
				# does this even happen?
				t = IR_T(
					t=self.resolve_type(obj.t),
					required=name in required_properties,
				)
				self.refcache.mark_referenceable(cache_ref, t)
				return t

			maybe_parent_class = self._is_full_inherit(obj)
			if maybe_parent_class:
				t = self.resolve_reference(name, maybe_parent_class, required_properties)
				self.refcache.mark_referenceable(cache_ref, t)
				return t

			if self._is_dict(obj):
				t = self.ir_dict(name, obj, required_properties)
				self.refcache.mark_referenceable(cache_ref, t)
				return t

			properties = {}
			if obj.properties is not None:
				# we're transforming an object
				properties.update({n: self.transform(n, e, obj.required or []) for n, e in obj.properties.items()})

			if obj.allOf:
				for referenced in obj.allOf:
					referenced_obj = self.transform(name, referenced, [])
					if isinstance(referenced_obj, IR_T):
						resolved_t = referenced_obj.t
						if not isinstance(resolved_t, IRDef):
							l.warning(f"Reference inside IR_T was not an IRDef, we can't use this to merge properties. {name=} resolved_t={resolved_t}")
							continue
					elif isinstance(referenced_obj, IRDef):
						resolved_t = referenced_obj
					else:  # cov: err
						raise ValueError(f"Reference was not expected type={type(referenced_obj)}")

					properties.update(resolved_t.properties)

			t = IR_T(
				t=IRDef(
					name=typename,
					properties=properties,
					description=obj.description,
					src=self.openapi.path,
				),
				required=name in required_properties,
			)
			self.refcache.mark_referenceable(cache_ref, t)
			return t
		elif isinstance(obj, OADef.Property):
			resolved_type = self.resolve_type(obj.t)
			required = obj.required or name in required_properties  # obj.required is for QueryParams &c
			return IR_T(t=resolved_type, readonly=obj.readOnly, required=required)
		elif isinstance(obj, OADef.Array):
			return self.ir_array(name, obj, required_properties)
		elif isinstance(obj, OAEnum):
			if enum_params := obj.x_ms_enum:
				enum_name = enum_params.name

				# modelAsString means that no validation will happen.
				if enum_params.modelAsString:
					return IR_T(t=str, required=name in required_properties)
			else:
				enum_name = name

			return IR_T(
				t=IR_Enum(
					name=enum_name,
					values=obj.enum,
					description=obj.description,
				),
				required=name in required_properties,
			)

		else:  # cov: err
			raise TypeError(f"unsupported OpenAPI type {type(obj)}")

	def ir_param(self, obj: Union[OAParam, OARef]) -> IRParam:
		if isinstance(obj, OARef):
			# this is a parameter reference, so we don't use the `resolve_reference` function
			reader, resolved = self.openapi.load_relative(obj.ref)
			relative_transformer = JSONSchemaSubparser(reader, self.refcache)
			resolved_loaded = cast(Union[OARef, OAParam], TypeAdapter(Union[OARef, OAParam]).validate_python(resolved))

			transformed = relative_transformer.ir_param(resolved_loaded)

			return transformed

		if obj.oa_schema:
			t = self.transform(obj.name, obj.oa_schema, []).model_copy(update={"required": obj.required})
		elif obj.type == "array" and obj.items:
			item_t = self.transform(obj.name, obj.items, [obj.name])
			t = IR_T(t=IR_List(items=item_t), required=obj.required)
		else:
			assert obj.type, "OAParam without schema does not have a type"
			t = IR_T(t=self.resolve_type(obj.type), required=obj.required)

		return IRParam(t=t, name=obj.name, position=obj.in_component)

	def ir_response(self, obj: Union[OAResponse, OARef]) -> IR_T:
		if isinstance(obj, OARef):
			reader, resolved = self.openapi.load_relative(obj.ref)
			relative_transformer = JSONSchemaSubparser(reader, self.refcache)
			resolved_loaded = cast(Union[OARef, OAResponse], TypeAdapter(Union[OARef, OAResponse]).validate_python(resolved))

			transformed = relative_transformer.ir_response(resolved_loaded)

			return transformed

		schema = obj.oa_schema
		if not schema:
			return IR_T(t="None")
		elif isinstance(schema, OARef):
			return self.resolve_reference("", schema, []).model_copy(update={"required": True})
		elif isinstance(schema, (OADef, OADef.Array)):
			return self.transform("response", schema, ["response"])
		else:  # cov: err
			raise TypeError(f"unsupported type for response schema type={type(obj)}")

	def _categorise_params(self, params: List[IRParam]) -> Dict[ParamPosition, List[IRParam]]:
		d = defaultdict(list)
		for p in params:
			d[p.position].append(p)
		return d

	def _is_200(self, s: str) -> bool:
		return s.isdigit() and 200 <= int(s) <= 300

	def ip_op(self, apiv: str, path: str, method: str, op: OAOp) -> IROp:
		object_name, name = op.operationId.split("_")

		params = self._categorise_params([self.ir_param(p) for p in op.parameters])

		body_params = params[ParamPosition.body]
		body_type = IRTransformer.unify_ir_t([e.t for e in body_params])
		body_name = None if len(body_params) != 1 else body_params[0].name  # there can only be one body parameter by the spec # TODO: assert

		url_params = {e.name: e.t for e in params[ParamPosition.path]}
		query_params = {e.name: e.t for e in params[ParamPosition.query] if e.name != "api-version"}

		rets_ts = [self.ir_response(r) for r_name, r in (op.responses.items()) if r_name != "default" and self._is_200(r_name)]
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
			params=url_params or None,
			query_params=query_params or None,
			ret_t=ret_t,
		)
		return ir_op


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
	annotations: List[str] = []
	readonly: bool

	@property
	def normalised_name(self) -> str:
		if self.name == "id":
			return "rid"
		return self.name

	def codegen(self) -> str:
		if self.name == "id":
			return f'rid: {self.t} = Field(alias="id", default=None)'
		default = f" = {self.default}" if self.default else ""

		if not self.annotations:
			typedecl = self.t
		else:
			s = ",".join([self.t, *self.annotations])
			typedecl = f"Annotated[{s}]"

		return f"{self.name}: {typedecl}" + default


class AZDef(BaseModel, CodeGenable):
	"""An Azure Definition"""

	name: str
	description: Optional[str]
	fields: List[AZField]
	subclasses: List[AZDef] = []

	def codegen(self) -> str:
		if self.subclasses:
			property_c_codegen = indent("\n\n".join([e.codegen() for e in self.subclasses]), "\t")
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
				conditions.append(f"self.{field.normalised_name} == o.{field.normalised_name}")

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


class AZEnum(BaseModel, CodeGenable):
	name: str
	values: List[str]
	description: Optional[str] = None

	@staticmethod
	def _normalise_name(s: str) -> str:
		if s == "None":
			s = "none"
		s = s.replace(",", "_")
		s = s.replace("/", "_")
		return s

	def codegen(self) -> str:
		variants = indent("\n".join('%s = "%s"' % (self._normalise_name(e), e) for e in self.values), "\t")
		return dedent(
			'''\
			class {name}(Enum):
				"""{description}"""
			{variants}
			'''
		).format(name=self.name, description=self.description, variants=variants)


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

	class Param(BaseModel):
		name: str
		type: str
		required: bool = False

	ops_name: str
	name: str
	description: Optional[str] = None
	path: str
	method: str
	apiv: Optional[str]
	body: Optional[Body] = None
	params: Dict[str, str] = {}
	query_params: List[Param] = []
	ret_t: Optional[str]

	def _safe_param_name(self, s: str) -> str:
		return s.replace("$", "")

	def codegen(self) -> str:
		params = []  # TODO: add from path
		req_args = {
			"name": self.quote(self.ops_name + "." + self.name),
			"path": self.fstring(self.path),
		}
		query_params = ""
		if self.apiv:
			req_args["apiv"] = self.quote(self.apiv)
		if self.params:
			params.extend([f"{p_name}: {p_type}" for p_name, p_type in self.params.items()])
		if self.body:
			params.append(f"{self.body.name}: {self.body.type}")
			req_args["body"] = self.body.name

		if self.query_params:
			for p in self.query_params:
				p_name_safe = self._safe_param_name(p.name)
				if p.required:
					params.append(f"{p_name_safe}: {p.type}")
				else:
					params.append(f"{p_name_safe}: {p.type} = None")

				query_params += dedent(
					f"""\
				if {p_name_safe} is not None:
					r = r.add_param("{p.name}", str({p_name_safe}))
				"""
				)

		if self.ret_t:
			req_args["ret_t"] = self.ret_t

		return dedent(
			'''\
		@staticmethod
		def {name}({params}) -> Req[{ret_t}]:
			"""{description}"""
			r = Req.{method}(
		{req_args}
			)
		{query_params}
			return r
		'''
		).format(
			name=self.name,
			params=", ".join(params),
			description=self.description,
			ret_t=self.ret_t,
			method=self.method,
			req_args=indent(",\n".join("=".join([k, v]) for k, v in req_args.items()), "\t\t"),
			query_params=indent(query_params, "\t"),
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


class AZImport(BaseModel, CodeGenable):
	path: Path
	names: Set[str] = set()

	def codegen(self) -> str:
		names_str = ", ".join(self.names)

		path_str = str(self.path).replace("/", ".")
		return f"from {path_str} import {names_str}"

	@classmethod
	def merge(cls, imports: Iterable[AZImport]) -> List[AZImport]:
		merged: Dict[Path, AZImport] = {}
		for imp in imports:
			p = imp.path
			if p in merged:
				t = merged[p]
				merged[p] = AZImport(path=p, names=t.names | imp.names)
			else:
				merged[p] = imp

		return list(merged.values())


def codegen(transformer: IRTransformer, base_module: Path) -> str:
	header = dedent(
		"""\
		# pylint: disable
		# flake8: noqa
		from __future__ import annotations
		from enum import Enum
		from typing import Annotated, Dict, List, Optional, Union

		from pydantic import BaseModel, Field

		from llamazure.azrest.models import AzList, ReadOnly, Req, default_list, default_dict

		"""
	)
	return "\n".join([header, transformer.transform_imports(base_module), transformer.transform_definitions(), transformer.transform_paths()])


def path2module(p: Path) -> Path:
	"""
	Convert the filepath of the Azure OpenAPI spec to a module name

	:param p: the path within the azure openapi repo
	:return: a valid module name with extraneous pieces removed
	"""
	parts = list(p.with_suffix("").parts)

	def _remove_end(s: str, tgt: str) -> str:
		if s.endswith(tgt):
			return s[: -len(tgt)]
		return s

	def _remove_start(s: str, tgt: str) -> str:
		if s.startswith(tgt):
			return s[len(tgt) :]
		return s

	def category_shortcode(s: str):
		return {
			"resource-management": "r",  # for common types
			"resource-manager": "r",  # for resources
			"data-plane": "d",
		}.get(s, s)

	def provider(s: str):
		namespace, provider = s.lower().split(".")
		if namespace == "microsoft":
			return ["m", provider]
		else:
			return [namespace, provider]

	def schema(s: str):
		s = _remove_end(s, "_API")
		s = _remove_end(s, "-apis")
		s = _remove_end(s, "Calls")
		s = _remove_end(s, "-preview")
		s = _remove_start(s, "authorization-")
		return s.replace("-", "_")

	if parts[1] == "common-types":
		return Path(
			"c",  # common types should be common
			category_shortcode(parts[2]),
			parts[3],  # version
			schema(parts[4]),
		)
	else:
		return Path(
			# remove "specification", common to all
			parts[1],
			category_shortcode(parts[2]),
			*provider(parts[3]),
			# remove api version # TODO: option to not skip this/merge these
			schema(parts[6]),
		)


def main(openapi_root, openapi_file, output_dir, output_package=None):
	if output_package is None:
		output_package = output_dir

	cache = {}
	for f in re.split(r"[;,]", openapi_file):
		reader = Reader.load(openapi_root, Path(f), cache)
		cache = reader.reader_cache

	last_size = 0
	while len(cache) > last_size:
		this_size = len(cache)
		for p, r in list(cache.items())[last_size:]:
			transformer = IRTransformer.from_reader(r)

			output_file = Path(output_dir / path2module(p)).with_suffix(".py")
			output_file.parent.mkdir(exist_ok=True, parents=True)
			l.info(f"writing out openapi={p} t={transformer.openapi.path} file={output_file}")
			with open(output_file, mode="w", encoding="utf-8") as f:
				f.write(codegen(transformer, output_package))

		last_size = this_size


logging.basicConfig(level=logging.DEBUG)


if __name__ == "__main__":
	import sys

	logging.basicConfig(level=logging.DEBUG)
	main(*sys.argv[1:])
