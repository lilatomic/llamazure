"""Test TresourceMP"""
from typing import Type

from llamazure.rid import conv, mp, rid
from llamazure.rid.mp import AzObj, Path, Resource, ResourceGroup, Subscription, narrow_assert
from llamazure.tresource.conftest import ABCTestBuildTree, TreeImplSpec
from llamazure.tresource.mp import TresourceMP, TresourceMPData


class TreeMPImpl(TreeImplSpec[AzObj, AzObj, Path]):
	"""Test that building the tree is correct and seamless"""

	@property
	def clz(self) -> Type:
		return TresourceMP

	def conv(self, obj: rid.AzObj) -> AzObj:
		return conv.rid2mp(obj)

	def recover(self, obj_repr: Path) -> rid.AzObj:
		return rid.parse(obj_repr)

	@property
	def recurse_implicit(self) -> bool:
		return False


class TestBuildTreeMP(ABCTestBuildTree):
	@property
	def impl(self) -> TreeImplSpec:
		return TreeMPImpl()


class TreeMPDataImpl(TreeImplSpec):
	"""Test building a TresourceData"""

	@property
	def clz(self) -> Type:
		return TresourceMPData

	def conv(self, obj: rid.AzObj) -> AzObj:
		return conv.rid2mp(obj)

	def recover(self, obj_repr: Path) -> rid.AzObj:
		return rid.parse(obj_repr)

	@property
	def recurse_implicit(self) -> bool:
		return False


class TestBuildTreeMPData(ABCTestBuildTree):
	"""Test building a TresourceData"""

	@property
	def impl(self) -> TreeImplSpec:
		return TreeMPDataImpl()


class TestQuery:
	def test_query_tresourcemp(self):
		tree = TresourceMP()

		target_rid = "/subscriptions/s0/resourceGroups/r0/providers/p0/t0/n0"
		target = mp.parse_chain(target_rid)
		other_resource = mp.parse_chain(target_rid.replace("n0", "n1"))
		other_rg = mp.parse_chain(target_rid.replace("r0", "r1"))
		other_sub = mp.parse_chain(target_rid.replace("s0", "s1"))

		all_cases = [target, other_resource, other_rg, other_sub]
		for obj in all_cases:
			tree.add(obj[-1][1])

		assert tree.where_subscription(narrow_assert(other_sub[0][1], Subscription)).subs() == frozenset((other_sub[0][0],))
		assert len(tree.where_subscription(narrow_assert(target[0][1], Subscription)).res_flat()) == 3

		assert tree.where_rg(narrow_assert(other_rg[1][1], ResourceGroup)).rgs_flat() == frozenset((other_rg[1][0],))
		assert len(tree.where_rg(narrow_assert(target[1][1], ResourceGroup)).res_flat()) == 2

		assert tree.where_parent(narrow_assert(other_resource[-1][1], Resource)).res_flat() == frozenset((other_resource[-1][0],))
		assert len(tree.where_parent(narrow_assert(target[-1][1], Resource)).res_flat()) == 1

		assert tree.where(target[-1][0]).res_flat() == frozenset((target[-1][0],))
