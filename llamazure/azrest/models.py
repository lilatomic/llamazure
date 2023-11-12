"""Models for the Azure REST API"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Dict, Optional

from pydantic import BaseModel


@dataclass(frozen=True)
class Req:
	"""Azure REST request"""

	path: str
	method: str
	apiv: Optional[str]
	body: Optional[BaseModel] = None
	params: Dict[str, str] = field(default_factory=dict)

	@classmethod
	def get(cls, path: str, apiv: str) -> Req:
		return cls(path, "GET", apiv)

	@classmethod
	def delete(cls, path: str, apiv: str) -> Req:
		return cls(path, "DELETE", apiv)

	@classmethod
	def put(cls, path: str, apiv: str, body: Optional[BaseModel]) -> Req:
		return cls(path, "PUT", apiv, body)

	@classmethod
	def post(cls, path: str, apiv: str, body: Optional[BaseModel]) -> Req:
		return cls(path, "POST", apiv, body)

	@classmethod
	def patch(cls, path: str, apiv: str, body: Optional[BaseModel]) -> Req:
		return cls(path, "PATCH", apiv, body)

	def add_params(self, params: Dict[str, str]) -> Req:
		return dataclasses.replace(self, params={**self.params, **params})
