"""Interface with the TimescaleDB"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from textwrap import dedent
from typing import Any, Dict, Iterable, List, Optional, Tuple
from uuid import UUID

import psycopg
from psycopg import OperationalError
from psycopg.types.json import Jsonb


@dataclass(frozen=True)
class Res:
	cols: Dict[str, int]
	rows: List[Tuple]

	@staticmethod
	def decode(cursor: psycopg.cursor, result) -> Res:
		return Res(
			cols={desc[0]: i for i, desc in enumerate(cursor.description)},
			rows=result,
		)


class TSDB:
	"""TimescaleDB connection"""

	def __init__(self, connstr: str):
		self.connstr = connstr

	def exec(self, q, data: Optional[Tuple] = None):
		"""Execute a query"""
		with psycopg.connect(self.connstr) as conn:
			cur = conn.cursor()
			cur.execute(q, data)
			conn.commit()
		return cur

	def exec_returning(self, q, data: Optional[Tuple] = None) -> Any:
		"""Execute a query"""
		with psycopg.connect(self.connstr) as conn:
			cur = conn.cursor()
			cur.execute(q, data)
			res = cur.fetchone()
			if res is not None:
				res = res[0]
			conn.commit()
		return res

	def create_hypertable(self, name: str, time_col: str):
		"""Convert a table into a hypertable"""
		self.exec(f"""SELECT create_hypertable('{name}', by_range('{time_col}'), if_not_exists => TRUE)""")

	def ping(self) -> bool:
		"""Check connectivity to postgresql"""
		try:
			r = self.exec_returning("select version();")
			assert r
			return True
		except OperationalError:
			return False


class DB:
	"""Store, load, and create tables"""

	def __init__(self, db: TSDB):
		self.db = db

	def create_tables(self):
		"""Create the tables in TimescaleDB"""
		self.db.exec(
			dedent(
				"""\
				CREATE TABLE IF NOT EXISTS snapshot (
					id 				SERIAL PRIMARY KEY,
					time			TIMESTAMPTZ NOT NULL,
					azure_tenant 	UUID
				)
				"""
			)
		)

		self.db.exec(
			dedent(
				"""\
				CREATE TABLE IF NOT EXISTS res (
					time TIMESTAMPTZ NOT NULL,
					snapshot 		INTEGER,
					azure_tenant 	UUID,
					rid				VARCHAR,
					data			JSONB,
					FOREIGN KEY (snapshot) REFERENCES snapshot (id)
				)
				"""
			)
		)
		self.db.create_hypertable("res", "time")

	def insert_resource(self, time: datetime.datetime, azure_tenant: UUID, snapshot_id, rid: str, data: dict):
		"""Insert a resource into the DB"""
		self.db.exec(
			"""INSERT INTO res (time, snapshot, azure_tenant, rid, data) VALUES (%s, %s, %s, %s, %s)""",
			(time, snapshot_id, azure_tenant, rid, Jsonb(data)),
		)

	def insert_snapshot(self, time: datetime.datetime, azure_tenant: UUID, resources: Iterable[Tuple[str, dict]]):
		"""Insert a complete snapshot into the DB"""
		snapshot_id = self.db.exec_returning("""INSERT INTO snapshot (time, azure_tenant) VALUES (%s, %s) RETURNING id""", (time, azure_tenant))
		for rid, data in resources:
			self.insert_resource(time, azure_tenant, snapshot_id, rid, data)

	def insert_delta(self, time: datetime.datetime, azure_tenant: UUID, rid: str, data: dict):
		"""Insert a single delta into the DB"""
		return self.insert_resource(time, azure_tenant, None, rid, data)

	def read_snapshot(self, time: datetime.datetime):
		"""Read a complete snapshot. Does not include any deltas"""
		res = self.db.exec(
			dedent(
				"""\
				WITH LatestSnapshot AS (
					SELECT id FROM snapshot WHERE time < %s ORDER BY time DESC LIMIT 1
				)
				SELECT * FROM res WHERE snapshot = (SELECT id FROM LatestSnapshot);
				"""
			),
			(time,),
		).fetchall()
		return res

	def read_latest(self) -> Res:
		"""Read the latest information for all resources. Includes deltas."""
		cur = self.db.exec("""SELECT DISTINCT ON (rid) * FROM res ORDER BY rid, time DESC;""")
		return Res.decode(cur, cur.fetchall())

	def read_at(self, time: datetime.datetime) -> Res:
		"""Read the information for all resources at a point in time. Includes deltas."""
		cur = self.db.exec("""SELECT DISTINCT ON (rid) * FROM res WHERE time < %s ORDER BY rid, time DESC;""", (time,))
		return Res.decode(cur, cur.fetchall())
