"""Interface to the Azure Resource Graph"""
from __future__ import annotations

import dataclasses
import json
import operator
from functools import reduce
from typing import Optional, Tuple

import requests

from llamazure.azgraph import codec
from llamazure.azgraph.models import Req, Res


class Graph:
	"""Access the Azure Resource Graph"""

	def __init__(self, token, subscriptions: Tuple[str]):
		self.token = token
		self.subscriptions = subscriptions

	@classmethod
	def from_credential(cls, credential) -> Graph:
		"""Create from an Azure credential"""
		token = credential.get_token("https://management.azure.com//.default")
		subscriptions = cls._get_subscriptions(token)
		return cls(token, subscriptions)

	@staticmethod
	def _get_subscriptions(token) -> Tuple[str]:
		raw = requests.get(
			"https://management.azure.com/subscriptions?api-version=2020-01-01",
			headers={"Authorization": f"Bearer {token.token}", "Content-Type": "application/json"},
		).json()
		return tuple(s["subscriptionId"] for s in raw["value"])

	def q(self, q: str):
		"""Make a graph query"""
		return self.query(Req(q, self.subscriptions)).data

	def query_single(self, req: Req) -> Res:
		"""Make a graph query for a single page"""
		raw = requests.post(
			"https://management.azure.com/providers/Microsoft.ResourceGraph/resources?api-version=2021-03-01",
			headers={"Authorization": f"Bearer {self.token.token}", "Content-Type": "application/json"},
			data=json.dumps(req, cls=codec.Encoder),
		).json()

		return codec.Decoder().decode(req, raw)

	def query(self, req: Req) -> Res:
		"""Make a graph query"""
		ress = []
		res = self.query_single(req)
		ress.append(res)
		while res.skipToken:
			res = self._query_next(req, res)
			ress.append(res)
		return reduce(operator.add, ress)

	def _query_next(self, req: Req, last: Res) -> Optional[Res]:
		"""Query the next page in a paginated query"""
		options = req.options.copy()
		options["$skipToken"] = last.skipToken
		next_req = dataclasses.replace(req, options=options)
		return self.query_single(next_req)
