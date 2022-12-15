import abc
from typing import List, Set, Type, Union

from hypothesis import given
from hypothesis.strategies import lists

from llamazure.rid import rid
from llamazure.rid.conftest import st_resource_base, st_resource_complex, st_rg, st_subscription
from llamazure.rid.rid import Resource, ResourceGroup, SubResource
from llamazure.tresource.itresource import AzObjT, ITresourceData, ObjReprT


class ABCTestBuildDataTree(abc.ABC):
	"""Test building a TresourceData"""

	@property
	@abc.abstractmethod
	def clz(self) -> Type[ITresourceData]:
		...

	@abc.abstractmethod
	def conv(self, obj: rid.AzObj) -> AzObjT:
		...

	@abc.abstractmethod
	def recover(self, repr: ObjReprT) -> rid.AzObj:
		...

	def _recover_many(self, objs: Set[ObjReprT]) -> Set[rid.AzObj]:
		return set(self.recover(x) for x in objs)

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

	@given(lists(st_subscription))
	def test_build_subscriptions(self, subs):
		"""Test adding only subscriptions"""
		tree = self.clz()

		for sub in subs:
			tree.set_data(self.conv(sub), hash(sub))

		assert len(set(tree.subs())) == len(subs)
		assert self._recover_many(tree.subs()) == set(subs)

	@given(lists(st_rg))
	def test_build_rgs(self, rgs: List[ResourceGroup]):
		"""Test adding only RGs"""
		tree: ITresourceData[int] = self.clz()

		subs = set()

		for rg in rgs:
			subs.add(rg.sub)
			tree.set_data(self.conv(rg), hash(rg))

		assert set(subs) == self._recover_many(tree.subs())
		assert set(rgs) == self._recover_many(tree.rgs_flat())

	@given(lists(st_resource_base))
	def test_build_simple_resources(self, ress: List[Resource]):
		tree: ITresourceData[int] = self.clz()

		subs = set()
		rgs = set()

		for res in ress:
			subs.add(res.sub)
			if res.rg:
				rgs.add(res.rg)
			tree.set_data(self.conv(res), hash(res))

		assert set(subs) == self._recover_many(tree.subs())
		assert set(rgs) == self._recover_many(tree.rgs_flat())
		# since there is no nesting, there are no implicit resources, and this comparison is valid
		assert set(ress) == self._recover_many(tree.res_flat())

	@given(lists(st_resource_complex))
	def test_build_complex_resources(self, ress: List[Union[Resource, SubResource]]):
		tree: ITresourceData[int] = self.clz()

		subs = set()
		rgs = set()
		resources = set()

		def recurse_register(resource):
			resources.add(resource)
			if self.recurse_implicit and resource.parent:
				recurse_register(resource.parent)

		for res in ress:
			subs.add(res.sub)
			if res.rg:
				rgs.add(res.rg)
			recurse_register(res)
			tree.set_data(self.conv(res), hash(res))

		assert set(subs) == self._recover_many(tree.subs())
		assert set(rgs) == self._recover_many(tree.rgs_flat())
		# since there is nesting, there are implicit resources, and there will be more
		assert set(resources) == self._recover_many(tree.res_flat())
