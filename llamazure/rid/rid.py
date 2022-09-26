import abc
from dataclasses import dataclass

class AzObj(abc.ABC):
	"""An Azure object"""

	...


@dataclass
class Subscription(AzObj):
	uuid: str


@dataclass
class ResourceGroup(AzObj):
	name: str
	subscription: Subscription


@dataclass
class Resource(AzObj):
	provider: str
	res_type: str
	name: str
	parent: Union[ResourceGroup, Resource]
