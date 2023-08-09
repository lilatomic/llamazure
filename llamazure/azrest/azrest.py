from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

import requests


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
