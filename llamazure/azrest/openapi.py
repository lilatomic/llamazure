"""
OpenAPI explorer for Azure

Naming Conventions:
- OA* : OpenAPI things
- AZ* : Azure things
OA things are used to parse the OpenAPI spec. AZ things are used for reasoning about the Azure API. For example, PermissionGetResult might be an OA object because it is present in the OpenAPI spec. However, it's just a list of Permission objects. It won't have an AZ object; instead, it will be transformed into something like an AZList[AZPermission].
"""
from __future__ import annotations
from __future__ import annotations

import itertools
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Union, Type

from pydantic import BaseModel, Field, TypeAdapter


class OADef(BaseModel):
	class Property(BaseModel):
		t: Union[str, OADef] = Field(alias="type")
		description: str = None

	class Ref(BaseModel):
		ref: str = Field(alias="$ref")
		description: str = None

	properties: Dict[str, Union[OADef.Property, OADef.Ref]]
	t: str = Field(alias="type")
	description: str = None


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


def dereference_refs(ds: Dict[str, OADef]) -> Dict[str, OADef]:
	"""Inflate refs to their objects"""
	def resolve_path(path: str) -> str:
		if path.startswith("#/definitions/"):
			return path[len("#/definitions/"):]
		return path

	out = {}
	for name, obj in ds.items():
		new_props = {}
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



if __name__ == "__main__":
	import sys

	reader = Reader.load(sys.argv[1])

	out = definitions(reader.definitions)
	out = dereference_refs(out)

	# out: dict[str, dict[str, Any]] = defaultdict(dict)
	# for path, pathobj in reader.paths:
	# 	for method, operationobj in operations(pathobj).items():
	# 		out[path][method] = {k: operationobj[k] for k in ("description", "operationId")}
	#
	print(json.dumps({k:v.model_dump() for k,v in out.items()}))
