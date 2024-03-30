"""Test fixtures for History"""
import random
import string
from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import UUID

import psycopg
import pytest
from psycopg.conninfo import make_conninfo
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for

from llamazure.azgraph import azgraph
from llamazure.history.collect import CredentialCache
from llamazure.history.data import DB, TSDB
from llamazure.test.credentials import credentials
from llamazure.test.util import Fixture


class TimescaledbContainer(DockerContainer):
	"""TimescaleDB Testcontainer"""

	_PORT = 5432
	_ADMIN_USER = "llamazure"
	_ADMIN_PASSWORD = "".join(random.SystemRandom().choices(string.ascii_letters + string.digits + string.punctuation, k=32))
	_DB = "llamazure"
	_IMAGE = "timescale/timescaledb:latest-pg16"

	def __init__(
		self,
		image: str = _IMAGE,
		port: int = _PORT,
		admin_user: str = _ADMIN_USER,
		admin_password: str = _ADMIN_PASSWORD,
		db: str = _DB,
		config_overrides: Optional[Dict[str, Any]] = None,
		**kwargs,
	):
		super().__init__(image, **kwargs)
		self.conf = {}
		# port
		self.port = port
		self.with_bind_ports(container=5432, host=port)
		self.db = db
		self._set_conf("POSTGRES_DB", db)
		self.user = admin_user
		self._set_conf("POSTGRES_USER", admin_user)
		self.password = admin_password
		self._set_conf("POSTGRES_PASSWORD", admin_password)

		if config_overrides:
			self.conf.update(config_overrides)

		self._apply_conf()

	def _set_conf(self, k, v):
		self.conf[k] = v

	def _apply_conf(self):
		for k, v in self.conf.items():
			self.with_env(k, v)

	def connstr(self, db: str) -> str:
		"""Get the connstr for connecting"""
		return make_conninfo(
			"",
			**{
				"host": "localhost",
				"user": self.user,
				"port": self.port,
				"dbname": db,
				"password": self.password,
			},
		)

	def try_connecting(self) -> bool:
		"""Attempt to connect to this container"""
		db = TSDB(connstr=self.connstr(self.db))
		if not db.ping():
			raise ConnectionError()
		return True

	def start(self):
		"""Start the container"""
		ret = super().start()
		wait_for(self.try_connecting)
		return ret

	def new_db(self, db_name: Optional[str] = None) -> DB:
		"""Create a new DB and return the connection info"""
		if db_name is None:
			db_name = "".join(random.choice(string.ascii_lowercase) for i in range(10))

		with psycopg.connect(self.connstr(self.db), autocommit=True) as conn:
			cur = conn.cursor()
			cur.execute(f"""CREATE DATABASE {db_name};""")
			cur.execute(f"""GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {self.user}""")
			conn.commit()

		db = DB(TSDB(connstr=(self.connstr(db_name))))
		db.create_tables()
		return db


@pytest.fixture(scope="module")
def timescaledb_container() -> Fixture[TimescaledbContainer]:
	"""A running TimescaledbContainer fixture"""
	with TimescaledbContainer() as tsdb:
		yield tsdb


@dataclass
class CredentialCacheIntegrationTest(CredentialCache):
	"""Load credentials from the integration test secrets"""

	def azgraph(self, tenant_id: UUID) -> azgraph.Graph:
		return azgraph.Graph.from_credential(credentials())
