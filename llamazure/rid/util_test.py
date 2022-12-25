"""Tests for the utilities"""

from hypothesis import given
from hypothesis.strategies import characters, lists, text

from llamazure.rid.util import SegmentAndPathIterable


class TestSegmentAndPathIterable:
	"""Test the SegmentAndPathIterable"""

	def test_no_results(self):
		s = "/hihello"
		r = list(iter(SegmentAndPathIterable(s)))
		assert r == [(s, s[1:])]

	def test_leading(self):
		s = "/0"
		r = list(iter(SegmentAndPathIterable(s)))
		assert r == [("/0", "0")]

	def test_trailing(self):
		"""Should have an empty segment at the end"""
		s = "/0/"
		r = list(iter(SegmentAndPathIterable(s)))
		assert r == [("/0", "0"), ("/0/", "")]

	def test_multiple(self):
		s = "/0/1"
		r = list(iter(SegmentAndPathIterable(s)))
		assert r == [("/0", "0"), ("/0/1", "1")]

	@given(lists(text(alphabet=characters(blacklist_characters="/")), min_size=1))
	def test_hypothesis(self, segments):
		s = "/" + "/".join(segments)
		r = list(iter(SegmentAndPathIterable(s)))
		assert [x[1] for x in r] == segments
