from abc import ABC, abstractmethod
from typing import Generic, List, Protocol, Set, TypeVar

AzObjT = TypeVar("AzObjT")
DataT = TypeVar("DataT")
ObjReprT = TypeVar("ObjReprT")


class ITresource(Generic[AzObjT, ObjReprT], ABC):
	"""Generic interface for all Tresources"""

	@abstractmethod
	def subs(self) -> Set[ObjReprT]:
		"""Return all subscriptions that contain resources in this tresource"""
		...

	@abstractmethod
	def rgs_flat(self) -> Set[ObjReprT]:
		"""Return all resource groups that contain resources in this tresource"""
		...

	@abstractmethod
	def res_flat(self) -> Set[ObjReprT]:
		"""Resturn all explicit resources in this tresource"""
		...


class INode(Protocol[AzObjT, DataT]):
	obj: AzObjT
	data: DataT


NodeT = TypeVar("NodeT", bound=INode)


class ITresourceData(Generic[AzObjT, NodeT, ObjReprT], ITresource[AzObjT, ObjReprT]):
	"""Generic interface for a TresourceData"""

	@abstractmethod
	def set_data(self, obj: AzObjT, data: DataT):
		...
