"""Test Tresource"""
from typing import List

from hypothesis import given
from hypothesis.strategies import lists

from llamazure.rid.rid import ResourceGroup
from llamazure.rid.rid_test import st_rg, st_subscription
from llamazure.tresource.tresource import Tresource


class TestBuildTree:
	"""Test that building a tree is correct and seamless"""

	@given(lists(st_subscription))
	def test_build_subscriptions(self, subs):
		"""Test adding only subscriptions"""
		tree = Tresource()

		for sub in subs:
			tree.add(sub)

		print(len(tree.subs))
		assert len(set(tree.subs)) == len(subs)

	@given(lists(st_rg))
	def test_build_rg(self, rgs: List[ResourceGroup]):
		"""Test adding only RGs"""
		tree = Tresource()

		subs = set()

		for rg in rgs:
			subs.add(rg.sub)
			tree.add(rg)

		assert subs == set(tree.subs)
		assert set(rgs) == set(tree.rgs_flat)
