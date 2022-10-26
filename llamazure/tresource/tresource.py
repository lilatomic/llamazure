"""Build a tree of Azure resources"""
from collections import defaultdict
from dataclasses import dataclass, field
from typing import DefaultDict, Dict, List, Sequence

from llamazure.rid.rid import AzObj, Resource, ResourceGroup, SubResource, Subscription, get_chain


def recursive_default_dict():
	return defaultdict(recursive_default_dict)


@dataclass
class Tresource:
	"""A tree of Azure resources"""

	resources: DefaultDict[Subscription, Dict] = field(default_factory=recursive_default_dict)

	def add(self, obj: AzObj):
		"""Add a resource to the tree"""
		if isinstance(obj, Subscription):
			self.resources[obj].update()
		elif isinstance(obj, ResourceGroup):
			self.resources[obj.sub][obj].update()
		elif isinstance(obj, Resource) or isinstance(obj, SubResource):
			self.add_chain(get_chain(obj))

	def add_chain(self, chain: Sequence[AzObj]):
		"""
		Add a chain of resources.
		This method is higher performance but assumes a valid resource chain.
		Fortunately, you can easily get a valid resurce chain with the `parse_chain` method.
		"""
		ref: Dict = self.resources
		for i in chain:
			ref = ref[i]

	@property
	def subs(self):
		"""Get subscriptions"""
		return list(self.resources.keys())

	@property
	def rgs(self) -> Dict[Subscription, List[ResourceGroup]]:
		"""
		Get RGs nested by subscription
		"""
		return {sub: list(rgs.keys()) for sub, rgs in self.resources.items()}

	def rgs_flat(self) -> List[ResourceGroup]:
		"""
		Get RGs as a flat list
		"""
		return [rg for rgs in self.resources.values() for rg in rgs]

	@property
	def res(self):
		return self.resources

	def res_flat(self):
		"""
		Return all resources flattened into a list,
		including resources that were implicitly added as a parent of another resource
		"""
		out = []

		def recurse_resources(res, children):
			out.append(res)
			if children:
				for child, subchildren in children.items():
					recurse_resources(child, subchildren)

		for rgs in self.resources.values():
			for ress in rgs.values():
				for res, children in ress.items():
					recurse_resources(res, children)

		return out
