"""Build a tree of Azure resources"""
from collections import defaultdict
from dataclasses import dataclass, field
from typing import DefaultDict, Dict, List

from llamazure.rid.rid import AzObj, Resource, ResourceGroup, SubResource, Subscription


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
			# Adding a Resource or SubResource requires us to add all parents
			# The llamazure.rid makes it very easy to trace backwards,
			# and that adds complexity here
			inv_path = [obj]
			r = obj
			while r.parent:
				inv_path.append(r.parent)
				r = r.parent

			def mut_recurse(d, parts):
				if parts:
					part = parts.pop()
					mut_recurse(d[part], parts)

			mut_recurse(self.resources, inv_path + [obj.rg, obj.sub])

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
