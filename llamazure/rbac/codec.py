"""Codec for serialising and deserialising for Azure"""

from typing import Any, Dict

from llamazure.rbac.models import Res, Req


class Encoder:
	"""Encode Req for query params for Azure"""

	def encode(self, req: Req):
		params = {
			"$top": req.top
		}
		params = {k: v for k, v in params.items() if v is not None}

		return req.query, params


class Decoder:
	"""Decode Res from JSON from Azure"""

	def decode(self, req: Req, o: Dict[str, Any]):
		"""Decode Res from JSON from Azure"""
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