"""Azure Role Definitions and Assignments"""
from __future__ import annotations

from typing import Any, Dict, Sequence
from urllib.parse import urljoin

import requests

RoleDefT = Dict
RoleAsnT = Dict


class AzRest:
	def __init__(self, token, session: requests.Session, base_url: str = "https://management.azure.com/"):
		self.token = token
		self.session = session

		self.base_url = base_url

	@classmethod
	def from_credential(cls, credential) -> AzRest:
		"""Create from an Azure credential"""
		token = credential.get_token("https://management.azure.com//.default")
		session = requests.Session()
		return cls(token, session)

	def call(self, req: requests.Request) -> Any:
		"""Make the request to Azure"""
		req.headers["Authorization"] = f"Bearer {self.token.token}"  # TODO: push down into self.session
		return self.session.send(req.prepare()).json()["value"]  # TODO: write yet another fun interface to Azure

	def get(self, slug: str) -> Any:
		return self.call(requests.Request("GET", urljoin(self.base_url, slug)))


class RoleDefs:
	"""Interact with Azure RoleDefinitions"""

	provider_type = "Microsoft.Authorization/roleDefinitions"
	provider_slug = "/subscriptions/{subscription_id}/providers/Microsoft.Authorization/roleDefinitions"

	def __init__(self, azrest: AzRest):
		self.azrest = azrest

	def list_at_subscription(self, subscription_id) -> Sequence[RoleDefT]:
		"""Get roles at a subscription"""
		url = self.provider_slug.format(subscription_id=subscription_id)
		return self.azrest.get(url)
