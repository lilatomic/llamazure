"""Tresources for Materialised Path resources"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Generic, Iterable, Optional, Tuple, TypeVar, Union

from llamazure.rid.mp import MP, AzObj, Path, PathResource, PathResourceGroup, PathSubResource, PathSubscription, Resource, ResourceGroup, SubResource, Subscription
from llamazure.tresource.itresource import INode, ITresource, ITresourceData


@dataclass
class TresourceMP(ITresource[AzObj, Path]):
	"""Tresource implementation for materialised-path-based resources. It's not really a tree, since materialised-path is an alternative to using trees"""

	resources: Dict[Path, AzObj] = field(default_factory=dict)

	def add(self, obj: AzObj):
		"""Add an AzObj to this Tresource"""
		self.resources[obj.path] = obj

	def add_many(self, mps: Iterable[MP]):
		"""Add an iterable of MP to this Tresource"""
		self.resources.update(dict(mps))

	def subs(self):
		return frozenset(obj.sub for obj in self.resources.values())

	def rgs_flat(self) -> FrozenSet[PathResourceGroup]:
		"""All resource groups that any resource is contained by"""

		def extract_rg(res: AzObj) -> Optional[PathResourceGroup]:
			if isinstance(res, Resource) or isinstance(res, SubResource):
				return res.rg
			if isinstance(res, ResourceGroup):
				return res.path
			return None

		return frozenset(filter(None, set(extract_rg(res) for res in self.resources.values())))

	@property
	def res(self):
		"""Resources in this Tresource"""
		return self.resources

	def res_flat(self) -> FrozenSet[Union[PathResource, PathSubResource]]:
		"""All Resources and SubResources"""
		return frozenset(path for path, res in self.resources.items() if isinstance(res, Resource) or isinstance(res, SubResource))

	def where_parent(self, obj: AzObj) -> TresourceMP:
		"""Return all objects with this as a parent"""
		return self.where(obj.path)

	def where(self, parent_path: Path) -> TresourceMP:
		"""
		Return all objects with this as the start of their Resource ID
		Excludes a complete match. For example, `where("/subscriptions/0")` will not return the subscription itself.
		"""
		o = TresourceMP({k: v for k, v in self.resources.items() if k.startswith(parent_path)})
		o.resources.pop(parent_path, None)  # remove complete match, if present
		return o

	def where_subscription(self, sub: Subscription) -> TresourceMP:
		"""Return all objects with this Subscription as a parent"""
		return self.where(sub.path)

	def where_rg(self, rg: ResourceGroup) -> TresourceMP:
		"""Return all objects with this ResourceGroup as a parent"""
		return self.where(rg.path)


T = TypeVar("T")


@dataclass
class MPData(INode[AzObj, T]):
	"""Node class for MP"""

	obj: AzObj
	data: Optional[T]


@dataclass
class TresourceMPData(Generic[T], ITresourceData[AzObj, T, MPData[T], Path]):
	"""
	Tresource implementation for materialised-path-based resources.
	It's not really a tree, since materialised-path is an alternative to using trees
	This one stores data, too.
	"""

	resources: Dict[Path, MPData[T]] = field(default_factory=dict)

	def set_data(self, obj: AzObj, data: T) -> None:
		"""Add an AzObj to this Tresource"""
		self.resources[obj.path] = MPData(
			obj,
			data,
		)

	def add(self, obj: MPData[T]) -> None:
		self.resources[obj.obj.path] = obj

	def add_many(self, mps: Iterable[Tuple[Path, MPData[T]]]):
		"""Add an iterable of MP to this Tresource"""
		self.resources.update(dict(mps))

	def subs(self) -> FrozenSet[PathSubscription]:
		return frozenset(obj.obj.sub for obj in self.resources.values())

	def rgs_flat(self) -> FrozenSet[PathResourceGroup]:
		"""All resource groups that any resource is contained by"""

		def extract_rg(res: AzObj) -> Optional[PathResourceGroup]:
			if isinstance(res, Resource) or isinstance(res, SubResource):
				return res.rg
			if isinstance(res, ResourceGroup):
				return res.path
			return None

		return frozenset(filter(None, set(extract_rg(res.obj) for res in self.resources.values())))

	@property
	def res(self):
		"""Resources in this Tresource"""
		return self.resources

	def res_flat(self) -> FrozenSet[Union[PathResource, PathSubResource]]:
		"""All Resources and SubResources"""
		return frozenset(path for path, node in self.resources.items() if isinstance(node.obj, Resource) or isinstance(node.obj, SubResource))

	def where_parent(self, obj: AzObj) -> TresourceMPData:
		"""Return all objects with this as a parent"""
		return self.where(obj.path)

	def where(self, parent_path: Path) -> TresourceMPData:
		"""
		Return all objects with this as the start of their Resource ID
		Excludes a complete match. For example, `where("/subscriptions/0")` will not return the subscription itself.
		"""
		o = TresourceMPData({k: v for k, v in self.resources.items() if k.startswith(parent_path)})
		o.resources.pop(parent_path, None)  # remove complete match, if present
		return o

	def where_subscription(self, sub: Subscription) -> TresourceMPData:
		"""Return all objects with this Subscription as a parent"""
		return self.where(sub.path)

	def where_rg(self, rg: ResourceGroup) -> TresourceMPData:
		"""Return all objects with this ResourceGroup as a parent"""
		return self.where(rg.path)
