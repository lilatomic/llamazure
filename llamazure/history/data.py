import datetime
from textwrap import dedent
from typing import Optional, Tuple, Iterable, Any

import psycopg2
import psycopg2.extras
import psycopg2.extensions

psycopg2.extensions.register_adapter(dict, psycopg2.extras.Json)


class TSDB:
	"""TimescaleDB connection"""

	def __init__(self, connstr: str):
		self.connstr = connstr

	def exec(self, q, data: Optional[Tuple] = None):
		"""Execute a query"""
		with psycopg2.connect(self.connstr) as conn:
			cur = conn.cursor()
			cur.execute(q, data)
			conn.commit()
		return cur

	def exec_returning(self, q, data: Optional[Tuple] = None) -> Any:
		"""Execute a query"""
		with psycopg2.connect(self.connstr) as conn:
			cur = conn.cursor()
			cur.execute(q, data)
			res = cur.fetchone()[0]
			conn.commit()
		return res

	def create_hypertable(self, name: str, time_col: str):
		"""Convert a table into a hypertable"""
		self.exec(f"""SELECT create_hypertable('{name}', by_range('{time_col}'), if_not_exists => TRUE)""")


class DB:
	def __init__(self, db: TSDB):
		self.db = db

	def create_tables(self):
		self.db.exec(
			dedent(
				"""\
				CREATE TABLE IF NOT EXISTS snapshot (
					id SERIAL PRIMARY KEY,
					time TIMESTAMPTZ NOT NULL
				)
				"""
			)
		)

		self.db.exec(
			dedent(
				"""\
				CREATE TABLE IF NOT EXISTS res (
					time TIMESTAMPTZ NOT NULL,
					snapshot 	INTEGER,
					rid			VARCHAR,
					data		JSONB,
					FOREIGN KEY (snapshot) REFERENCES snapshot (id)
				)
				"""
			)
		)
		self.db.create_hypertable("res", "time")

	def insert_resource(self, time: datetime.datetime, snapshot_id, rid: str, data: dict):
		"""Insert a resource into the DB"""
		self.db.exec("""INSERT INTO res (time, snapshot, rid, data) VALUES (%s, %s, %s, %s)""", (time, snapshot_id, rid, data),)

	def insert_snapshot(self, time: datetime.datetime, resources: Iterable[Tuple[str, dict]]):
		snapshot_id = self.db.exec_returning("""INSERT INTO snapshot (time) VALUES (%s) RETURNING id""", (time,))
		for rid, data in resources:
			self.insert_resource(time, snapshot_id, rid, data)

	def read_at(self, time: datetime.datetime):
		res = self.db.exec(
			dedent(
				"""\
				WITH LatestSnapshot AS (
					SELECT id FROM snapshot WHERE time < %s ORDER BY time DESC LIMIT 1
				)
				SELECT * FROM res WHERE snapshot = (SELECT id FROM LatestSnapshot);
				"""),
		(time,)
		).fetchall()
		return res
