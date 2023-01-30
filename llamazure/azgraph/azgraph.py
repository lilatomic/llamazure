"""Interface to the Azure Resource Graph"""
from __future__ import annotations

from typing import List

import requests


class Graph:
	"""Access the Azure Resource Graph"""

	def __init__(self, token, subscriptions: List[str]):
		self.token = token
		self.subscriptions = subscriptions

	@classmethod
	def from_credential(cls, credential) -> Graph:
		"""Create from an Azure credential"""
		token = credential.get_token("https://management.azure.com//.default")
		subscriptions = cls._get_subscriptions(token)
		return cls(token, subscriptions)

	@staticmethod
	def _get_subscriptions(token):
		raw = requests.get(
			"https://management.azure.com/subscriptions?api-version=2020-01-01",
			headers={"Authorization": f"Bearer {token.token}", "Content-Type": "application/json"},
		).json()
		return [s["id"] for s in raw["value"]]

	def q(self, q: str):
		"""Make a graph query"""
		raw = requests.post(
			"https://management.azure.com/providers/Microsoft.ResourceGraph/resources?api-version=2021-03-01",
			headers={"Authorization": f"Bearer {self.token.token}", "Content-Type": "application/json"},
			json={"subscriptions": self.subscriptions, "query": q},
		).json()

		return raw["data"]
