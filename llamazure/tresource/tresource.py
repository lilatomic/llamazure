"""Build a tree of Azure resources"""
from __future__ import annotations

import abc
from collections import defaultdict
from dataclasses import dataclass, field
from typing import DefaultDict, Dict, Generic, Iterable, List, Optional, Sequence, TypeVar, Union

from llamazure.rid.rid import AzObj, Resource, ResourceGroup, SubResource, Subscription, get_chain


def recursive_default_dict():
	"""A default dictionary where the default is a default dictionary where the default..."""
	return defaultdict(recursive_default_dict)


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

	def rgs_flat(self) -> List[ResourceGroup]:
		"""Get RGs as a flat list"""
		...

	@property
	@abc.abstractmethod
	def res(self):
		"""Return all resources as a tree"""
		...

	def res_flat(self) -> List[Union[Resource, SubResource]]:
		"""
		Return all resources flattened into a list,
		including resources that were implicitly added as a parent of another resource
		but excluding subscriptions and resource groups
		"""
		...


@dataclass
class Tresource(ITresource):
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
		return list(self.resources.keys())

	@property
	def rgs(self) -> Dict[Subscription, List[ResourceGroup]]:
		return {sub: list(rg for rg in rgs.keys() if isinstance(rg, ResourceGroup)) for sub, rgs in self.resources.items()}

	def rgs_flat(self) -> List[ResourceGroup]:

		return [rg for rgs in self.resources.values() for rg in rgs if isinstance(rg, ResourceGroup)]

	@property
	def res(self):
		return self.resources

	def res_flat(self):
		out = []

		def recurse_resources(res, children):
			out.append(res)
			if children:
				for child, subchildren in children.items():
					recurse_resources(child, subchildren)

		for rgs in self.resources.values():
			for rg, ress in rgs.items():
				if isinstance(rg, ResourceGroup):
					for res, children in ress.items():
						recurse_resources(res, children)
				else:  # actually a resource attached to the subscription directly
					recurse_resources(rg, ress)

		return out


T = TypeVar("T")


@dataclass
class Node(Generic[T]):
	"""Generic node in a TresourceData"""

	obj: AzObj
	data: Optional[T]
	children: Dict[str, Node[T]] = field(default_factory=dict)

	def add(self, slug: str, node: Node[T]):
		"""
		Add an arbitrary Node as a child with an arbitrary slug.
		You probably want `add_child`, which will compute the slug for you
		"""
		self.children[slug] = node

	def add_child_resource(self, res: AzObj, data: T = None):
		"""Create a Node for a resource and add it as a child of this Node"""
		self.children[res.slug()] = Node(res, data)

	def add_child(self, child: Node[T]):
		"""Add a child to this node"""
		self.children[Node.obj.slug()] = child

	def add_children(self, children: Iterable[Node[T]]):
		"""Add multiple children to this node"""
		for child in children:
			self.add_child(child)


@dataclass
class TresourceData(Generic[T], ITresource):
	"""A tree of Azure resources with data attached"""

	resources: Node[T] = field(default_factory=lambda: Node(None, None))  # type: ignore # This node is just to make recursion easier, we can contain its grossness

	def set_data(self, obj: AzObj, data: T):
		"""
		Create a node with data.
		Missing intermediate nodes are created with no data.
		"""
		self.set_data_chain(get_chain(obj), data)

	def set_data_chain(self, chain: Sequence[AzObj], data: T):
		"""
		Create a node with data at the end of a resource chain.
		Missing intermediate nodes are created with no data.
		"""
		ref = self.resources
		for i in chain:
			slug = i.slug()
			if i not in ref.children:
				ref.children[slug] = ref = Node(i, None)  # multiple assignment is done left-to-right
			else:
				ref = ref.children[slug]

		ref.data = data

	def add_node(self, node: Node[T]):
		"""
		Add a node to the tresource.
		Missing intermediate nodes are created with no data.
		"""
		self.add_node_chain(get_chain(node.obj)[:-1], node)  # need to remove the last element from the chain, since we add that as a node

	def add_node_chain(self, chain: Sequence[AzObj], node: Node[T]):
		"""
		Add a node at the end of a chain of resources.
		The chain should not contain the resource in the node
		Missing intermediate nodes are created with no data.
		"""
		ref = self.resources
		for i in chain:
			slug = i.slug()
			if i not in ref.children:
				ref.children[slug] = ref = Node(i, None)
			else:
				ref = ref.children[slug]

		ref.children[node.obj.slug()] = node

	@property
	def subs(self):
		return self.resources.children

	def rgs_flat(self) -> List[ResourceGroup]:
		rgs = []
		for sub in self.resources.children.values():
			for maybe_rg in sub.children.values():
				if isinstance(maybe_rg.obj, ResourceGroup):
					rgs.append(maybe_rg.obj)
		return rgs

	@property
	def res(self):
		return self.resources

	def res_flat(self):
		out: List[AzObj] = []

		def recurse_resource_node(res: Node[T]):
			out.append(res.obj)
			for child in res.children.values():
				recurse_resource_node(child)

		for sub in self.resources.children.values():
			for maybe_rg in sub.children.values():
				if isinstance(maybe_rg.obj, ResourceGroup):
					for res in maybe_rg.children.values():
						recurse_resource_node(res)
				else:
					recurse_resource_node(maybe_rg)

		return out
