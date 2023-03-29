from typing import List, Any

from llamazure.rbac.models import Req, ResMaybe, Res
from llamazure.rbac.msgraph import Graph


def get_or_raise(res_maybe: ResMaybe) -> Any:
	if isinstance(res_maybe, Res):
		return res_maybe.value
	else:
		raise res_maybe.exception()


class Users:
	def __init__(self, graph: Graph):
		self.g = graph

	def list(self, **opts) -> List:
		return get_or_raise(self.g.query(Req("users", options=opts)))


class Groups:
	def __init__(self, graph: Graph):
		self.g = graph

	def list(self, **opts):
		return get_or_raise(self.g.query(Req("groups", options=opts)))
