import datetime
from collections import defaultdict
from typing import Dict, Set
from uuid import UUID

from llamazure.azgraph.azgraph import Graph
from llamazure.azgraph.models import ResErr
from llamazure.azrest.azrest import AzRest
from llamazure.azrest.models import AzList
from llamazure.azrest.models import Req as AzReq
from llamazure.history.app import Collector
from llamazure.history.conftest import TimescaledbContainer
from llamazure.history.data import DB, TSDB, Res
from llamazure.test.credentials import credentials


def group_by_time(snapshot: Res) -> Dict[datetime.datetime, Set[str]]:
	out = defaultdict(set)
	for r in snapshot.rows:
		out[r[snapshot.cols["time"]]].add(r[snapshot.cols["rid"]])
	return out


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

	history = Collector(g, azr, db, tenant_id)
	history.take_snapshot()

	delta_q = g.q("Resources | take(1)")
	if isinstance(delta_q, ResErr):
		raise RuntimeError(ResErr)
	history.insert_deltas(delta_q)

	latest = db.read_latest()
	found_resources = {e[latest.cols["rid"]]: e for e in latest.rows}

	delta_id = delta_q[0]["id"].lower()

	assert delta_id in found_resources, "did not find delta in resources"
	found_delta = found_resources[delta_id]
	found_by_time = group_by_time(latest)
	found_delta_time = found_delta[latest.cols["time"]]
	assert found_by_time[found_delta_time] == {delta_id}
	assert {e["id"].lower() for e in g.q("Resources")} == set(found_resources), "snapshot did not contain same resources"
