import dataclasses
from copy import copy
from typing import Any, List

from llamazure.msgraph.models import QueryOpts, Req, Res, ResMaybe
from llamazure.msgraph.msgraph import Graph


def get_or_raise(res_maybe: ResMaybe) -> Any:
	if isinstance(res_maybe, Res):
		return res_maybe.value
	else:
		raise res_maybe.exception()


class Users:
	def __init__(self, graph: Graph):
		self.g = graph

	def current(self):
		return get_or_raise(self.g.query(Req("me", options=QueryOpts(expand={"memberOf"}))))

	def list(self, opts: QueryOpts = QueryOpts()) -> List:
		return get_or_raise(self.g.query(Req("users", options=opts)))

	def list_with_memberOf(self, opts: QueryOpts = QueryOpts()) -> List:
		new_opts = dataclasses.replace(opts, expand=copy(opts.expand))
		new_opts.expand.add("memberOf")
		return self.list(new_opts)


class Groups:
	def __init__(self, graph: Graph):
		self.g = graph

	def list(self, opts: QueryOpts = QueryOpts()):
		return get_or_raise(self.g.query(Req("groups", options=opts)))

	def list_with_memberships(self, opts: QueryOpts = QueryOpts()):
		"""Get groups with their transitive members and transitive memberOfs"""

		# only allows 1 item in `$expand`, so we have to make 2 queries and join
		transitive_members = self.list(dataclasses.replace(opts, expand={"transitiveMembers"}))
		transitive_memberOfs = self.list(dataclasses.replace(opts, expand={"transitiveMemberOf"}))

		keyed_transitive_memberOfs = {v["id"]: v for v in transitive_memberOfs}

		# I think there's minimal risk in assuming these 2 are bijective
		out = {}
		for i in transitive_members:
			i["transitiveMemberOf"] = keyed_transitive_memberOfs[i["id"]]
			out[i["id"]] = i

		return list(out.values())
