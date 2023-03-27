from dataclasses import dataclass
from typing import Any, Optional, Dict


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

