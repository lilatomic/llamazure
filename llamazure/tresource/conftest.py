import abc
from typing import List, NewType, Type, TypeVar, Union

from hypothesis import given
from hypothesis.strategies import lists

from llamazure.rid import rid
from llamazure.rid.conftest import st_resource_any, st_resource_base, st_resource_complex, st_rg, st_subscription
from llamazure.rid.rid import AzObj, Resource, ResourceGroup, SubResource, parse_chain, serialise
from llamazure.tresource.itresource import AzObjT, ITresourceData
from llamazure.tresource.tresource import Node, Tresource, TresourceData


class ABCTestBuildDataTree(abc.ABC):
	"""Test building a TresourceData"""

	@property
	@abc.abstractmethod
	def clz(self) -> Type[ITresourceData]:
		...

	@abc.abstractmethod
	def conv(self, obj: rid.AzObj) -> AzObjT:
		...

	@given(lists(st_subscription))
	def test_build_subscriptions(self, subs):
		"""Test adding only subscriptions"""
		tree = self.clz()

		for sub in subs:
			tree.set_data(sub, hash(sub))

		assert len(set(tree.subs())) == len(subs)
		assert tree.subs() == set(subs)

	@given(lists(st_rg))
	def test_build_rgs(self, rgs: List[ResourceGroup]):
		"""Test adding only RGs"""
		tree: ITresourceData[int] = self.clz()

		subs = set()

		for rg in rgs:
			subs.add(rg.sub)
			tree.set_data(rg, hash(rg))

		assert subs == tree.subs()
		assert set(rgs) == set(tree.rgs_flat())

	@given(lists(st_resource_base))
	def test_build_simple_resources(self, ress: List[Resource]):
		tree: ITresourceData[int] = self.clz()

		subs = set()
		rgs = set()

		for res in ress:
			subs.add(res.sub)
			if res.rg:
				rgs.add(res.rg)
			tree.set_data(res, hash(res))

		assert subs == tree.subs()
		assert rgs == set(tree.rgs_flat())
		# since there is no nesting, there are no implicit resources, and this comparison is valid
		assert set(ress) == set(tree.res_flat())

	@given(lists(st_resource_complex))
	def test_build_complex_resources(self, ress: List[Union[Resource, SubResource]]):
		tree: ITresourceData[int] = self.clz()

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
			tree.set_data(res, hash(res))

		assert subs == tree.subs()
		assert rgs == set(tree.rgs_flat())
		# since there is nesting, there are implicit resources, and there will be more
		assert resources == set(tree.res_flat())
