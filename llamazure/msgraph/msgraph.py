from __future__ import annotations

import dataclasses
import operator
import urllib.parse
from functools import reduce
from typing import Any, Dict, Optional, Union

import requests

from llamazure.msgraph import codec
from llamazure.msgraph.models import Req, Res, ResErr, ResMaybe


@dataclasses.dataclass
class RetryPolicy:
	"""Parameters and strategies for retrying Azure Resource Graph queries"""

	retries: int = 0  # number of times to retry. This is in addition to the initial try


class Graph:
	"""
	Access the Microsoft Graph
	"""

	def __init__(self, token, retry_policy: RetryPolicy = RetryPolicy()):
		self.token = token
		self.retry_policy = retry_policy

	@classmethod
	def from_credential(cls, credential) -> Graph:
		"""Create from an Azure credential"""
		token = credential.get_token("https://graph.microsoft.com/")
		return cls(token)

	def q(self, q: str) -> Union[Any, ResErr]:
		"""Make a graph query"""
		return self._exec_query(Req(q))

	def _make_http_request(self, req: Req, url: str, params: Optional[Dict] = None) -> ResMaybe:
		raw = requests.get(
			url,
			headers={"Authorization": f"Bearer {self.token.token}"},
			params=params,
		)
		res = codec.Decoder().decode(req, raw.json())
		return res

	def _exec_query(self, req: Req) -> ResMaybe:
		path, params = codec.Encoder().encode(req)
		if not urllib.parse.urlparse(req.query).netloc:
			url = f"https://graph.microsoft.com/v1.0/{path}"
		else:
			url = path
		res = self._make_http_request(req, url, params)
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
		if previous.nextLink is None:
			raise StopIteration("nextLink is None, no more pages to iterage")

		# The @odata.nextLink contains the whole link, so we just call it without modifying params
		next_req = Req(previous.nextLink)
		res = self.query_single(next_req)
		return res

	def query(self, req: Req) -> ResMaybe:
		"""Make a graph query"""
		ress = []
		res = self.query_single(req)
		if isinstance(res, ResErr):
			return res

		ress.append(res)
		while res.nextLink is not None:
			res = self.query_next(req, res)
			if isinstance(res, ResErr):
				return res
			ress.append(res)
		return reduce(operator.add, ress)
