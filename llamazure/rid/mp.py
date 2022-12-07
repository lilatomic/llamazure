"""Resource IDs that treat the resource id as a materialised path"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Generator, NewType, Optional, Tuple, Union

from llamazure.rid.util import FindAllIterable, _Peekable

Path = NewType("Path", str)
PathSubscription = Path
PathResourceGroup = Path
PathResource = Path
PathSubResource = Path


class AzObj(abc.ABC):
	"""An Azure object"""

	@property
	@abc.abstractmethod
	def path(self) -> Path:
		"""The materialised path of this resource. This is the resource ID"""
		...


@dataclass(frozen=True)
class Subscription(AzObj):
	"""An Azure Subscription"""

	path: PathSubscription
	uuid: str


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


MP = NewType("MP", Tuple[Path, AzObj])


def parse_gen(rid: str) -> Generator[MP, None, None]:
	"""Parse an Azure resource ID into the Azure Resource it represents and its chain of parents"""

	parts = _Peekable(FindAllIterable(rid))

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

				parsed_resource = Resource(mp, provider, res_type, name, parent=parent, rg=rg.path, sub=subscription.path)
				parent = mp
				yield mp, parsed_resource
			else:
				res_type = start[1]
				mp, name = next(parts)

				parsed_resource = SubResource(mp, res_type, name, parent=parent, rg=rg.path, sub=subscription.path)
				parent = mp
				yield mp, parsed_resource

	except StopIteration:
		return
