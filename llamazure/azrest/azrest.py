"""Access the Azure HTTP API"""
from __future__ import annotations

import dataclasses
import json
import logging
import time
from typing import Dict, Optional, Type, Union, cast

import requests
from pydantic import BaseModel, TypeAdapter, ValidationError

from llamazure.azrest.models import AzBatch, AzBatchResponses, AzList, AzureError, AzureErrorResponse, BatchReq, Req, Ret_T

l = logging.getLogger(__name__)


def fmt_req(req: Req) -> str:
	"""Format a request"""
	return req.name


def fmt_log(msg: str, req: Req, **kwargs: Union[str, int, float]) -> str:
	"""Format a log statement referencing a request"""
	arg_s = " ".join(f"{k}={v}" for k, v in kwargs.items())
	return f"{msg} req={fmt_req(req)} {arg_s}"


@dataclasses.dataclass
class RetryPolicy:
	"""Parameters and strategies for retrying Azure Resource Graph queries"""

	retries: int = 0  # number of times to retry. This is in addition to the initial try
	long_running_retries: int = 10  # number of retry attempts to try each long-running task. This is in addition to the initial try


HEADER_LOCATION = "Location"
HEADER_ASYNC = "Azure-AsyncOperation"
HEADER_RETRY_AFTER = "Retry-After"


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
		"""Convert a Req into a requests.Request"""
		r = requests.Request(method=req.method, url=self.base_url + req.path)
		if req.params:
			r.params = req.params
		if req.apiv:  # TODO: isn't this always required?
			r.params["api-version"] = req.apiv
		if req.body:
			r.headers["Content-Type"] = "application/json"
			if isinstance(req.body, dict):
				# allows you to do your own serialisation
				r.data = json.dumps(req.body)
			else:
				r.data = req.body.model_dump_json(exclude_none=True, by_alias=True)
		return r

	def _build_url(self, req: Req) -> str:
		"""Hacky way to get requests to build our url for us"""
		return cast(str, self.session.prepare_request(self.to_request(req)).url)

	def _to_batchable_request(self, req: Req, batch_id: str) -> Dict[str, Union[str, BaseModel]]:
		r: Dict[str, Union[str, BaseModel]] = {
			"httpMethod": req.method,
			"name": batch_id,
			"url": self._build_url(req),
		}
		if req.body:
			r["content"] = req.body
		return r

	def batch_to_request(self, batch: BatchReq) -> Req[AzBatchResponses]:
		"""Convert the BatchReq into the Req that contains the requests"""
		req = Req(
			name=batch.name,
			path="/batch",
			method="POST",
			apiv=batch.apiv,
			body=AzBatch(requests=[self._to_batchable_request(r, batch_id) for batch_id, r in batch.requests.items()]),
			ret_t=AzBatchResponses,
		)
		return req

	def _resolve_batch_response(self, req: Req[Ret_T], res) -> Union[Ret_T, AzureError]:
		"""Deserialise the response to a batch request"""
		if res.content.get("error"):
			return AzureErrorResponse.model_validate(res.content).error.as_exception()
		type_adapter = TypeAdapter(req.ret_t)
		return type_adapter.validate_python(res.content)

	def call_batch(self, req: BatchReq) -> Dict[str, Union[Ret_T, AzureError]]:
		"""Call a batch request"""
		batch_request = self.batch_to_request(req)

		batch_response: AzBatchResponses = self.call(batch_request)
		deserialised_responses = {e.name: self._resolve_batch_response(req.requests[e.name], e) for e in batch_response.responses}
		return deserialised_responses

	def call(self, req: Req[Ret_T]) -> Ret_T:
		"""Make the request to Azure"""
		r = self.to_request(req)
		res = self._deserialise(req, self._call_with_retry(req, r))
		if res is None:
			return res

		if isinstance(res, AzList):
			res_list: AzList = res
			acc = res.value
			page = 0
			while res_list.nextLink:
				page += 1
				l.debug(fmt_log("paginating req", req, page=str(page)))
				# This is basically always a GET
				# TODO: support the nextLink.operationName
				r = requests.Request(method="GET", url=res_list.nextLink)
				res_list = self._deserialise(req, self._call_with_retry(req, r))  # type: ignore  # we know the req
				acc.extend(res_list.value)
			return acc  # type: ignore  # we're deliberately unwrapping a list into its primitive type
		else:
			return res

	def _call_with_retry(self, req: Req[Ret_T], r: requests.Request) -> requests.Response:
		l.debug(fmt_log("making req", req))
		res = self._do_call(r)
		if isinstance(res, AzureError):
			retries = 0
			while retries < self.retry_policy.retries and isinstance(res, AzureError):
				l.debug(fmt_log("req returned error; retrying", req, err=res.error.model_dump_json()))
				retries += 1
				res = self._do_call(r)  # type: ignore

		if isinstance(res, AzureError):
			l.warning(fmt_log("req returned error; retries exhausted", req, err=res.error.model_dump_json()))
			raise res
		else:
			l.debug(fmt_log("req complete", req))
			return res

	def _do_call(self, r: requests.Request) -> Union[requests.Response, AzureError]:
		"""Make a single request to Azure, without retry or pagination"""
		res = self.session.send(self.session.prepare_request(r))
		if not res.ok:
			return AzureErrorResponse.model_validate_json(res.content).error.as_exception()
		return res

	def _deserialise(self, req: Req[Ret_T], res: requests.Response) -> Ret_T:
		if req.ret_t is Type[None]:  # noqa: E721  # we're comparing types here
			return None  # type: ignore

		type_adapter = TypeAdapter(req.ret_t)
		if len(res.content) == 0:
			return type_adapter.validate_python(None)

		deserialised = type_adapter.validate_json(res.content)
		return deserialised

	def _get_longpoll_location(self, res: requests.Response) -> Optional[str]:
		if HEADER_ASYNC in res.headers:
			return res.headers[HEADER_ASYNC]
		elif HEADER_LOCATION in res.headers:
			return res.headers[HEADER_LOCATION]
		else:
			return None

	def _get_time_to_wait(self, res: requests.Response) -> float:
		if HEADER_RETRY_AFTER in res.headers:
			return float(res.headers[HEADER_RETRY_AFTER])
		else:
			return 5.0

	def call_long_operation(self, req: Req[Ret_T]) -> Ret_T:
		"""Make a call for a long-running operation, where we will need to check a new location for the result."""
		ir = self._call_with_retry(req, self.to_request(req))

		if ir.status_code not in {202, 201}:
			l.warning(fmt_log("req longpoll returned unexpected status", req, status=ir.status_code))

		result_location = self._get_longpoll_location(ir)
		if result_location is None:
			msg = f"req longpoll did not have header needed to find result of longpoll, expected one of '{HEADER_ASYNC}' or '{HEADER_LOCATION}'"
			l.error(fmt_log(msg, req))
			raise RuntimeError(msg)  # TODO: use real class

		done_req = Req.from_url(req.name, "GET", result_location.removeprefix(self.base_url), ret_t=req.ret_t)  # TODO: better name

		res = self._call_with_retry(done_req, self.to_request(done_req))

		retries = 0
		while retries < self.retry_policy.long_running_retries and res.status_code != 200:
			time_to_wait = self._get_time_to_wait(res)
			l.debug(fmt_log("longpoll request sleep", req, attempt=retries, time=time_to_wait))
			time.sleep(time_to_wait)
			res = self._call_with_retry(done_req, self.to_request(done_req))

		if res.status_code not in {200, 204}:
			try:
				error = AzureErrorResponse.model_validate_json(res.content).error.as_exception()
			except ValidationError:
				msg = "req longpoll returned unexpected status that could not be deserialised into an error"
				l.error(fmt_log(msg, req, status=res.status_code, content=res.content.decode()))
				raise RuntimeError(msg)
			raise error
		else:
			return self._deserialise(req, res)


class AzOps:
	"""Parent class for helpers which dispatch requests to Azure"""

	def __init__(self, azrest: AzRest):
		self.azrest = azrest

	def run(self, req: Req[Ret_T]) -> Ret_T:
		"""Call a request"""
		return self.azrest.call(req)


def rid_eq(a: Optional[str], b: Optional[str]) -> bool:
	"""Whether 2 Azure resource IDs are the same"""
	return a is not None and b is not None and a.lower() == b.lower()
