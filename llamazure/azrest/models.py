"""Models for the Azure REST API"""

from __future__ import annotations

import dataclasses
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Generic, Iterator, List, Optional, Type, TypeVar, Union
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel, BeforeValidator, Field

Ret_T = TypeVar("Ret_T")
Ret_T0 = TypeVar("Ret_T0")
ReadOnly = Optional[Ret_T]


# pylint: disable=too-many-arguments
@dataclass(frozen=True)
class Req(Generic[Ret_T]):
	"""Azure REST request"""

	name: str
	path: str
	method: str
	apiv: Optional[str]
	body: Optional[BaseModel] = None
	params: Dict[str, Union[str, List[str]]] = field(default_factory=dict)
	ret_t: Type[Ret_T] = Type[None]  # type: ignore

	@classmethod
	def get(cls, name: str, path: str, apiv: str, ret_t: Type[Ret_T]) -> Req:
		"""Create a GET request"""
		return cls(name, path, "GET", apiv, ret_t=ret_t)

	@classmethod
	def delete(cls, name: str, path: str, apiv: str, ret_t: Union[Any, Optional[Type[Ret_T]]] = Type[None]) -> Req:
		"""Create a DELETE request"""
		return cls(name, path, "DELETE", apiv, ret_t=ret_t)  # type: ignore

	@classmethod
	def put(cls, name: str, path: str, apiv: str, body: Optional[BaseModel], ret_t: Type[Ret_T]) -> Req:
		"""Create a PUT request"""
		return cls(name, path, "PUT", apiv, body, ret_t=ret_t)

	@classmethod
	def post(cls, name: str, path: str, apiv: str, body: Optional[BaseModel], ret_t: Type[Ret_T]) -> Req:
		"""Create a POST request"""
		return cls(name, path, "POST", apiv, body, ret_t=ret_t)

	@classmethod
	def patch(cls, name: str, path: str, apiv: str, body: Optional[BaseModel], ret_t: Type[Ret_T]) -> Req:
		"""Create a PATCH request"""
		return cls(name, path, "PATCH", apiv, body, ret_t=ret_t)

	def named(self, name: str) -> Req:
		"""Change the friendly name of this request"""
		return dataclasses.replace(self, name=name)

	def add_params(self, params: Dict[str, str]) -> Req:
		"""Add query params to this request"""
		return dataclasses.replace(self, params={**self.params, **params})

	def add_param(self, name: str, value: str) -> Req:
		return dataclasses.replace(self, params={**self.params, **{name: value}})

	def with_ret_t(self, ret_t: Type[Ret_T0]) -> Req[Ret_T0]:
		"""Override the return type"""
		return dataclasses.replace(self, ret_t=ret_t)  # type: ignore

	@classmethod
	def from_url(
		cls,
		name: str,
		method: str,
		url: str,
		body: Optional[BaseModel] = None,
		ret_t: Type[Ret_T] = Type[None],  # type: ignore
	) -> Req:
		"""
		Build a Req from a URL, useful for when Azure has handed you one; for example, from the 'Azure-AsyncOperation' header.

		This function does less validation, on the assumption Azure knows what we should do.
		"""
		parsed = urlparse(url)

		path = parsed.path
		params = parse_qs(parsed.query)
		built_params = {k: v[0] if len(v) == 1 else v for k, v in params.items()}
		apiv = built_params.pop("api-version", None)  # type: ignore # this shouldn't happen but there's no reason for us to throw

		return Req(
			name=name,
			path=path,
			method=method,
			apiv=apiv,  # type: ignore # we know what we're doing
			body=body,
			params=built_params,
			ret_t=ret_t,
		)


@dataclass
class BatchReq:
	"""A batch of requests to the Azure API"""

	requests: Dict[str, Req]
	name: str = "batch"
	apiv: str = "2020-06-01"

	@classmethod
	def gather(cls, reqs: List[Req], name: str = "batch", apiv: str = "2020-06-01") -> BatchReq:
		"""Gather many requests into a batch, automatically assigning them an ID"""
		keyed_requests = {str(uuid.uuid4()): r for r in reqs}
		return cls(keyed_requests, name, apiv)


class AzBatch(BaseModel, Generic[Ret_T]):
	"""A serialisable request to the batch API"""

	requests: List[Ret_T]


class AzBatchResponse(BaseModel):
	"""A single response in a batch"""

	name: str
	httpStatusCode: int
	headers: Dict[str, str] = {}
	content: Optional[Dict]


class AzBatchResponses(BaseModel):
	"""The bundle of responses from the Azure batch API"""

	responses: List[AzBatchResponse]


class AzList(BaseModel, Generic[Ret_T]):
	"""A deserialisation of a List from Azure"""

	value: List[Ret_T]
	nextLink: Optional[str] = None

	def __iter__(self) -> Iterator[Ret_T]:  # type: ignore[override]
		# TODO: explode if there's a nextLink because this won't paginate properly
		return self.value.__iter__()


default_list = BeforeValidator(lambda v: v if v is not None else [])
default_dict = BeforeValidator(lambda v: v if v is not None else {})


class AzureError(Exception):
	"""An error from the Azure API"""

	def __init__(self, error: AzureErrorDetails):
		super().__init__(error.message)  # TODO: better stringify message
		self.error = error


class AzureErrorResponse(BaseModel):
	"""The container of an Azure error"""

	error: AzureErrorDetails


class AzureErrorDetails(BaseModel):
	"""An Azure-specific error"""

	code: str
	message: str
	target: Optional[str] = None
	details: List[AzureErrorDetails] = []
	additionalInfo: List[AzureErrorAdditionInfo] = []

	def as_exception(self) -> AzureError:
		"""Wrap this in a Python Exception for throwing"""
		return AzureError(self)


class AzureErrorAdditionInfo(BaseModel):
	"""The resource management error additional info."""

	info_type: str = Field(alias="type")
	info: Dict = {}


T = TypeVar("T")


def ensure(a: Optional[T]) -> T:
	"""Ensure the result is not None"""
	if a is None:
		raise TypeError("value was None")
	return a


P0 = TypeVar("P0", bound=BaseModel)
P1 = TypeVar("P1", bound=BaseModel)


def cast_as(obj: P0, cls: Type[P1]) -> P1:
	"""
	Cast one model into another.

	Useful for turning a Foo into a FooUpdateParameters.
	"""
	return cls.model_validate(obj.model_dump())
