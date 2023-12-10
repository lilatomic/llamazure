"""Access the Azure HTTP API"""
from __future__ import annotations

import dataclasses
import logging
import uuid
from typing import Type, Union, Tuple, Dict

import requests
from pydantic import TypeAdapter

from llamazure.azrest.models import AzList, Req, Ret_T, AzureError, AzureErrorResponse, BatchReq, AzBatch, \
	AzBatchResponses

l = logging.getLogger(__name__)


def fmt_req(req: Req) -> str:
	"""Format a request"""
	return req.name


def fmt_log(msg: str, req: Req, **kwargs: str) -> str:
	arg_s = " ".join(f"{k}={v}" for k,v in kwargs.items())
	return f"{msg} req={fmt_req(req)} {arg_s}"


@dataclasses.dataclass
class RetryPolicy:
	"""Parameters and strategies for retrying Azure Resource Graph queries"""

	retries: int = 0  # number of times to retry. This is in addition to the initial try


class AzRest:
	"""Access the Azure HTTP API"""

	def __init__(self, session: requests.Session, base_url: str = "https://management.azure.com", retry_policy: RetryPolicy = RetryPolicy()):
		self.session = session

		self.base_url = base_url
		self.retry_policy = retry_policy

	@classmethod
	def from_credential(cls, credential, token_scope="https://management.azure.com//.default", base_url="https://management.azure.com") -> AzRest:
		"""Create from an Azure credential"""
		token = credential.get_token(token_scope)
		session = requests.Session()
		session.headers["Authorization"] = f"Bearer {token.token}"

		return cls(session=session, base_url=base_url)

	def to_request(self, req: Req) -> requests.Request:
		r = requests.Request(method=req.method, url=self.base_url + req.path)
		if req.params:
			r.params = req.params
		if req.apiv:  # TODO: isn't this always required?
			r.params["api-version"] = req.apiv
		if req.body:
			r.headers["Content-Type"] = "application/json"
			r.data = req.body.model_dump_json(exclude_none=True)
		return r


	def _build_url(self, req: Req) -> str:
		"""Hacky way to get requests to build our url for us"""
		return self.session.prepare_request(self.to_request(req)).url

	def _to_batchable_request(self, req: Req, batch_id: str) -> dict:
		r = {
			"httpMethod": req.method,
			"name": batch_id,
			"url": self._build_url(req),
		}
		if req.body:
			r["content"]=req.body
		return r

	def batch_to_request(self, batch: BatchReq) -> Tuple[Dict[str, Req], Req[AzBatchResponses]]:
		keyed_requests = {str(uuid.uuid4()): r for r in batch.requests}
		req = Req(
			name=batch.name,
			path="/batch",
			method="POST",
			apiv=batch.apiv,
			body=AzBatch(
				requests=[self._to_batchable_request(r, batch_id) for batch_id, r in keyed_requests.items()]
			),
			ret_t=AzBatchResponses,
		)
		return keyed_requests, req

	def _resolve_batch_response(self, req: Req[Ret_T], res) -> Union[Ret_T, AzureError]:
		if res.content.get("error"):
			return AzureErrorResponse.model_validate(res.content)
		type_adapter = TypeAdapter(req.ret_t)
		return type_adapter.validate_python(res.content)

	def call_batch(self, req: BatchReq) -> Tuple:
		keyed_requests, batch_request = self.batch_to_request(req)

		batch_response: AzBatchResponses = self.call(batch_request)
		deserialised_responses = [self._resolve_batch_response(keyed_requests[e.name], e) for e in batch_response.responses]
		return deserialised_responses

	def call(self, req: Req[Ret_T]) -> Ret_T:
		"""Make the request to Azure"""
		r = self.to_request(req)
		res = self._call_with_retry(req, r)
		if res is None:
			return res

		if isinstance(res, AzList):
			acc = res.value
			page = 0
			while res.nextLink:
				page += 1
				l.debug(fmt_log("paginating req", req, page=str(page)))
				r = self.to_request(req)
				r.url = res.nextLink
				res = self._call_with_retry(req, r)
				acc.extend(res.value)
			return acc
		else:
			return res

	def _call_with_retry(self, req: Req[Ret_T], r: requests.Request) -> Ret_T:
		l.debug(fmt_log("making req", req))
		res = self._do_call(req, r)
		if isinstance(res, AzureError):
			retries = 0
			while retries < self.retry_policy.retries and isinstance(res, AzureError):
				l.debug(fmt_log("req returned error; retrying", req, err=res.error.model_dump_json()))
				retries += 1
				res = self._do_call(req, r)

		if isinstance(res, AzureError):
			l.warning(fmt_log("req returned error; retries exhausted", req, err=res.error.model_dump_json()))
			raise res
		else:
			l.debug(fmt_log("req complete", req))
			return res

	def _do_call(self, req: Req[Ret_T], r: requests.Request) -> Union[Ret_T, AzureError]:
		"""Make a single request to Azure, without retry or pagination"""
		res = self.session.send(self.session.prepare_request(r))
		if not res.ok:
			return AzureErrorResponse.model_validate_json(res.content).error.as_exception()

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
