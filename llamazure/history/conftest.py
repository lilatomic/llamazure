"""Test fixtures for History"""
import datetime
import random
import string
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from uuid import UUID

import psycopg
import pytest
from psycopg.conninfo import make_conninfo
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for

from llamazure.azgraph import azgraph
from llamazure.history.collect import CredentialCache
from llamazure.history.data import DB, TSDB, Res
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
		admin_user: str = _ADMIN_USER,
		admin_password: str = _ADMIN_PASSWORD,
		db: str = _DB,
		config_overrides: Optional[Dict[str, Any]] = None,
		**kwargs,
	):
		super().__init__(image, **kwargs)
		self.conf = {}
		# port
		self.with_exposed_ports(self._PORT)
		self.db = db
		self._set_conf("POSTGRES_DB", db)
		self.user = admin_user
		self._set_conf("POSTGRES_USER", admin_user)
		self.password = admin_password
		self._set_conf("POSTGRES_PASSWORD", admin_password)

		if config_overrides:
			self.conf.update(config_overrides)

		self._apply_conf()

	@property
	def port(self) -> int:
		return int(self.get_exposed_port(self._PORT))

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


@pytest.fixture(scope="function")
def newdb(timescaledb_container: TimescaledbContainer) -> DB:
	"""Fixture for DB"""
	return timescaledb_container.new_db()


@pytest.fixture
def now() -> datetime.datetime:
	"""Fixture for current time"""
	return datetime.datetime.now(tz=datetime.timezone.utc)


@dataclass
class CredentialCacheIntegrationTest(CredentialCache):
	"""Load credentials from the integration test secrets"""

	def azgraph(self, tenant_id: UUID) -> azgraph.Graph:
		return azgraph.Graph.from_credential(credentials())


@dataclass
class FakeDataFactory:
	"""
	All the fake data you need.

	Generator functions accept a kw-only parameter `idx`.
	This key is used to store the value generated.
	Re-invoke this function to retrieve the generated value
	"""

	tenants: dict = field(default_factory=dict)
	resources: dict = field(default_factory=dict)
	snapshots: dict = field(default_factory=dict)

	def _get_or_gen(self, db: dict, gen: Callable, idx: Union[str, int]):
		if idx in db:
			return db[idx]
		else:
			v = gen()
			db[idx] = v
			return v

	def tenant(self, *, idx: Union[str, int]) -> UUID:
		"""A fake tenant"""
		return self._get_or_gen(self.tenants, uuid.uuid4, idx)

	def _resource(self, rev=0) -> dict:
		return {"id": "/subscriptions/s0/fakeResource/", "k0": rev}

	def resource(self, rev=0, *, idx: Union[str, int]) -> dict:
		"""A single fake resource"""
		return self._get_or_gen(self.resources, lambda: self._resource(rev), idx)

	def snapshot(self, i=4, *, idx: Union[str, int]) -> List[Tuple[str, dict]]:
		"""A fake snapshot"""

		def _mk_snapshot():
			resources = [self._resource(rev) for rev in range(0, i)]
			return [(e["id"], e) for e in resources]

		return self._get_or_gen(self.snapshots, _mk_snapshot, idx)

	def res2snapshot(self, res: Res) -> List[Tuple[str, dict]]:
		"""Convert a Res into the original snapshot"""
		return [(e[res.cols["rid"]], e[res.cols["data"]]) for e in res.rows]

	def compare_snapshot(self, r: Res, *idxs) -> bool:
		"""Assert that a result of reading a snapshot is the same as the snapshot inserted"""
		merged = sum((self.snapshot(idx=idx) for idx in idxs), start=[])
		assert self.res2snapshot(r) == merged
		return True

	def assert_snapshot_at(self, r: Res, at: datetime.datetime) -> bool:
		"""Assert that a snapshot happened at the given time"""
		assert all(e[r.cols["time"]] == at for e in r.rows)
		return True


@pytest.fixture(scope="function")
def fdf() -> FakeDataFactory:
	"""Fixture for FakeDataFactory"""
	return FakeDataFactory()
