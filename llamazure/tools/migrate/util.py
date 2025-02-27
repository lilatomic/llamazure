"""Utils"""

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from llamazure.azrest.models import ensure
from llamazure.rid import rid


@dataclass
class JSONTraverser:
	"""Traverse a JSON structure and replace exact string matches"""

	replacements: Dict[str, str]

	def traverse(self, obj: Any) -> Any:
		"""Traverse a JSON structure and replace exact string matches"""
		if isinstance(obj, dict):
			return {key: self.traverse(value) for key, value in obj.items()}
		elif isinstance(obj, list):
			return [self.traverse(item) for item in obj]
		elif isinstance(obj, str):
			return self.replacements.get(obj, obj)
		else:
			return obj


def rid_params(res: rid.Resource) -> Tuple[str, str, str]:
	return ensure(res.sub).uuid, ensure(res.rg).name, res.name
