"""Tresources for Materialised Path resources"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Dict, Generic, Iterable, List, Optional, Set, Tuple, TypeVar, Union

from llamazure.rid.mp import MP, AzObj, Path, PathResource, PathResourceGroup, PathSubResource, PathSubscription, Resource, ResourceGroup, SubResource, Subscription
from llamazure.tresource.itresource import INode, ITresource, ITresourceData


@dataclass
class TresourceMP(ITresource[AzObj, Path]):
	"""Tresource implementation for materialised-path-based resources. It's not really a tree, since materialised-path is an alternative to using trees"""

	resources: Dict[Path, AzObj] = field(default_factory=dict)

	def add_single(self, obj: AzObj):
		"""Add an AzObj to this Tresource"""
		self.resources[obj.path] = obj

	def add_many(self, mps: Iterable[MP]):
		"""Add an iterable of MP to this Tresource"""
		self.resources.update(dict(mps))

	def subs(self):
		return set(obj.sub for obj in self.resources.values())

	def rgs_flat(self) -> Set[PathResourceGroup]:
		"""All resource groups that any resource is contained by"""

		def extract_rg(res: AzObj) -> Optional[PathResourceGroup]:
			if isinstance(res, Resource) or isinstance(res, SubResource):
				return res.rg
			if isinstance(res, ResourceGroup):
				return res.path
			return None

		return set(filter(None, set(extract_rg(res) for res in self.resources.values())))

	@property
	def res(self):
		return self.resources

	def res_flat(self) -> Set[Union[PathResource, PathSubResource]]:
		"""All Resources and SubResources"""
		return set(path for path, res in self.resources.items() if isinstance(res, Resource) or isinstance(res, SubResource))

	def where_parent(self, obj: AzObj) -> TresourceMP:
		"""Return all objects with this as a parent"""
		return self.where(obj.path)

	def where(self, parent_path: Path) -> TresourceMP:
		"""Return all objects with this as the start of their Resource ID"""
		return TresourceMP({k: v for k, v in self.resources.items() if k.startswith(parent_path)})

	def where_subscription(self, sub: Subscription) -> TresourceMP:
		"""Return all objects with this Subscription as a parent"""
		return self.where(sub.path)

	def where_rg(self, rg: ResourceGroup) -> TresourceMP:
		"""Return all objects with this ResourceGroup as a parent"""
		return self.where(rg.path)


T = TypeVar("T")


@dataclass
class MPData(INode[AzObj, T]):
	obj: AzObj
	data: Optional[T]


@dataclass
class TresourceMPData(ITresourceData[AzObj, MPData[T], Path]):
	"""
	Tresource implementation for materialised-path-based resources.
	It's not really a tree, since materialised-path is an alternative to using trees
	This one stores data, too.
	"""

	resources: Dict[Path, MPData[T]] = field(default_factory=dict)

	def add_single(self, obj: AzObj, data: T):
		"""Add an AzObj to this Tresource"""
		self.resources[obj.path] = MPData(
			obj,
			data,
		)

	def add_many(self, mps: Iterable[Tuple[Path, MPData[T]]]):
		"""Add an iterable of MP to this Tresource"""
		self.resources.update(dict(mps))

	def subs(self) -> Set[PathSubscription]:
		return set(obj.obj.sub for obj in self.resources.values())

	def rgs_flat(self) -> List[PathResourceGroup]:
		"""All resource groups that any resource is contained by"""

		def extract_rg(res: AzObj) -> Optional[PathResourceGroup]:
			if isinstance(res, Resource) or isinstance(res, SubResource):
				return res.rg
			if isinstance(res, ResourceGroup):
				return res.path
			return None

		return list(filter(None, set(extract_rg(res.obj) for res in self.resources.values())))

	@property
	def res(self):
		return self.resources

	def res_flat(self) -> Set[Union[PathResource, PathSubResource]]:
		"""All Resources and SubResources"""
		return set(path for path, res in self.resources.values() if isinstance(res.obj, Resource) or isinstance(res.obj, SubResource))

	def where_parent(self, obj: AzObj) -> TresourceMPData:
		"""Return all objects with this as a parent"""
		return self.where(obj.path)

	def where(self, parent_path: Path) -> TresourceMPData:
		"""Return all objects with this as the start of their Resource ID"""
		return TresourceMPData({k: v for k, v in self.resources.items() if k.startswith(parent_path)})

	def where_subscription(self, sub: Subscription) -> TresourceMPData:
		"""Return all objects with this Subscription as a parent"""
		return self.where(sub.path)

	def where_rg(self, rg: ResourceGroup) -> TresourceMPData:
		"""Return all objects with this ResourceGroup as a parent"""
		return self.where(rg.path)
