from textwrap import dedent
from typing import Optional, Tuple

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
				CREATE TABLE IF NOT EXISTS res (
					time	TIMESTAMPTZ NOT NULL,
					rid		VARCHAR,
					data	JSONB
				)
				"""
			)
		)
		self.db.create_hypertable("res", "time")

	def insert_resource(self, time, rid, data):
		"""Insert a resource into the DB"""
		self.db.exec("""INSERT INTO res (time, rid, data) values (%s, %s, %s)""", (time, rid, data),)
