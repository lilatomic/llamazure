from __future__ import annotations

import itertools
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


class Reader:
	"""Read Microsoft OpenAPI specifications"""

	def __init__(self, openapi: dict):
		self.doc = openapi

	@classmethod
	def load(cls, fp) -> Reader:
		if isinstance(fp, (str, Path)):
			with open(fp, mode="r", encoding="utf-8") as fp:
				return Reader(json.load(fp))
		else:
			return Reader(json.load(fp))

	@property
	def paths(self):
		return list(itertools.chain(self.doc["paths"].items(), self.doc.get("x-ms-paths", {}).items()))


def operations(path_object: dict):
	return {k: v for k, v in path_object.items() if k in {"get", "put", "post", "delete", "options", "head", "patch", "trace"}}


if __name__ == "__main__":
	import sys

	reader = Reader.load(sys.argv[1])

	out: dict[str, dict[str, Any]] = defaultdict(dict)
	for path, pathobj in reader.paths:
		for method, operationobj in operations(pathobj).items():
			out[path][method] = {k: operationobj[k] for k in ("description", "operationId")}

	print(json.dumps(out))
