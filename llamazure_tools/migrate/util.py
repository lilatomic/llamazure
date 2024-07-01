from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class JSONTraverser:
	"""Traverse a JSON structure and replace exact string matches"""

	replacements: Dict[str, str]

	def traverse(self, obj: Any) -> Any:
		if isinstance(obj, dict):
			return {key: self.traverse(value) for key, value in obj.items()}
		elif isinstance(obj, list):
			return [self.traverse(item) for item in obj]
		elif isinstance(obj, str):
			return self.replacements.get(obj, obj)
		else:
			return obj
