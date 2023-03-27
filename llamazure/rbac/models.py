from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Dict, Union


@dataclass(frozen=True)
class Req:
	"""Microsoft Graph request"""

	query: str
	top: Optional[int] = None


@dataclass(frozen=True)
class Res:
	"""Microsoft Graph response"""

	req: Req

	odata: Dict[str, Any]
	value: Any


@dataclass(frozen=True)
class ResErr:
	"""Microsoft Graph error response"""

	code: str
	message: str
	innererror: Optional[ResErr]


ResMaybe = Union[Res, ResErr]
