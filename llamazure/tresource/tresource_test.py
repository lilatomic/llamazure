"""Test Tresource"""
from typing import List, Type, Union

from hypothesis import given
from hypothesis.strategies import lists

from llamazure.rid import rid
from llamazure.rid.conftest import st_resource_any, st_resource_base, st_resource_complex, st_rg, st_subscription
from llamazure.rid.rid import AzObj, Resource, ResourceGroup, SubResource, parse_chain, serialise
from llamazure.tresource.conftest import ABCTestBuildDataTree
from llamazure.tresource.itresource import AzObjT, ObjReprT
from llamazure.tresource.tresource import Node, Tresource, TresourceData


class TestBuildTree:
	"""Test that building a tree is correct and seamless"""

	@given(lists(st_subscription))
	def test_build_subscriptions(self, subs):
		"""Test adding only subscriptions"""
		tree = Tresource()

		for sub in subs:
			tree.add(sub)

		assert len(tree.subs()) == len(subs)

	@given(lists(st_rg))
	def test_build_rgs(self, rgs: List[ResourceGroup]):
		"""Test adding only RGs"""
		tree = Tresource()

		subs = set()

		for rg in rgs:
			subs.add(rg.sub)
			tree.add(rg)

		assert subs == tree.subs()
		assert set(rgs) == set(tree.rgs_flat())

	@given(lists(st_resource_base))
	def test_build_simple_resources(self, ress: List[Resource]):
		tree = Tresource()

		subs = set()
		rgs = set()

		for res in ress:
			subs.add(res.sub)
			if res.rg:
				rgs.add(res.rg)
			tree.add(res)

		assert subs == tree.subs()
		assert rgs == set(tree.rgs_flat())
		# since there is no nesting, there are no implicit resources, and this comparison is valid
		assert set(ress) == set(tree.res_flat())

	@given(lists(st_resource_complex))
	def test_build_complex_resources(self, ress: List[Union[Resource, SubResource]]):
		tree = Tresource()

		subs = set()
		rgs = set()
		resources = set()

		def recurse_register(resource):
			resources.add(resource)
			if resource.parent:
				recurse_register(resource.parent)

		for res in ress:
			subs.add(res.sub)
			if res.rg:
				rgs.add(res.rg)
			recurse_register(res)
			tree.add(res)

		assert subs == tree.subs()
		assert rgs == set(tree.rgs_flat())
		# since there is nesting, there are implicit resources, and there will be more
		assert resources == set(tree.res_flat())


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


class TestBuildDataTree(ABCTestBuildDataTree):
	"""Test building a TresourceData"""

	@property
	def clz(self) -> Type:
		return TresourceData

	def conv(self, obj: rid.AzObj) -> AzObjT:
		return obj

	def recover(self, repr: ObjReprT) -> rid.AzObj:
		return repr

	@property
	def recurse_implicit(self) -> bool:
		return True


class TestNodesDataTree:
	"""Test building a TresourceData with add_node"""

	@given(lists(st_resource_complex))
	def test_build_complex_resources(self, ress: List[Union[Resource, SubResource]]):
		tree: TresourceData[int] = TresourceData()
		verifier: TresourceData[int] = TresourceData()

		for res in ress:
			data = hash(res)
			tree.add_node(Node(res, data))
			verifier.set_data(res, data)

		assert verifier.res_flat() == tree.res_flat()
