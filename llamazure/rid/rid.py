import abc


class AzObj(abc.ABC):
	"""An Azure object"""

	...


class Subscription(AzObj):
	...


class ResourceGroup(AzObj):
	...


class Resource(AzObj):
	...
