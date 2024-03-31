import datetime
from collections import defaultdict
from typing import Dict, Set
from uuid import UUID

import pytest

from llamazure.azgraph.azgraph import Graph
from llamazure.azgraph.models import ResErr
from llamazure.azrest.azrest import AzRest
from llamazure.azrest.models import AzList
from llamazure.azrest.models import Req as AzReq
from llamazure.history.collect import Collector
from llamazure.history.conftest import CredentialCacheIntegrationTest, TimescaledbContainer
from llamazure.history.data import Res
from llamazure.test.credentials import load_credentials


def group_by_time(snapshot: Res) -> Dict[datetime.datetime, Set[str]]:
	out = defaultdict(set)
	for r in snapshot.rows:
		out[r[snapshot.cols["time"]]].add(r[snapshot.cols["rid"]])
	return out


def test_nothing():
	"""Prevent collection problems for partitions"""


@pytest.mark.integration
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
	db = timescaledb_container.new_db()

	credential = load_credentials()
	g = Graph.from_credential(credential)
	azr = AzRest.from_credential(credential)

	tenants = azr.call(AzReq.get("GetTenants", "/tenants", "2022-12-01", AzList[dict]))
	tenant_id = UUID(tenants[0]["tenantId"])

	history = Collector(CredentialCacheIntegrationTest(), db)
	history.take_snapshot(tenant_id)

	delta_q = g.q("Resources | take(1)")
	if isinstance(delta_q, ResErr):
		raise RuntimeError(ResErr)
	history.insert_deltas(tenant_id, delta_q)

	latest = db.read_latest()
	found_resources = {e[latest.cols["rid"]]: e for e in latest.rows}

	delta_id = delta_q[0]["id"].lower()

	assert delta_id in found_resources, "did not find delta in resources"
	found_delta = found_resources[delta_id]
	found_by_time = group_by_time(latest)
	found_delta_time = found_delta[latest.cols["time"]]
	assert found_by_time[found_delta_time] == {delta_id}

	resources = g.q("Resources")
	if isinstance(delta_q, ResErr):
		raise RuntimeError(ResErr)
	assert isinstance(resources, list)
	assert len(resources) == len(found_resources), "snapshot and resources had different count"
	assert {e["id"].lower() for e in resources} == set(found_resources), "snapshot did not contain same resources"
