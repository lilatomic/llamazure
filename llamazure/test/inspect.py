import datetime
import json
import os
from dataclasses import asdict, is_dataclass
from typing import Any
from uuid import UUID


def print_output(name: str, output: Any):
	should_print = os.environ.get("INTEGRATION_PRINT_OUTPUT", "False") == "True"
	if should_print:
		print(name, output)


class MyEncoder(json.JSONEncoder):
	"""Encoder for more types"""

	def default(self, o):
		if is_dataclass(o):
			return asdict(o)
		if isinstance(o, datetime.datetime):
			return o.isoformat()
		if isinstance(o, UUID):
			return str(o)
		return super().default(o)
