from __future__ import annotations

from typing import Any, Union

import requests

from llamazure.rbac import codec
from llamazure.rbac.models import Req, ResMaybe, ResErr


class Graph:
	"""
	Access the Microsoft Graph
	"""

	def __init__(self, token):
		self.token = token

	@classmethod
	def from_credential(cls, credential) -> Graph:
		"""Create from an Azure credential"""
		token = credential.get_token("https://graph.microsoft.com/")
		return cls(token)

	def q(self, q: str) -> Union[Any, ResErr]:
		"""Make a graph query"""
		return self._exec_query(Req(q))

	def _exec_query(self, req: Req) -> ResMaybe:
		path, params = codec.Encoder().encode(req)
		raw = requests.get(
			f"https://graph.microsoft.com/v1.0/{path}",
			headers={"Authorization": f"Bearer {self.token.token}"},
			params=params,
		).json()
		res = codec.Decoder().decode(req, raw)
		return res

	def query(self, req: Req) -> ResMaybe:
		"""Make a graph query"""
		return self._exec_query(req)