"""Tests for DB functions"""
import datetime

from llamazure.history.conftest import FakeDataFactory
from llamazure.history.data import DB


class TestSnapshotsSingleTenant:
	"""Test for reading snapshots where all snapshots are the same tenant"""

	def test_single(self, fdf: FakeDataFactory, newdb: DB, now: datetime.datetime):
		"""Test reading a single snapshot"""
		newdb.insert_snapshot(now, fdf.tenant(idx=0), fdf.snapshot(idx=0))
		r = newdb.read_snapshot(now)
		assert fdf.compare_snapshot(r, 0)

	def test_in_past(self, fdf: FakeDataFactory, newdb: DB, now: datetime):
		"""Test that we read the snapshot even if we're after the latest one"""
		newdb.insert_snapshot(now, fdf.tenant(idx=0), fdf.snapshot(idx=0))
		r = newdb.read_snapshot(now + datetime.timedelta(days=1))
		assert fdf.compare_snapshot(r, 0)

	def test_multiple(self, fdf: FakeDataFactory, newdb: DB, now: datetime):
		"""Test with multiple snapshots"""
		newdb.insert_snapshot(now, fdf.tenant(idx=0), fdf.snapshot(idx=0))
		time_2 = now + datetime.timedelta(days=2)
		newdb.insert_snapshot(time_2, fdf.tenant(idx=0), fdf.snapshot(idx=1))

		r_between = newdb.read_snapshot(now + datetime.timedelta(days=1))
		assert fdf.compare_snapshot(r_between, 0)
		assert fdf.assert_snapshot_at(r_between, now)

		r_after = newdb.read_snapshot(now + datetime.timedelta(days=3))
		assert fdf.compare_snapshot(r_after, 1)
		assert fdf.assert_snapshot_at(r_after, time_2)


class TestSnapshotMultiTenant:
	def test_single_per_tenant(self, fdf: FakeDataFactory, newdb: DB, now: datetime):
		"""Test that the latest is retrieved for each of multiple tenants"""
		newdb.insert_snapshot(now, fdf.tenant(idx=0), fdf.snapshot(idx=0))
		newdb.insert_snapshot(now, fdf.tenant(idx=1), fdf.snapshot(idx=1))

		r = newdb.read_snapshot(now)
		assert fdf.compare_snapshot(r, 0, 1)
