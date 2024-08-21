"""Models for the Azure Resource Graph"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple, TypedDict, Union


class AzureGraphException(RuntimeError):
	err: ResErr

	def __init__(self, err: ResErr):
		super().__init__("Error querying the Azure Resource Graph")
		self.err = err


@dataclass(frozen=True)
class Req:
	"""Azure Resource Graph request"""

	query: str
	subscriptions: Tuple[str, ...]

	facets: Tuple = tuple()
	managementGroupId: Optional[str] = None
	options: Dict = field(default_factory=dict)


@dataclass(frozen=True)
class Res:
	"""Azure Resource Graph response"""

	req: Req

	totalRecords: int
	count: int
	resultTruncated: Any
	facets: Tuple
	data: Any
	skipToken: Optional[str] = None

	def __add__(self, other):
		if not isinstance(other, Res):
			raise TypeError(type(other))
		# using `other` here ensures that we get the skipToken and other stuff more up-to-date
		return dataclasses.replace(other, count=self.count + other.count, data=self.data + other.data)

	def to_optional(self) -> Optional[Any]:
		return self.data


@dataclass(frozen=True)
class ResErr:
	"""Azure Resource Graph error response"""

	code: str
	message: str
	details: Tuple[ErrorDetails, ...]

	def to_optional(self) -> Optional[Any]:
		return None

	def exception(self) -> Exception:
		return AzureGraphException(self)

class ErrorDetails(TypedDict):
	"""Error details. TypedDict because extra parameters are supplied"""

	code: str
	message: str


ResMaybe = Union[Res, ResErr]
