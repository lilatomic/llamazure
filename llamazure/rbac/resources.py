import dataclasses
from typing import Any, List

from llamazure.rbac.models import QueryOpts, Req, Res, ResMaybe
from llamazure.rbac.msgraph import Graph


def get_or_raise(res_maybe: ResMaybe) -> Any:
	if isinstance(res_maybe, Res):
		return res_maybe.value
	else:
		raise res_maybe.exception()


class Users:
	def __init__(self, graph: Graph):
		self.g = graph

	def list(self, opts: QueryOpts = QueryOpts()) -> List:
		return get_or_raise(self.g.query(Req("users", options=opts)))


class Groups:
	def __init__(self, graph: Graph):
		self.g = graph

	def list(self, opts: QueryOpts = QueryOpts()):
		return get_or_raise(self.g.query(Req("groups", options=opts)))

	def list_with_members(self, opts: QueryOpts = QueryOpts()):
		new_opts = dataclasses.replace(opts)
		new_opts.expand.add("members")
		return self.list(new_opts)
