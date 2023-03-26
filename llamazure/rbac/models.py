from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Res:
	"""Microsoft Graph response"""

	req: str

	odata_context: str
	value: Any

