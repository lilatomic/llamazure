"""Codec for serialising and deserialising for Azure"""

import dataclasses
from typing import Any, Dict

from llamazure.rbac.models import Res


class Decoder:
	"""Decode Res from JSON from Azure"""

	def decode(self, req: str, o: Dict):
		"""Decode Res from JSON from Azure"""

		odata_context = o.pop("@odata.context")
		return Res(
			req=req,
			odata_context=odata_context,
			**o,
		)