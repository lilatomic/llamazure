"""Utilities for the `llamazure.rid` package"""

from __future__ import annotations

from typing import Iterator


class _Peekable:
	"""A wrapper for iterators which lets you peek at the next element without consuming it"""

	def __init__(self, iterator: Iterator):
		self.iterator = iterator
		self._cache = None

	def peek(self):
		"""Peek at the next item in the iterator without consuming it"""
		if not self._cache:
			self._cache = next(self.iterator)
		return self._cache

	def __next__(self):
		if not self._cache:
			return next(self.iterator)
		else:
			out, self._cache = self._cache, None
			return out


class SegmentAndPathIterable:
	"""An iterator that yields the current segment and absolute path"""

	def __init__(self, s: str):
		self.s = s
		self.start = 0

	def __next__(self):
		if self.start == -1:
			raise StopIteration

		i = self.s.find("/", self.start + 1)
		if i == -1:
			segment = self.s[self.start + 1 :]
			mp = self.s
			self.start = -1
		else:
			segment = self.s[self.start + 1 : i]
			mp = self.s[:i]
		self.start = i
		return mp, segment

	def __iter__(self):
		return self
