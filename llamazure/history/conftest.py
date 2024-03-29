import random
import string
from typing import Any, Dict, Optional

import pytest
from psycopg.conninfo import make_conninfo
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for

from llamazure.history.data import TSDB
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

	@property
	def connstr(self) -> str:
		"""Get the connstr for connecting"""
		return make_conninfo(
			"",
			**{
				"host": "localhost",
				"user": self.user,
				"port": self.port,
				"dbname": self.db,
				"password": self.password,
			},
		)

	def try_connecting(self) -> bool:
		"""Attempt to connect to this container"""
		db = TSDB(connstr=self.connstr)
		if not db.ping():
			raise ConnectionError()
		return True

	def start(self):
		"""Start the container"""
		ret = super().start()
		wait_for(self.try_connecting)
		return ret


@pytest.fixture(scope="module")
def timescaledb_container() -> Fixture[TimescaledbContainer]:
	with TimescaledbContainer() as tsdb:
		yield tsdb
