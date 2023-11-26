"""Access the Azure HTTP API"""
from __future__ import annotations

from typing import Type

import requests

from llamazure.azrest.models import AzType, Req, Ret_T


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

	def to_request(self, req: Req) -> requests.Request:
		r = requests.Request(method=req.method, url=self.base_url + req.path)
		if req.params:
			r.params = req.params
		if req.apiv:
			r.params["api-version"] = req.apiv
		if req.body:
			r.headers["Content-Type"] = "application/json"
			r.data = req.body.model_dump_json()
		return r

	def call(self, req: Req[Ret_T]) -> Ret_T:
		"""Make the request to Azure"""
		r = self.to_request(req)
		r.headers["Authorization"] = f"Bearer {self.token.token}"  # TODO: push down into self.session
		res = self.session.send(r.prepare())
		if not res.ok:
			print(res.json())
			raise AzureError(res.json())

		if req.ret_t is Type[None]:  # noqa: E721  # we're comparing types here
			return None  # type: ignore
		else:
			if issubclass(req.ret_t, AzType):
				return req.ret_t.model_validate(res.json()).render()
			else:
				return req.ret_t.model_validate(res.json())


class AzOps:
	"""Parent class for helpers which dispatch requests to Azure"""

	def __init__(self, azrest: AzRest):
		self.azrest = azrest

	def run(self, req: Req[Ret_T]) -> Ret_T:
		return self.azrest.call(req)
