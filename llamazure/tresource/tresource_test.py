"""Test Tresource"""

from typing import List, Type, Union

from hypothesis import given
from hypothesis.strategies import lists

from llamazure.rid import rid
from llamazure.rid.conftest import st_resource_any, st_resource_complex
from llamazure.rid.rid import AzObj, Resource, SubResource, parse_chain, serialise
from llamazure.tresource.conftest import ABCTestBuildTree, TreeImplSpec
from llamazure.tresource.itresource import ITresource
from llamazure.tresource.tresource import Node, T, Tresource, TresourceData


class TreeImpl(TreeImplSpec[AzObj, AzObj, AzObj]):
	"""Test that building a tree is correct and seamless"""

	@property
	def clz(self) -> Type[ITresource]:
		return Tresource

	def conv(self, obj: rid.AzObj) -> AzObj:
		return obj

	def recover(self, obj_repr: AzObj) -> rid.AzObj:
		return obj_repr

	@property
	def recurse_implicit(self) -> bool:
		return True


class TestBuildTree(ABCTestBuildTree):
	"""Test that building a tree is correct and seamless"""

	@property
	def impl(self) -> TreeImplSpec:
		return TreeImpl()


class TestBuildTreeFromChain:
	"""Test that adding from chain is the same as adding from a terminal AzObj"""

	@given(lists(st_resource_any))
	def test_chain_and_normal_are_equivalent(self, ress: List[AzObj]):
		single_tree = Tresource()
		for res in ress:
			single_tree.add(res)

		chains = [parse_chain(serialise(res)) for res in ress]
		chain_tree = Tresource()
		for chain in chains:
			chain_tree.add_chain(chain)

		assert single_tree.resources == chain_tree.resources


class DataTreeImpl(TreeImplSpec[AzObj, Node[T], AzObj]):
	"""Test building a TresourceData"""

	@property
	def clz(self) -> Type:
		return TresourceData

	def conv(self, obj: rid.AzObj) -> AzObj:
		return obj

	def recover(self, obj_repr: AzObj) -> rid.AzObj:
		return obj_repr

	@property
	def recurse_implicit(self) -> bool:
		return True


class TestBuildDataTree(ABCTestBuildTree):
	"""Test building a TresourceData"""

	@property
	def impl(self) -> TreeImplSpec:
		return DataTreeImpl()


class TestNodesDataTree:
	"""Test building a TresourceData with add_node"""

	@given(lists(st_resource_complex))
	def test_build_complex_resources(self, ress: List[Union[Resource, SubResource]]):
		tree: TresourceData[int] = TresourceData()
		verifier: TresourceData[int] = TresourceData()

		for res in ress:
			data = hash(res)
			tree.add(Node(res, data))
			verifier.set_data(res, data)

		assert verifier.res_flat() == tree.res_flat()
