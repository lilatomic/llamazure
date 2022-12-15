from typing import Generic, List, Protocol, Set, TypeVar

AzObjT = TypeVar("AzObjT")
DataT = TypeVar("DataT")
ObjReprT = TypeVar("ObjReprT")


class ITresource(Protocol[AzObjT, ObjReprT]):
	"""Generic interface for all Tresources"""

	def subs(self) -> Set[ObjReprT]:
		"""Return all subscriptions that contain resources in this tresource"""
		...

	def rgs_flat(self) -> Set[ObjReprT]:
		"""Return all resource groups that contain resources in this tresource"""
		...

	def res_flat(self) -> Set[ObjReprT]:
		"""Resturn all explicit resources in this tresource"""
		...


class INode(Protocol[AzObjT, DataT]):
	obj: AzObjT
	data: DataT


NodeT = TypeVar("NodeT", bound=INode)


class ITresourceData(ITresource[AzObjT, ObjReprT], Protocol[AzObjT, NodeT, ObjReprT]):
	"""Generic interface for a TresourceData"""

	def set_data(self, obj: AzObjT, data: DataT):
		...
