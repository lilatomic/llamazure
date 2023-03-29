"""Codec for serialising and deserialising for Azure"""

from typing import Any, Dict, Optional, Union

from llamazure.rbac.models import Req, Res, ResErr, ResMaybe


class Encoder:
	"""Encode Req for query params for Azure"""

	def encode(self, req: Req):
		return req.query, req.options


class Decoder:
	"""Decode Res from JSON from Azure"""

	def decode(self, req: Req, o: Dict[str, Any]) -> ResMaybe:
		"""Decode Res from JSON from Azure"""
		print(">>>>>>", o)

		error = self.deserialise_error(o.pop("error", None))
		if error:
			return error

		odata = {}
		data = {}
		for k, v in o.items():
			if k.startswith("@odata"):
				odata[k] = v
			else:
				data[k] = v

		return Res(
			req=req,
			odata=odata,
			nextLink=odata.get("@odata.nextLink", None),
			**data,
		)

	def deserialise_error(self, o: Optional[Dict[str, Any]]) -> Optional[ResErr]:
		if o is None:
			return None
		inner_error_raw = o.pop("innerError", {})
		inner_error = self.deserialise_inner_error(inner_error_raw)
		if isinstance(inner_error, ResErr):
			return ResErr(o["code"], o["message"], innerError=inner_error)
		else:
			return ResErr(o["code"], o["message"], innerError=None, error_metadata=inner_error)

	def deserialise_inner_error(self, o: Optional[Dict[str, Any]]) -> Union[ResErr, Dict, None]:
		"""Deserialise the inner error which is either an error or some metadata"""
		if o is None:
			return o

		inner_error_raw = o.pop("innerError", None)
		inner_error = self.deserialise_inner_error(inner_error_raw)
		if isinstance(inner_error, ResErr):
			# If we successfully deserialised an inner error, we're confident that we're also an error
			return ResErr(o["code"], o["message"], innerError=inner_error)
		else:
			try:
				return ResErr(o["code"], o["message"], innerError=None, error_metadata=inner_error)
			except KeyError:
				# If there's a KeyError, we know that we're the error metadata (or something broken).
				# Either way, we should return the input dictionary
				return o
