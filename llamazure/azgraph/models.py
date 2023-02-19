"""Models for the Azure Resource Graph"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple, Union


@dataclass(frozen=True)
class Req:
	"""Azure Resource Graph request"""

	query: str
	subscriptions: Tuple[str]

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


@dataclass(frozen=True)
class ResErr:
	"""Azure Resource Graph error response"""

	code: str
	message: str
	details: Any


ResMaybe = Union[Res, ResErr]
