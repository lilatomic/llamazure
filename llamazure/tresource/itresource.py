"""Interface definitions for Tresources"""
from abc import ABC, abstractmethod
from typing import FrozenSet, Generic, Optional, TypeVar

AzObjT = TypeVar("AzObjT")  # Your AzObj type
ObjReprT = TypeVar("ObjReprT")  # The type that your tresource uses to represent resources for membership


class ITresource(Generic[AzObjT, ObjReprT], ABC):
	"""Generic interface for all Tresources"""

	@abstractmethod
	def subs(self) -> FrozenSet[ObjReprT]:
		"""Return all subscriptions that contain resources in this tresource"""
		...

	@abstractmethod
	def rgs_flat(self) -> FrozenSet[ObjReprT]:
		"""Return all resource groups that contain resources in this tresource"""
		...

	@abstractmethod
	def res_flat(self) -> FrozenSet[ObjReprT]:
		"""Resturn all explicit resources in this tresource"""
		...


DataT = TypeVar("DataT")  # The type of Data you want to store


class INode(Generic[AzObjT, DataT], ABC):
	"""Generic interface for a node in a Tresource"""

	obj: AzObjT
	data: Optional[DataT]


NodeT = TypeVar("NodeT", bound=INode)


class ITresourceData(Generic[AzObjT, DataT, NodeT, ObjReprT], ITresource[AzObjT, ObjReprT]):
	"""Generic interface for a TresourceData"""

	@abstractmethod
	def set_data(self, obj: AzObjT, data: DataT):
		"""Create a node with data."""
		...
