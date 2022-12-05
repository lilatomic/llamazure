from hypothesis import assume, given
from hypothesis.strategies import lists, text, characters

from llamazure.rid.util import FindAllIterable


class TestFindAll:

	def test_no_results(self):
		s = "hihello"
		r = list(iter(FindAllIterable(s)))
		assert r == [(s, s)]

	def test_leading(self):
		s = "/0"
		r = list(iter(FindAllIterable(s)))
		assert r == [('/0', '/0')]

	def test_trailing(self):
		"""Should have an empty segment at the end"""
		s = "0/"
		r = list(iter(FindAllIterable(s)))
		assert r == [('0', '0'), ('0/', '/')]

	def test_multiple(self):
		s = "/0/1"
		r = list(iter(FindAllIterable(s)))
		assert r == [('/0', '/0'), ('/0/1', '/1')]

	@given(lists(text(alphabet=characters(blacklist_characters="/")), min_size=1))
	def test_hypothesis(self, segments):
		s = "/" + "/".join(segments)
		r = list(iter(FindAllIterable(s)))
		assert [x[1] for x in r] == ["/" + x for x in segments]


