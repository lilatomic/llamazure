"""Access the Azure HTTP API"""
from __future__ import annotations

from typing import Any

import requests
from pydantic import BaseModel


class AzureError(Exception):
	"""An Azure-specific error"""

	def __init__(self, json):
		self.json = json


class AzRest:
	"""Access the Azure HTTP API"""

	def __init__(self, token, session: requests.Session, base_url: str = "https://management.azure.com"):
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
		res = self.session.send(req.prepare())  # TODO: write yet another fun interface to Azure
		if not res.ok:
			raise AzureError(res.json())

		return res

	def get(self, slug: str, apiv: str) -> Any:
		"""GET request"""
		return self.call(requests.Request("GET", self.base_url + slug, params={"api-version": apiv})).json()

	def delete(self, slug: str, apiv: str) -> Any:
		"""DELETE request"""
		return self.call(requests.Request("DELETE", self.base_url + slug, params={"api-version": apiv}))

	def put(self, slug: str, apiv: str, body: BaseModel) -> Any:
		"""PUT request, serialising the body"""
		return self.call(
			requests.Request("PUT", self.base_url + slug, params={"api-version": apiv}, data=body.model_dump_json(), headers={"Content-Type": "application/json"})
		).json()
