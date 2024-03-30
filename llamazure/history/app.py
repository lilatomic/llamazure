"""The llamazure.history application, a webserver to collect and present the history of Azure tenancies"""
from __future__ import annotations

import datetime
from typing import List
from uuid import UUID

from azure.identity import DefaultAzureCredential
from fastapi import Depends, FastAPI
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from llamazure.azgraph import azgraph
from llamazure.history.collect import Collector, CredentialCache
from llamazure.history.data import DB, TSDB, Res


class CredentialCacheDefault(CredentialCache):
	"""Load Azure credentials with default loader"""

	@staticmethod
	def credential():
		"""Get the Default Azure credential"""
		return DefaultAzureCredential()

	def azgraph(self, tenant_id: UUID) -> azgraph.Graph:
		return azgraph.Graph.from_credential(self.credential())


class Settings(BaseSettings):
	"""Settings for llamazure.history"""

	model_config = SettingsConfigDict(env_nested_delimiter="__")

	class DB(BaseModel):
		"""Settings for DB"""

		connstr: str

	db: Settings.DB


settings = Settings()


def get_collector() -> Collector:
	"""FastAPI Dependency for Collector"""
	yield Collector(
		CredentialCacheDefault(),
		DB(TSDB(settings.db.connstr)),
	)


def get_db() -> DB:
	"""FastAPI Dependency for DB"""
	yield DB(TSDB(settings.db.connstr))


app = FastAPI()


@app.post("/collect/snapshots")
async def collect_snapshot(tenant_id: UUID, collector: Collector = Depends(get_collector)):
	"""Dispatch the collection of a snapshot"""
	collector.take_snapshot(tenant_id)


@app.post("/collect/delta")
async def collect_delta(tenant_id: UUID, delta: dict, collector: Collector = Depends(get_collector)):
	"""Insert a single delta"""
	collector.insert_deltas(tenant_id, [delta])


@app.post("/collect/deltas")
async def collect_deltas(tenant_id: UUID, deltas: List[dict], collector: Collector = Depends(get_collector)):
	"""Insert multiple deltas"""
	collector.insert_deltas(tenant_id, deltas)


@app.get("/history")
async def read_history(db: DB = Depends(get_db), at: datetime.datetime = None) -> Res:
	"""Read history at a point in time"""
	if at is None:
		return db.read_latest()
	else:
		return db.read_at(at)


@app.get("/ping")
async def ping() -> str:
	"""PING this service for up check"""
	now = datetime.datetime.now(datetime.timezone.utc).isoformat()
	return f"PONG {now}"


@app.post("/admin/init_db")
async def init_db(db: DB = Depends(get_db)):
	"""Initialize the tables in the database"""
	db.create_tables()
