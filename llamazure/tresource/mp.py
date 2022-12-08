"""Tresources for Materialised Path resources"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Union

from llamazure.rid.mp import MP, AzObj, Path, PathResourceGroup, Resource, ResourceGroup, SubResource, Subscription


class ITresource(abc.ABC):
	"""Common interface to output resources from all Tresources"""

	@property
	@abc.abstractmethod
	def subs(self):
		"""Get subscriptions"""
		...

	# @property
	# @abc.abstractmethod
	# def rgs(self):
	# 	"""Get RGs nested by subscription"""
	# 	...

	@abc.abstractmethod
	def rgs_flat(self) -> List[PathResourceGroup]:
		"""Get RGs as a flat list"""
		...

	@property
	@abc.abstractmethod
	def res(self):
		"""Return all resources as a tree"""
		...

	@abc.abstractmethod
	def res_flat(self) -> List[Union[Resource, SubResource]]:
		"""
		Return all resources flattened into a list,
		including resources that were implicitly added as a parent of another resource
		but excluding subscriptions and resource groups
		"""
		...


@dataclass
class TresourceMP(ITresource):
	"""Tresource implementation for materialised-path-based resources. It's not really a tree, since materialised-path is an alternative to using trees"""

	resources: Dict[Path, AzObj] = field(default_factory=dict)

	def add_single(self, obj: AzObj):
		"""Add an AzObj to this Tresource"""
		self.resources[obj.path] = obj

	def add_many(self, mps: Iterable[MP]):
		"""Add an iterable of MP to this Tresource"""
		self.resources.update(dict(mps))

	@property
	def subs(self):
		return list(set(obj.sub for obj in self.resources.values()))

	def rgs_flat(self) -> List[PathResourceGroup]:
		"""All resource groups that any resource is contained by"""

		def extract_rg(res: AzObj) -> Optional[PathResourceGroup]:
			if isinstance(res, Resource) or isinstance(res, SubResource):
				return res.rg
			if isinstance(res, ResourceGroup):
				return res.path
			return None

		return list(filter(None, set(extract_rg(res) for res in self.resources.values())))

	@property
	def res(self):
		return self.resources

	def res_flat(self) -> List[Union[Resource, SubResource]]:
		"""All Resources and SubResources"""
		return list(res for res in self.resources.values() if isinstance(res, Resource) or isinstance(res, SubResource))

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
