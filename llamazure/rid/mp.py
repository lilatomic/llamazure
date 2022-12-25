"""Resource IDs that treat the resource id as a materialised path"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Generator, NewType, Optional, Protocol, Sequence, Tuple, Type, TypeVar, Union

from llamazure.rid.util import SegmentAndPathIterable, _Peekable

Path = NewType("Path", str)
PathSubscription = Path
PathResourceGroup = Path
PathResource = Path
PathSubResource = Path


class AzObj(Protocol):
	"""An Azure object"""

	path: Path
	"""The materialised path of this resource. This is the resource ID"""

	sub: PathSubscription


@dataclass(frozen=True)
class Subscription(AzObj):
	"""An Azure Subscription"""

	path: PathSubscription
	uuid: str

	@property
	def sub(self) -> PathSubscription:  # type: ignore
		"""Path of this subscription. Shim for uniformity with other AzObj"""
		return self.path


@dataclass(frozen=True)
class ResourceGroup(AzObj):
	"""An Azure Resource Group"""

	path: PathResourceGroup
	name: str
	sub: PathSubscription


@dataclass(frozen=True)
class Resource(AzObj):
	"""An Azure Resource"""

	path: PathResource
	provider: str
	res_type: str
	name: str
	rg: Optional[PathResourceGroup]
	sub: PathSubscription
	parent: Optional[Union[PathResource, PathSubResource]] = None


@dataclass(frozen=True)
class SubResource(AzObj):
	"""Some Azure resources aren't a full child, but are nested under a parent resource"""

	path: PathSubResource
	res_type: str
	name: str
	rg: Optional[PathResourceGroup]
	sub: PathSubscription
	parent: Optional[Union[PathResource, PathSubResource]] = None


MP = Tuple[Path, AzObj]


def parse(rid: str) -> MP:
	"""Parse an Azure resource ID into the Azure Resource it represents and its chain of parents"""
	*_, resource = list(parse_gen(rid))
	return resource


def parse_chain(rid: str) -> Sequence[MP]:
	"""Parse an Azure resource ID into a sequence of a resource and its parents"""

	return tuple(parse_gen(rid))


def parse_gen(rid: str) -> Generator[MP, None, None]:
	"""Parse an Azure resource ID into the Azure Resource it represents and its chain of parents"""

	parts = _Peekable(SegmentAndPathIterable(rid.lower()))

	try:
		if next(parts)[1] == "subscriptions":
			mp, p = next(parts)
			subscription = Subscription(mp, p)
			yield mp, subscription
		else:
			return

		if parts.peek()[1] == "resourcegroups":
			_ = next(parts)
			mp, p = next(parts)
			rg = ResourceGroup(mp, p, subscription.path)
			yield mp, rg
		else:
			rg = None

		parent: Optional[Union[PathResource, PathSubResource]] = None
		parsed_resource: Union[Resource, SubResource]

		while True:
			start = next(parts)

			if start[1] == "providers":
				provider = next(parts)[1]
				res_type = next(parts)[1]
				mp, name = next(parts)

				parsed_resource = Resource(mp, provider, res_type, name, parent=parent, rg=rg.path if rg else None, sub=subscription.path)
				parent = mp
				yield mp, parsed_resource
			else:
				res_type = start[1]
				mp, name = next(parts)

				parsed_resource = SubResource(mp, res_type, name, parent=parent, rg=rg.path if rg else None, sub=subscription.path)
				parent = mp
				yield mp, parsed_resource

	except StopIteration:
		return


def serialise(obj: AzObj):
	"""Turn an AzObj back into its resource ID"""
	return obj.path


def serialise_p(obj: AzObj) -> PurePosixPath:
	"""Turn an AzObj back into its resource ID as a pathlib.Path"""

	return PurePosixPath(obj.path)


def get_chain(obj: AzObj) -> Sequence[MP]:
	"""
	Get the resource chain from a parsed resource.
	If you have a resource ID, you can instead parse that directly with `parse_chain`
	"""
	return parse_chain(obj.path)


T = TypeVar("T", bound=AzObj)


def narrow_assert(obj: AzObj, t: Type[T]) -> T:
	"""
	Narrow a generic AzObj to a specific subtype.
	Uses `assert` for enforcement.
	This is useful for failing tests
	"""
	assert isinstance(obj, t), f"object {obj} was not of type {t}"
	return obj
