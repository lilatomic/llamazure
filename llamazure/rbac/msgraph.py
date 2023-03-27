from __future__ import annotations

import dataclasses
import operator
from functools import reduce
from typing import Any, Union

import requests

from llamazure.rbac import codec
from llamazure.rbac.models import Req, Res, ResErr, ResMaybe


@dataclasses.dataclass
class RetryPolicy:
	"""Parameters and strategies for retrying Azure Resource Graph queries"""

	retries: int = 0  # number of times to retry. This is in addition to the initial try


class Graph:
	"""
	Access the Microsoft Graph
	"""

	def __init__(self, token, retry_policy: RetryPolicy = RetryPolicy()):
		self.token = token
		self.retry_policy = retry_policy

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

	def query_single(self, req: Req) -> ResMaybe:
		"""Make a graph query for a single page"""
		res = self._exec_query(req)

		if isinstance(res, ResErr):
			retries = 0
			while retries < self.retry_policy.retries and isinstance(res, ResErr):
				retries += 1
				res = self._exec_query(req)
		return res

	def query_next(self, req: Req, previous: Res) -> ResMaybe:
		"""Query the next page in a paginated query"""
		# The @odata.nextLink contains the whole link, so we just call it without modifying params
		raw = requests.get(
			previous.odata["@odata.nextLink"],
			headers={"Authorization": f"Bearer {self.token.token}"},
		).json()
		res = codec.Decoder().decode(req, raw)
		return res

	def query(self, req: Req) -> ResMaybe:
		"""Make a graph query"""
		ress = []
		res = self.query_single(req)
		if isinstance(res, ResErr):
			return res

		ress.append(res)
		while "@odata.nextLink" in res.odata:
			res = self.query_next(req, res)
			if isinstance(res, ResErr):
				return res
			ress.append(res)
		return reduce(operator.add, ress)
