"""Tresources for Materialised Path resources"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Union

from llamazure.rid.mp import MP, AzObj, Path, PathResourceGroup, Resource, ResourceGroup, SubResource, Subscription
from llamazure.tresource.tresource import ITresource


@dataclass
class TresourceMP(ITresource):

	resources: Dict[Path, AzObj] = field(default_factory=dict)

	def add_single(self, obj: AzObj):
		self.resources[obj.path] = obj

	def add_many(self, mps: Iterable[MP]):
		self.resources.update(dict(mps))

	@property
	def subs(self):
		return list(set(obj.sub for obj in self.resources.values()))

	def rgs_flat(self) -> List[PathResourceGroup]:
		def extract_rg(res: AzObj) -> Optional[PathResourceGroup]:
			if isinstance(res, Resource) or isinstance(res, SubResource):
				return res.rg
			if isinstance(res, ResourceGroup):
				return res.path
			return None

		return list(set(extract_rg(res) for res in self.resources.values()) - {None})

	@property
	def res(self):
		return self.resources

	def res_flat(self) -> List[Union[Resource, SubResource]]:
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
