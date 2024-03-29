import datetime
from typing import Dict, cast
from uuid import UUID

from llamazure.azgraph.azgraph import Graph
from llamazure.azgraph.models import ResErr
from llamazure.azrest.azrest import AzRest
from llamazure.azrest.models import AzList
from llamazure.azrest.models import Req as AzReq
from llamazure.history.app import reformat_resources_for_tresource
from llamazure.history.conftest import TimescaledbContainer
from llamazure.history.data import DB, TSDB
from llamazure.test.credentials import credentials
from llamazure.tresource.mp import TresourceMPData


def test_integration(timescaledb_container: TimescaledbContainer) -> None:
	"""
	End-to-end test that:
	- creates tables
	- loads data from azure
	- converts to a tresource
	- inserts into the tsdb
	- synthesises a delta
	- inserts a delta
	"""
	tsdb = TSDB(connstr=timescaledb_container.connstr)
	db = DB(tsdb)
	db.create_tables()

	credential = credentials()
	g = Graph.from_credential(credential)
	azr = AzRest.from_credential(credential)

	tenants = azr.call(AzReq.get("GetTenants", "/tenants", "2022-12-01", AzList[dict]))
	tenant_id = UUID(tenants[0]["tenantId"])

	resources = g.q("Resources")
	if isinstance(resources, ResErr):
		raise RuntimeError(ResErr)

	tree: TresourceMPData[Dict] = TresourceMPData()
	tree.add_many(reformat_resources_for_tresource(resources))

	snapshot_time = datetime.datetime.now(datetime.timezone.utc)

	db.insert_snapshot(snapshot_time, tenant_id, ((cast(str, path), mpdata.data) for path, mpdata in tree.resources.items() if mpdata.data is not None))

	delta_q = g.q("Resources | take(1)")
	if isinstance(delta_q, ResErr):
		raise RuntimeError(ResErr)
	delta = delta_q[0]
	delta_id = delta["id"].lower()
	delta_time = snapshot_time + datetime.timedelta(seconds=1)
	db.insert_delta(delta_time, tenant_id, delta_id, delta)

	latest = db.read_latest()
	found_resources = {e[latest.cols["rid"]]: e for e in latest.rows}

	assert delta_id in found_resources, "did not find delta in resources"
	found_delta = found_resources[delta_id]
	assert found_delta[latest.cols["time"]] == delta_time
	assert set(tree.resources) == set(found_resources), "snapshot did not contain same resources"
