"""Models for the Azure REST API"""
from __future__ import annotations

import dataclasses
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel

Ret_T = TypeVar("Ret_T")
ReadOnly = Optional


@dataclass(frozen=True)
class Req(Generic[Ret_T]):
	"""Azure REST request"""

	path: str
	method: str
	apiv: Optional[str]
	body: Optional[BaseModel] = None
	params: Dict[str, str] = field(default_factory=dict)
	ret_t: Type[Ret_T] = Type[None]  # type: ignore

	@classmethod
	def get(cls, path: str, apiv: str, ret_t: Type[Ret_T]) -> Req:
		return cls(path, "GET", apiv, ret_t=ret_t)

	@classmethod
	def delete(cls, path: str, apiv: str, ret_t: Optional[Type[Ret_T]] = Type[None]) -> Req:
		return cls(path, "DELETE", apiv, ret_t=ret_t)

	@classmethod
	def put(cls, path: str, apiv: str, body: Optional[BaseModel], ret_t: Type[Ret_T]) -> Req:
		return cls(path, "PUT", apiv, body, ret_t=ret_t)

	@classmethod
	def post(cls, path: str, apiv: str, body: Optional[BaseModel], ret_t: Type[Ret_T]) -> Req:
		return cls(path, "POST", apiv, body, ret_t=ret_t)

	@classmethod
	def patch(cls, path: str, apiv: str, body: Optional[BaseModel], ret_t: Type[Ret_T]) -> Req:
		return cls(path, "PATCH", apiv, body, ret_t=ret_t)

	def add_params(self, params: Dict[str, str]) -> Req:
		return dataclasses.replace(self, params={**self.params, **params})

	def with_ret_t(self, ret_t: Type[Ret_T]) -> Req:
		return dataclasses.replace(self, ret_t=ret_t)


T = TypeVar("T")


class AzType(ABC, Generic[T]):
	@abstractmethod
	def render(self) -> T:
		"""Render this into the actual target type"""


class AzList(BaseModel, Generic[Ret_T], AzType[List[Ret_T]]):
	value: List[Ret_T]
	nextLink: Optional[str] = None

	def render(self) -> List[Ret_T]:
		return self.value
