"""Test TresourceMP"""
from typing import Type

from llamazure.rid import conv, rid
from llamazure.rid.mp import AzObj, Path
from llamazure.tresource.conftest import ABCTestBuildTree, ABCTestQuery, TreeImplSpec
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


class TestQueryMP(ABCTestQuery):
	"""Test querying on MP Tresource"""

	@property
	def impl(self) -> TreeImplSpec:
		return TreeMPImpl()


class TestQueryMPData(ABCTestQuery):
	"""Test querying on MP Data Tresource"""

	@property
	def impl(self) -> TreeImplSpec:
		return TreeMPDataImpl()
