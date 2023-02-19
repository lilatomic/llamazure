"""Codec for serialising and deserialising for Azure"""

import dataclasses
import json
from typing import Any, Dict

from llamazure.azgraph.models import Req, Res, ResErr, ResMaybe


class Encoder(json.JSONEncoder):
	"""Encode Req for JSON for Azure"""

	def default(self, o: Any) -> Any:
		if dataclasses.is_dataclass(o):
			return dataclasses.asdict(o)
		return super().default(o)


class Decoder:
	"""Decode Res from JSON from Azure"""

	def decode(self, req: Req, o: Dict) -> ResMaybe:
		"""Decode Res from JSON from Azure"""
		error = o.pop("error", None)
		if error:
			details_json = error.pop("details", [])
			details = tuple(detail_json for detail_json in details_json)
			return ResErr(**error, details=details)

		skip_token = o.pop("$skipToken", None)
		return Res(req=req, **o, skipToken=skip_token)
