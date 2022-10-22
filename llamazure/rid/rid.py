"""Tools for working with Azure resource IDs"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Optional, Union


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
	sub: Subscription


@dataclass
class Resource(AzObj):
	"""An Azure Resource"""

	provider: str
	res_type: str
	name: str
	rg: Optional[ResourceGroup]
	sub: Subscription
	parent: Optional[Union[Resource, SubResource]] = None


@dataclass
class SubResource(AzObj):
	"""Some Azure resources aren't a full child, but are nested under a parent resource"""

	res_type: str
	name: str
	rg: Optional[ResourceGroup]
	sub: Subscription
	parent: Optional[Union[Resource, SubResource]] = None


class _Peekable:
	def __init__(self, iter):
		self.iter = iter
		self._cache = None

	def peek(self):
		if not self._cache:
			self._cache = next(self.iter)
		return self._cache

	def __next__(self):
		if not self._cache:
			return next(self.iter)
		else:
			out, self._cache = self._cache, None
			return out


def parse(rid: str) -> Optional[AzObj]:
	"""Parse an Azure resource ID into the Azure Resource it represenets and its chain of parents"""
	parts = _Peekable(iter(rid.lower().split("/")))

	out: Optional[AzObj] = None
	try:
		_ = next(parts)  # escape leading `/`
		if next(parts) == "subscriptions":
			out = subscription = Subscription(next(parts))
		else:
			return None

		if parts.peek() == "resourcegroups":
			_ = next(parts)
			out = rg = ResourceGroup(next(parts), subscription)
		else:
			rg = None  # There are subscription-level resources, like locks

		parent: Optional[Union[Resource, SubResource]] = None
		while True:
			start = next(parts)

			if start == "providers":
				provider = next(parts)
				res_type = next(parts)
				name = next(parts)
				out = parent = Resource(provider, res_type, name, parent=parent, rg=rg, sub=subscription)
			else:
				res_type = start
				name = next(parts)
				out = parent = SubResource(res_type, name, parent=parent, rg=rg, sub=subscription)

	except StopIteration:
		return out


def serialise(obj: AzObj) -> str:
	"""Turn an AzObj back into its resource ID"""
	return str(serialise_p(obj))


def serialise_p(obj: AzObj) -> PurePosixPath:
	"""Turn an AzObj back into its resource ID as a pathlib.Path"""
	if isinstance(obj, Subscription):
		return PurePosixPath("/subscriptions") / obj.uuid
	if isinstance(obj, ResourceGroup):
		return serialise_p(obj.sub) / "resourcegroups" / obj.name
	if isinstance(obj, Resource):
		return serialise_p(obj.parent or obj.rg or obj.sub) / "providers" / obj.provider / obj.res_type / obj.name
	if isinstance(obj, SubResource):
		return serialise_p(obj.parent or obj.rg or obj.sub) / obj.res_type / obj.name
	else:
		raise TypeError(f"expected valid subclass of AzObj, found {type(obj)}")
