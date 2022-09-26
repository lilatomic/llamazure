from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Optional, Union


class AzObj(abc.ABC):
	"""An Azure object"""

	...


@dataclass
class Subscription(AzObj):
	uuid: str


@dataclass
class ResourceGroup(AzObj):
	name: str
	subscription: Subscription


@dataclass
class Resource(AzObj):
	provider: str
	res_type: str
	name: str
	rg: ResourceGroup
	parent: Optional["Resource"]


def parse(rid: str) -> Optional[AzObj]:
	parts = iter(rid.lower().split("/"))

	out = None
	try:
		if next(parts) == "subscription":
			out = Subscription(next(parts))
		else:
			return None

		if next(parts) == "resourcegroups":
			out = rg = ResourceGroup(next(parts), out)
		else:
			return out

		parent = None
		while True:
			if next(parts) == "providers":
				provider = next(parts)
				res_type = next(parts)
				name = next(parts)
				parent = Resource(provider, res_type, name, parent=parent, rg=rg)

	except StopIteration:
		return out