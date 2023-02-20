"""Interface to the Azure Resource Graph"""
from __future__ import annotations

import dataclasses
import json
import operator
from functools import reduce
from typing import Any, Tuple, Union, cast

import requests

from llamazure.azgraph import codec
from llamazure.azgraph.models import Req, Res, ResErr, ResMaybe


@dataclasses.dataclass
class RetryPolicy:
	"""Parameters and strategies for retrying Azure Resource Graph queries"""

	retries: int = 0  # number of times to retry. This is in addition to the initial try


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

	def __init__(self, token, subscriptions: Tuple[str], retry_policy: RetryPolicy = RetryPolicy()):
		self.token = token
		self.subscriptions = subscriptions
		self.retry_policy = retry_policy

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
		return cast(Tuple[str], tuple(s["subscriptionId"] for s in raw["value"]))

	def q(self, q: str) -> Union[Any, ResErr]:
		"""Make a graph query"""
		res = self.query(Req(q, self.subscriptions))
		if isinstance(res, ResErr):
			return res
		return res.data

	def _exec_query(self, req) -> ResMaybe:
		raw = requests.post(
			"https://management.azure.com/providers/Microsoft.ResourceGraph/resources?api-version=2021-03-01",
			headers={"Authorization": f"Bearer {self.token.token}", "Content-Type": "application/json"},
			data=json.dumps(req, cls=codec.Encoder),
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
		options = req.options.copy()
		options["$skipToken"] = previous.skipToken

		# "$skip" overrides "$skipToken", so we need to remove it.
		# This is fine, since the original skip amount is encoded into the
		options.pop("$skip", None)

		next_req = dataclasses.replace(req, options=options)
		return self.query_single(next_req)

	def query(self, req: Req) -> ResMaybe:
		"""Make a graph query"""
		ress = []
		res = self.query_single(req)
		if isinstance(res, ResErr):
			return res

		ress.append(res)
		while res.skipToken:
			res = self.query_next(req, res)
			if isinstance(res, ResErr):
				return res
			ress.append(res)
		return reduce(operator.add, ress)
