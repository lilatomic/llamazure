"""Codec for serialising and deserialising for Azure"""

from typing import Any, Dict, Optional

from llamazure.rbac.models import Res, Req, ResMaybe, ResErr


class Encoder:
	"""Encode Req for query params for Azure"""

	def encode(self, req: Req):
		return req.query, req.options


class Decoder:
	"""Decode Res from JSON from Azure"""

	def decode(self, req: Req, o: Dict[str, Any]) -> ResMaybe:
		"""Decode Res from JSON from Azure"""
		error = self.deserialise_error(o.pop("error", None))
		if error:
			return error

		odata = {}
		data = {}
		for k,v in o.items():
			if k.startswith("@odata"):
				odata[k] = v
			else:
				data[k] = v

		return Res(
			req=req,
			odata=odata,
			**data,
		)

	def deserialise_error(self, o: Optional[Dict[str, Any]]) -> Optional[ResErr]:
		if o is None:
			return None
		inner_error = self.deserialise_error(o.pop("innererror", None))
		return ResErr(o["code"], o["message"], inner_error)
