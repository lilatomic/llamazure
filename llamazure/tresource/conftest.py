"""Test helpers for Tresource"""
import abc
from typing import FrozenSet, Generic, List, Set, Type, Union

from hypothesis import given
from hypothesis.strategies import lists

from llamazure.rid import rid
from llamazure.rid.conftest import st_resource_base, st_resource_complex, st_rg, st_subscription
from llamazure.rid.rid import Resource, ResourceGroup, SubResource
from llamazure.tresource.itresource import AzObjT, DataT, ITresource, ITresourceData, ObjReprT


class ABCTestBuildTree(Generic[AzObjT, ObjReprT], abc.ABC):
	"""Test building a TresourceData"""

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

	def _recover_many(self, objs: FrozenSet[ObjReprT]) -> Set[rid.AzObj]:
		"""Vectorised `recover`"""
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

	def add_to_tree(self, tree: ITresource, obj: AzObjT, data: DataT):
		if isinstance(tree, ITresourceData):
			tree.set_data(obj, data)
		else:
			tree.add(obj)

	@given(lists(st_subscription))
	def test_build_subscriptions(self, subs):
		"""Test adding only subscriptions"""
		tree = self.clz()

		for sub in subs:
			self.add_to_tree(tree, self.conv(sub), hash(sub))

		assert len(set(tree.subs())) == len(subs)
		assert self._recover_many(tree.subs()) == set(subs)

	@given(lists(st_rg))
	def test_build_rgs(self, rgs: List[ResourceGroup]):
		"""Test adding only RGs"""
		tree: ITresource = self.clz()

		subs = set()

		for rg in rgs:
			subs.add(rg.sub)
			self.add_to_tree(tree, self.conv(rg), hash(rg))

		assert set(subs) == self._recover_many(tree.subs())
		assert set(rgs) == self._recover_many(tree.rgs_flat())

	@given(lists(st_resource_base))
	def test_build_simple_resources(self, ress: List[Resource]):
		"""Test building a Tresource of simple resources"""
		tree: ITresource = self.clz()

		subs = set()
		rgs = set()

		for res in ress:
			subs.add(res.sub)
			if res.rg:
				rgs.add(res.rg)
			self.add_to_tree(tree, self.conv(res), hash(res))

		assert set(subs) == self._recover_many(tree.subs())
		assert set(rgs) == self._recover_many(tree.rgs_flat())
		# since there is no nesting, there are no implicit resources, and this comparison is valid
		assert set(ress) == self._recover_many(tree.res_flat())

	@given(lists(st_resource_complex))
	def test_build_complex_resources(self, ress: List[Union[Resource, SubResource]]):
		"""Test building a Tresource of complex resources with parents"""
		tree: ITresource = self.clz()

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
			self.add_to_tree(tree, self.conv(res), hash(res))

		assert set(subs) == self._recover_many(tree.subs())
		assert set(rgs) == self._recover_many(tree.rgs_flat())
		# since there is nesting, there are implicit resources, and there will be more
		assert set(resources) == self._recover_many(tree.res_flat())
