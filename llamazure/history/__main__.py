import json
import os
from dataclasses import is_dataclass, asdict
import datetime

from azure.identity import DefaultAzureCredential

from llamazure.azgraph.azgraph import Graph
from llamazure.history.data import TSDB, DB
from llamazure.rid import mp
from llamazure.tresource.mp import TresourceMPData, MPData


class MyEncoder(json.JSONEncoder):
	def default(self, obj):
		if is_dataclass(obj):
			return asdict(obj)
		if isinstance(obj, datetime.datetime):
			return obj.isoformat()
		return super().default(obj)


def reformat(resources):
	for r in resources:
		path, azobj = mp.parse(r["id"])
		mpdata = MPData(azobj, r)
		yield path, mpdata


if __name__ == "__main__":
	tsdb = TSDB(connstr=os.environ.get("connstr"))
	db = DB(tsdb)
	db.create_tables()

	g = Graph.from_credential(DefaultAzureCredential())
	resources = g.q("Resources")

	tree = TresourceMPData()
	tree.add_many(reformat(resources))

	snapshot_time = datetime.datetime.utcnow()

	db.insert_snapshot(snapshot_time, ((path, mpdata.data) for path, mpdata in tree.resources.items()))

	delta = g.q("Resources | take(1)")[0]
	db.insert_delta(snapshot_time + datetime.timedelta(seconds=1), delta["id"].lower(), delta)

	print(json.dumps(db.read_latest(), indent=2, cls=MyEncoder))
	# print(json.dumps(db.read_snapshot(snapshot_time + datetime.timedelta(seconds=2)), indent=2, cls=MyEncoder))
