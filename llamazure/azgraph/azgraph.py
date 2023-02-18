"""Interface to the Azure Resource Graph"""
from __future__ import annotations

import json
from typing import Tuple

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

	def query(self, req: Req) -> Res:
		"""Make a graph query"""
		raw = requests.post(
			"https://management.azure.com/providers/Microsoft.ResourceGraph/resources?api-version=2021-03-01",
			headers={"Authorization": f"Bearer {self.token.token}", "Content-Type": "application/json"},
			data=json.dumps(req, cls=codec.Encoder),
		).json()

		return codec.Decoder().decode(raw)
