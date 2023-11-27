"""Access the Azure HTTP API"""
from __future__ import annotations

import dataclasses
import logging
from typing import Type, Union

import requests
from pydantic import TypeAdapter

from llamazure.azrest.models import AzList, Req, Ret_T

l = logging.getLogger(__name__)


class AzureError(Exception):
	"""An Azure-specific error"""

	def __init__(self, json):
		self.json = json


@dataclasses.dataclass
class RetryPolicy:
	"""Parameters and strategies for retrying Azure Resource Graph queries"""

	retries: int = 0  # number of times to retry. This is in addition to the initial try


class AzRest:
	"""Access the Azure HTTP API"""

	def __init__(self, token, session: requests.Session, base_url: str = "https://management.azure.com", retry_policy: RetryPolicy = RetryPolicy()):
		self.token = token
		self.session = session

		self.base_url = base_url
		self.retry_policy = retry_policy

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
			r.data = req.body.model_dump_json(exclude_none=True)
		return r

	def call(self, req: Req[Ret_T]) -> Ret_T:
		"""Make the request to Azure"""
		r = self.to_request(req)
		res = self._call_with_retry(req, r)
		if res is None:
			return res

		if isinstance(res, AzList):
			acc = res.value
			while res.nextLink:
				r = self.to_request(req)
				r.url = res.nextLink
				res = self._call_with_retry(req, r)
				acc.extend(res.value)
			return acc
		else:
			return res

	def _call_with_retry(self, req: Req[Ret_T], r: requests.Request) -> Ret_T:
		res = self._do_call(req, r)
		if isinstance(res, AzureError):
			retries = 0
			while retries < self.retry_policy.retries and isinstance(res, AzureError):
				retries += 1
				res = self._do_call(req, r)

		if isinstance(res, AzureError):
			raise res
		else:
			return res

	def _do_call(self, req: Req[Ret_T], r: requests.Request) -> Union[Ret_T, AzureError]:
		"""Make a single request to Azure, without retry or pagination"""
		r.headers["Authorization"] = f"Bearer {self.token.token}"  # TODO: push down into self.session
		res = self.session.send(r.prepare())
		if not res.ok:
			l.warning(res.json())
			return AzureError(res.json())

		if req.ret_t is Type[None]:  # noqa: E721  # we're comparing types here
			return None  # type: ignore

		type_adapter = TypeAdapter(req.ret_t)
		if len(res.content) == 0:
			return type_adapter.validate_python(None)

		deserialised = type_adapter.validate_json(res.content)
		return deserialised


class AzOps:
	"""Parent class for helpers which dispatch requests to Azure"""

	def __init__(self, azrest: AzRest):
		self.azrest = azrest

	def run(self, req: Req[Ret_T]) -> Ret_T:
		return self.azrest.call(req)


def rid_eq(a: str, b: str) -> bool:
	"""Whether 2 Azure resource IDs are the same"""
	return a.lower() == b.lower()
