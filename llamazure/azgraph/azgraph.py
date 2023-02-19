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
	"""
	Access the Azure Resource Graph

	The easiest way to instantiate this is with the `from_credential` method.

	>>> from azure.identity import DefaultAzureCredential
	>>> credential = DefaultAzureCredential()
	>>> graph = Graph(credential)

	Making queries is easiest with the `q` method:
	>>> graph.q("Resources | project id, name, type, location | limit 5")
	[{'id': '/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg0/providers/Microsoft.Storage/storageAccounts/sa0', 'name': 'sa0', 'type': 'microsoft.storage/storageaccounts', 'location': 'canadacentral'}]

	If you want to provide options to the query, use a `Req` and the `query` function

	>>> from llamazure.azgraph.models import Req, Res
	>>> graph.query(Req(
	... 	query="Resources | project id, name, type, location | limit 5",
	... 	subscriptions=("00000000-0000-0000-0000-000000000001",)
	... ))
	"""

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

		# "$skip" overrides "$skipToken", so we need to remove it.
		# This is fine, since the original skip amount is encoded into the
		options.pop("$skip", None)

		next_req = dataclasses.replace(req, options=options)
		return self.query_single(next_req)
