import datetime
from dataclasses import dataclass
from typing import Dict, Generator, Tuple, cast
from uuid import UUID

from llamazure.azgraph import azgraph
from llamazure.azrest.azrest import AzRest
from llamazure.history.data import DB
from llamazure.rid import mp
from llamazure.tresource.mp import MPData, TresourceMPData


def reformat_resources_for_tresource(resources):
	"""Reformat mp_resources for TresourceMPData"""
	for r in resources:
		path, azobj = mp.parse(r["id"])
		mpdata = MPData(azobj, r)
		yield path, mpdata


def reformat_resources_for_db(tree: TresourceMPData) -> Generator[Tuple[str, Dict], None, None]:
	return ((cast(str, path), mpdata.data) for path, mpdata in tree.resources.items() if mpdata.data is not None)


@dataclass
class Collector:
	"""Load data from Azure Resource Manager and put into the DB"""
	g: azgraph.Graph
	azr: AzRest
	db: DB
	tenant_id: UUID

	def take_snapshot(self):
		"""Take a snapshot and insert it into the DB"""
		resources = self.g.q("Resources")
		if isinstance(resources, azgraph.ResErr):
			raise RuntimeError(azgraph.ResErr)

		tree: TresourceMPData[Dict] = TresourceMPData()
		tree.add_many(reformat_resources_for_tresource(resources))

		self.db.insert_snapshot(
			time=self.snapshot_time(),
			azure_tenant=self.tenant_id,
			resources=reformat_resources_for_db(tree),
		)

	def insert_deltas(self, deltas):
		tree: TresourceMPData[Dict] = TresourceMPData()
		tree.add_many(reformat_resources_for_tresource(deltas))

		for rid, data in reformat_resources_for_db(tree):
			self.db.insert_delta(time=self.snapshot_time(), azure_tenant=self.tenant_id, rid=rid, data=data)

	@staticmethod
	def snapshot_time() -> datetime.datetime:
		return datetime.datetime.now(datetime.timezone.utc)
