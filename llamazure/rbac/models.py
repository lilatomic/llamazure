from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union


@dataclass(frozen=True)
class Req:
	"""Microsoft Graph request"""

	query: str

	options: Dict = field(default_factory=dict)


@dataclass(frozen=True)
class Res:
	"""Microsoft Graph response"""

	req: Req

	odata: Dict[str, Any]
	value: Any

	nextLink: Optional[str] = None

	def __add__(self, other):
		if not isinstance(other, Res):
			raise TypeError(type(other))
		return dataclasses.replace(other, value=self.value + other.value)


@dataclass(frozen=True)
class ResErr:
	"""Microsoft Graph error response"""

	code: str
	message: str
	innerError: Optional[ResErr]
	error_metadata: Optional[dict] = None  # the info crammed into the innerError field that is not actually an error


ResMaybe = Union[Res, ResErr]
