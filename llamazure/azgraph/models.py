"""Models for the Azure Resource Graph"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple


@dataclass(frozen=True)
class Req:
	"""Azure Resource Graph request"""

	query: str
	subscriptions: Tuple[str]

	facets: Tuple = tuple()
	managementGroupId: Optional[str] = None
	options: Any = None


@dataclass(frozen=True)
class Res:
	"""Azure Resource Graph response"""

	totalRecords: int
	count: int
	resultTruncated: Any
	facets: Tuple
	data: Any
	skipToken: Optional[str] = None


@dataclass(frozen=True)
class ResErr:
	"""Azure Resource Graph error response"""

	code: str
	message: str
	details: Any
