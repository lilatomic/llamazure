"""Demo for the `llamazure.history` application"""
import datetime
import json
import os
from dataclasses import asdict, is_dataclass
from typing import Dict, cast

from azure.identity import DefaultAzureCredential

from llamazure.azgraph.azgraph import Graph
from llamazure.azgraph.models import ResErr
from llamazure.history.data import DB, TSDB
from llamazure.rid import mp
from llamazure.tresource.mp import MPData, TresourceMPData


class MyEncoder(json.JSONEncoder):
	"""Encoder for more types"""

	def default(self, o):
		if is_dataclass(o):
			return asdict(o)
		if isinstance(o, datetime.datetime):
			return o.isoformat()
		return super().default(o)


def reformat_resources_for_tresource(resources):
	"""Reformat mp_resources for TresourceMPData"""
	for r in resources:
		path, azobj = mp.parse(r["id"])
		mpdata = MPData(azobj, r)
		yield path, mpdata


if __name__ == "__main__":
	tsdb = TSDB(connstr=os.environ["connstr"])
	db = DB(tsdb)
	db.create_tables()

	g = Graph.from_credential(DefaultAzureCredential())
	resources = g.q("Resources")
	if isinstance(resources, ResErr):
		raise RuntimeError(ResErr)

	tree: TresourceMPData[Dict] = TresourceMPData()
	tree.add_many(reformat_resources_for_tresource(resources))

	snapshot_time = datetime.datetime.utcnow()

	db.insert_snapshot(snapshot_time, ((cast(str, path), mpdata.data) for path, mpdata in tree.resources.items() if mpdata.data is not None))

	delta_q = g.q("Resources | take(1)")
	if isinstance(delta_q, ResErr):
		raise RuntimeError(ResErr)
	delta = delta_q[0]
	db.insert_delta(snapshot_time + datetime.timedelta(seconds=1), delta["id"].lower(), delta)

	print(json.dumps(db.read_latest(), indent=2, cls=MyEncoder))
	# print(json.dumps(db.read_snapshot(snapshot_time + datetime.timedelta(seconds=2)), indent=2, cls=MyEncoder))
