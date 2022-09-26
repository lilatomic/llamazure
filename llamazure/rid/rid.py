"""Tools for working with Azure resource IDs"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class AzObj(abc.ABC):
	"""An Azure object"""

	...


@dataclass
class Subscription(AzObj):
	"""An Azure Subscription"""

	uuid: str


@dataclass
class ResourceGroup(AzObj):
	"""An Azure Resource Group"""

	name: str
	subscription: Subscription


@dataclass
class Resource(AzObj):
	"""An Azure Resource"""

	provider: str
	res_type: str
	name: str
	rg: ResourceGroup
	parent: Optional["Resource"] = None


def parse(rid: str) -> Optional[AzObj]:
	"""Parse an Azure resource ID into the Azure Resource it represenets and its chain of parents"""
	parts = iter(rid.lower().split("/"))

	out: Optional[AzObj] = None
	try:
		_ = next(parts)
		if next(parts) == "subscriptions":
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
				out = parent = Resource(provider, res_type, name, parent=parent, rg=rg)

	except StopIteration:
		return out


def serialise(obj: AzObj) -> str:
	"""Turn an AzObj back into its resource ID"""
	return str(serialise_p(obj))


def serialise_p(obj: AzObj) -> Path:
	"""Turn an AzObj back into its resource ID as a pathlib.Path"""
	if isinstance(obj, Subscription):
		return Path("/subscriptions") / obj.uuid
	if isinstance(obj, ResourceGroup):
		return serialise_p(obj.subscription) / "resourcegroups" / obj.name
	if isinstance(obj, Resource):
		return (
			serialise_p(obj.parent if obj.parent else obj.rg)
			/ "providers"
			/ obj.provider
			/ obj.res_type
			/ obj.name
		)
	else:
		raise TypeError(f"expected valid subclass of AzObj, found {type(obj)}")
