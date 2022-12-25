"""Test helpers for Tresource"""
import abc
from typing import FrozenSet, Generic, List, Set, Type, Union

from hypothesis import given
from hypothesis.strategies import lists

from llamazure.rid import rid
from llamazure.rid.conftest import st_resource_base, st_resource_complex, st_rg, st_subscription
from llamazure.rid.rid import Resource, ResourceGroup, SubResource
from llamazure.tresource.itresource import AzObjT, DataT, ITresource, ITresourceData, ObjReprT, ObjT


class TreeImplSpec(Generic[AzObjT, ObjT, ObjReprT], abc.ABC):
	"""Information on an implementation of ITresource"""

	@property
	@abc.abstractmethod
	def clz(self) -> Type[ITresource]:
		"""Class of the Tresource to test"""
		...

	@abc.abstractmethod
	def conv(self, obj: rid.AzObj) -> AzObjT:
		"""Convert a rid.AzObj into your AzObjT"""
		...

	@abc.abstractmethod
	def recover(self, obj_repr: ObjReprT) -> rid.AzObj:
		"""Convert one of your AzObjT into a rid.AzObj"""
		...

	@property
	@abc.abstractmethod
	def recurse_implicit(self) -> bool:
		"""
		Whether implicit resources should be verified in the output
		Implicit resources are resources which are parents of a resource which was added
		For example, if a lock on a VNet is added:
			- a value of `True` would request us to verify that the VNet and the Lock have been added
			- a value of `False` would request us to verify that only the Lock has been added
		"""
		...

	def recover_many(self, objs: FrozenSet[ObjReprT]) -> Set[rid.AzObj]:
		"""Vectorised `recover`"""
		return set(self.recover(x) for x in objs)

	@staticmethod
	def add_to_tree(tree: ITresource, obj: AzObjT, data: DataT):
		if isinstance(tree, ITresourceData):
			tree.set_data(obj, data)
		else:
			tree.add(obj)


class ABCTestBuildTree(abc.ABC):
	"""Test building a TresourceData"""

	@property
	@abc.abstractmethod
	def impl(self) -> TreeImplSpec:
		"""The implementation of this tresource"""
		...

	@given(lists(st_subscription))
	def test_build_subscriptions(self, subs):
		"""Test adding only subscriptions"""
		tree = self.impl.clz()

		for sub in subs:
			self.impl.add_to_tree(tree, self.impl.conv(sub), hash(sub))

		assert len(set(tree.subs())) == len(subs)
		assert self.impl.recover_many(tree.subs()) == set(subs)

	@given(lists(st_rg))
	def test_build_rgs(self, rgs: List[ResourceGroup]):
		"""Test adding only RGs"""
		tree: ITresource = self.impl.clz()

		subs = set()

		for rg in rgs:
			subs.add(rg.sub)
			self.impl.add_to_tree(tree, self.impl.conv(rg), hash(rg))

		assert set(subs) == self.impl.recover_many(tree.subs())
		assert set(rgs) == self.impl.recover_many(tree.rgs_flat())

	@given(lists(st_resource_base))
	def test_build_simple_resources(self, ress: List[Resource]):
		"""Test building a Tresource of simple resources"""
		tree: ITresource = self.impl.clz()

		subs = set()
		rgs = set()

		for res in ress:
			subs.add(res.sub)
			if res.rg:
				rgs.add(res.rg)
			self.impl.add_to_tree(tree, self.impl.conv(res), hash(res))

		assert set(subs) == self.impl.recover_many(tree.subs())
		assert set(rgs) == self.impl.recover_many(tree.rgs_flat())
		# since there is no nesting, there are no implicit resources, and this comparison is valid
		assert set(ress) == self.impl.recover_many(tree.res_flat())

	@given(lists(st_resource_complex))
	def test_build_complex_resources(self, ress: List[Union[Resource, SubResource]]):
		"""Test building a Tresource of complex resources with parents"""
		tree: ITresource = self.impl.clz()

		subs = set()
		rgs = set()
		resources = set()

		def recurse_register(resource):
			resources.add(resource)
			if self.impl.recurse_implicit and resource.parent:
				recurse_register(resource.parent)

		for res in ress:
			subs.add(res.sub)
			if res.rg:
				rgs.add(res.rg)
			recurse_register(res)
			self.impl.add_to_tree(tree, self.impl.conv(res), hash(res))

		assert set(subs) == self.impl.recover_many(tree.subs())
		assert set(rgs) == self.impl.recover_many(tree.rgs_flat())
		# since there is nesting, there are implicit resources, and there will be more
		assert set(resources) == self.impl.recover_many(tree.res_flat())


class ABCTestQuery(abc.ABC):
	"""
	Test querying functions of a Tresource
	# TODO: doesn't distinguish if impl.recurse_implicit
	"""

	@property
	@abc.abstractmethod
	def impl(self) -> TreeImplSpec:
		"""The implementation of this tresource"""
		...

	def test_query_tresource(self):
		"""Test that the query functions return things they are supposed to"""
		tree: ITresource = self.impl.clz()

		target_rid = "/subscriptions/s0/resourceGroups/r0/providers/p0/t0/n0/providers/p_l0/t_l0/n_l0"
		other_resource_rid = target_rid.replace("n0", "n1")
		other_rg_rid = target_rid.replace("r0", "r1")
		other_sub_rid = target_rid.replace("s0", "s1")

		target = rid.parse_chain(target_rid)
		other_resource = rid.parse_chain(other_resource_rid)
		other_rg = rid.parse_chain(other_rg_rid)
		other_sub = rid.parse_chain(other_sub_rid)

		for obj in [target, other_resource, other_rg, other_sub]:
			self.impl.add_to_tree(tree, self.impl.conv(obj[-1]), hash(obj))

		assert self.impl.recover_many(tree.where_subscription(self.impl.conv(other_sub[0])).subs()) == {other_sub[0]}
		assert len(tree.where_subscription(self.impl.conv(target[0])).res_flat()) == 3

		idx_rg = 1
		assert self.impl.recover_many(tree.where_rg(self.impl.conv(other_rg[idx_rg])).rgs_flat()) == {other_rg[1]}
		assert len(tree.where_rg(self.impl.conv(target[idx_rg])).res_flat()) == 2

		idx_parent = -2
		assert self.impl.recover_many(tree.where_parent(self.impl.conv(other_resource[idx_parent])).res_flat()) == {other_resource[-1]}
		assert len(tree.where_parent(self.impl.conv(target[idx_parent])).res_flat()) == 1

	def test_query_excludes_parent(self):
		"""Tests that the query methods exclude the resoure requested in the `where`"""
		tree: ITresource = self.impl.clz()

		target_rid = "/subscriptions/s0/resourceGroups/r0/providers/p0/t0/n0/providers/p_l0/t_l0/n_l0"
		target = rid.parse_chain(target_rid)

		for obj in [target[0], target[-1]]:
			self.impl.add_to_tree(tree, self.impl.conv(obj), hash(obj))

		assert self.impl.recover_many(tree.where_subscription(self.impl.conv(target[0])).res.keys()) == {target[-1]}
