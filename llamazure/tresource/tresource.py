"""Build a tree of Azure resources"""
from collections import defaultdict
from dataclasses import dataclass, field
from typing import DefaultDict, Dict

from llamazure.rid.rid import AzObj, ResourceGroup, Subscription

recursive_default_dict = lambda: defaultdict(recursive_default_dict)


@dataclass
class Tresource:
	"""A tree of Azure resources"""

	resources: DefaultDict[Subscription, Dict] = field(default_factory=recursive_default_dict)

	def add(self, obj: AzObj):
		"""Add a resource to the tree"""
		if isinstance(obj, Subscription):
			self.resources[obj].update()
		if isinstance(obj, ResourceGroup):
			self.resources[obj.sub][obj].update()

	@property
	def subs(self):
		"""Get subscriptions"""
		return list(self.resources.keys())

	@property
	def rgs(self):
		"""
		Get RGs nested by subscription
		"""
		return {sub: list(rgs.keys()) for sub, rgs in self.resources.items()}

	@property
	def rgs_flat(self):
		return [rg for rgs in self.resources.values() for rg in rgs]
