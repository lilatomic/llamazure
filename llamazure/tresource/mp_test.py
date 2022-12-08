"""Test TresourceMP"""
from typing import List

from hypothesis import given
from hypothesis.strategies import lists

from llamazure.rid import rid
from llamazure.rid.conftest import st_resource_base, st_rg, st_subscription
from llamazure.rid.conv import rid2mp
from llamazure.rid.mp import Resource
from llamazure.tresource.mp import TresourceMP


class TestBuildTree:
	"""Test that building the tree is correct and seamless"""

	@given(lists(st_subscription))
	def test_build_subscriptions(self, subs):
		subs = [rid2mp(sub) for sub in subs]
		tree = TresourceMP()

		for sub in subs:
			tree.add_single(sub)

		assert set(tree.subs) == set(sub.path for sub in subs)

	@given(lists(st_rg))
	def test_build_rgs(self, rgs):
		rgs = [rid2mp(rg) for rg in rgs]
		tree = TresourceMP()

		subs = set()
		for rg in rgs:
			subs.add(rg.sub)
			tree.add_single(rg)

		assert subs == set(tree.subs)
		assert set(rg.path for rg in rgs) == set(tree.rgs_flat())

	@given(lists(st_resource_base))
	def test_build_simple_resource(self, ress_rid: List[rid.Resource]):
		ress: List[Resource] = []
		for res_rid in ress_rid:
			converted = rid2mp(res_rid)
			assert isinstance(converted, Resource)
			ress.append(converted)
		tree = TresourceMP()

		subs = set()
		rgs = set()

		for res in ress:
			subs.add(res.sub)
			if res.rg:
				rgs.add(res.rg)
			tree.add_single(res)

		assert subs == set(tree.subs)
		assert rgs == set(tree.rgs_flat())

		# since there is no nesting, there are no implicit resources, and this comparison is valid
		assert set(ress) == set(tree.res_flat())
