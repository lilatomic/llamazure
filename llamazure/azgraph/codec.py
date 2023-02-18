"""Codec for serialising and deserialising for Azure"""

import dataclasses
import json
from typing import Any


class Encoder(json.JSONEncoder):
	"""Encode Req for JSON for Azure"""

	def default(self, o: Any) -> Any:
		if dataclasses.is_dataclass(o):
			return dataclasses.asdict(o)
		return super().default(o)
