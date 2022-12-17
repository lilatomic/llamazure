"""Test TresourceMP"""
from typing import Type

from llamazure.rid import conv, rid
from llamazure.rid.mp import AzObj, Path
from llamazure.tresource.conftest import ABCTestBuildTree
from llamazure.tresource.itresource import AzObjT, ObjReprT
from llamazure.tresource.mp import TresourceMP, TresourceMPData


class TestBuildTreeMP(ABCTestBuildTree):
	"""Test that building the tree is correct and seamless"""

	@property
	def clz(self) -> Type:
		return TresourceMP

	def conv(self, obj: rid.AzObj) -> AzObjT:
		return conv.rid2mp(obj)

	def recover(self, obj_repr: ObjReprT) -> rid.AzObj:
		return rid.parse(obj_repr)

	@property
	def recurse_implicit(self) -> bool:
		return False


class TestBuildTreeMPData(ABCTestBuildTree):
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
