"""Tools for working with Azure resource IDs"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Generator, Iterator, Optional, Sequence, Union


class AzObj(abc.ABC):
	"""An Azure object"""

	@abc.abstractmethod
	def slug(self) -> str:
		"""
		Generate the component of the resource ID specific to this resource (and not part of its parent).
		For example, for a resource with ID "/subscriptions/000/resourcegroups/111/providers/Microsoft.things/widgets/222",
		the resource "222" would have slug "/providers/Microsoft.things/widgets/222"
		"""
		...


@dataclass(frozen=True)
class Subscription(AzObj):
	"""An Azure Subscription"""

	uuid: str

	def slug(self) -> str:
		return f"/subscriptions/{self.uuid}"


@dataclass(frozen=True)
class ResourceGroup(AzObj):
	"""An Azure Resource Group"""

	name: str
	sub: Subscription

	def slug(self) -> str:
		return f"/resourcegroups/{self.name}"


@dataclass(frozen=True)
class Resource(AzObj):
	"""An Azure Resource"""

	provider: str
	res_type: str
	name: str
	rg: Optional[ResourceGroup]
	sub: Subscription
	parent: Optional[Union[Resource, SubResource]] = None

	def slug(self) -> str:
		return f"/providers/{self.provider}/{self.res_type}/{self.name}"


@dataclass(frozen=True)
class SubResource(AzObj):
	"""Some Azure resources aren't a full child, but are nested under a parent resource"""

	res_type: str
	name: str
	rg: Optional[ResourceGroup]
	sub: Subscription
	parent: Optional[Union[Resource, SubResource]] = None

	def slug(self) -> str:
		return f"/{self.res_type}/{self.name}"


class _Peekable:
	"""A wrapper for iterators which lets you peek at the next element without consuming it"""

	def __init__(self, iterator: Iterator):
		self.iterator = iterator
		self._cache = None

	def peek(self):
		"""Peek at the next item in the iterator without consuming it"""
		if not self._cache:
			self._cache = next(self.iterator)
		return self._cache

	def __next__(self):
		if not self._cache:
			return next(self.iterator)
		else:
			out, self._cache = self._cache, None
			return out


def parse(rid: str) -> Optional[AzObj]:
	"""Parse an Azure resource ID into the Azure Resource it represents and its chain of parents"""
	*_, resource = parse_gen(rid)
	return resource


def parse_chain(rid: str) -> Sequence[AzObj]:
	"""Parse an Azure resource ID into a sequence of a resource and its parents"""
	return tuple(parse_gen(rid))


def parse_gen(rid: str) -> Generator[AzObj, None, None]:
	"""Parse an Azure resource ID into a generator with components"""
	parts = _Peekable(iter(rid.lower().split("/")))

	try:
		_ = next(parts)  # escape leading `/`
		if next(parts) == "subscriptions":
			subscription = Subscription(next(parts))
			yield subscription
		else:
			return

		if parts.peek() == "resourcegroups":
			_ = next(parts)
			rg = ResourceGroup(next(parts), subscription)
			yield rg
		else:
			rg = None  # There are subscription-level resources, like locks

		parent: Optional[Union[Resource, SubResource]] = None
		parsed_resource: Union[Resource, SubResource]
		while True:
			start = next(parts)

			if start == "providers":
				provider = next(parts)
				res_type = next(parts)
				name = next(parts)

				parsed_resource = Resource(provider, res_type, name, parent=parent, rg=rg, sub=subscription)
				parent = parsed_resource
				yield parsed_resource
			else:
				res_type = start
				name = next(parts)

				parsed_resource = SubResource(res_type, name, parent=parent, rg=rg, sub=subscription)
				parent = parsed_resource
				yield parsed_resource

	except StopIteration:
		return


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


def get_chain(obj: AzObj) -> Sequence[AzObj]:
	"""
	Get the resource chain from a parsed resource.
	If you have a resource ID, you can instead parse that directly with `parse_chain`
	"""
	if isinstance(obj, Subscription):
		return (obj,)
	elif isinstance(obj, ResourceGroup):
		return (obj.sub, obj)
	elif isinstance(obj, Resource) or isinstance(obj, SubResource):
		o = []
		current: Union[Resource, SubResource, None] = obj
		while current:
			o.append(current)
			current = current.parent
		if obj.rg:
			return (obj.sub, obj.rg, *reversed(o))
		else:
			return (obj.sub, *reversed(o))
	else:
		raise TypeError(f"Expected known subclass of AzObj, got {type(obj)}")
