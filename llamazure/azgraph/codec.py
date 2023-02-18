"""Codec for serialising and deserialising for Azure"""

import dataclasses
import json
from typing import Any, Dict, Union

from llamazure.azgraph.models import Res, ResErr


class Encoder(json.JSONEncoder):
	"""Encode Req for JSON for Azure"""

	def default(self, o: Any) -> Any:
		if dataclasses.is_dataclass(o):
			return dataclasses.asdict(o)
		return super().default(o)


class Decoder:
	"""Decode Res from JSON from Azure"""

	def decode(self, o: Dict) -> Union[Res, ResErr]:
		"""Decode Res from JSON from Azure"""
		error = o.pop("error", None)
		if error:
			return ResErr(**error)

		skip_token = o.pop("$skipToken", None)
		return Res(**o, skipToken=skip_token)
