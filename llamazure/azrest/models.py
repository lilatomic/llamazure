"""Models for the Azure REST API"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Dict, Generic, List, Optional, Type, TypeVar, Any

from pydantic import BaseModel, Field

Ret_T = TypeVar("Ret_T")
ReadOnly = Optional


@dataclass(frozen=True)
class Req(Generic[Ret_T]):
	"""Azure REST request"""

	name: str
	path: str
	method: str
	apiv: Optional[str]
	body: Optional[BaseModel] = None
	params: Dict[str, str] = field(default_factory=dict)
	ret_t: Type[Ret_T] = Type[None]  # type: ignore

	@classmethod
	def get(cls, name: str, path: str, apiv: str, ret_t: Type[Ret_T]) -> Req:
		return cls(name, path, "GET", apiv, ret_t=ret_t)

	@classmethod
	def delete(cls, name: str, path: str, apiv: str, ret_t: Optional[Type[Ret_T]] = Type[None]) -> Req:
		return cls(name, path, "DELETE", apiv, ret_t=ret_t)

	@classmethod
	def put(cls, name: str, path: str, apiv: str, body: Optional[BaseModel], ret_t: Type[Ret_T]) -> Req:
		return cls(name, path, "PUT", apiv, body, ret_t=ret_t)

	@classmethod
	def post(cls, name: str, path: str, apiv: str, body: Optional[BaseModel], ret_t: Type[Ret_T]) -> Req:
		return cls(name, path, "POST", apiv, body, ret_t=ret_t)

	@classmethod
	def patch(cls, name: str, path: str, apiv: str, body: Optional[BaseModel], ret_t: Type[Ret_T]) -> Req:
		return cls(name, path, "PATCH", apiv, body, ret_t=ret_t)

	def add_params(self, params: Dict[str, str]) -> Req:
		return dataclasses.replace(self, params={**self.params, **params})

	def with_ret_t(self, ret_t: Type[Ret_T]) -> Req:
		return dataclasses.replace(self, ret_t=ret_t)


class AzList(BaseModel, Generic[Ret_T]):
	value: List[Ret_T]
	nextLink: Optional[str] = None


class AzureError(Exception):
	def __init__(self, error: AzureErrorDetails):
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
		return AzureError(self)


class AzureErrorAdditionInfo(BaseModel):
	"""The resource management error additional info."""

	info_type: str = Field(alias="type")
	info: Dict = {}
