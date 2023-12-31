import json
import os
from dataclasses import is_dataclass, asdict
import datetime

from azure.identity import DefaultAzureCredential

from llamazure.azgraph.azgraph import Graph
from llamazure.history.data import TSDB, DB
from llamazure.rid import mp
from llamazure.tresource.mp import TresourceMPData, MPData


class DataclassEncoder(json.JSONEncoder):
	def default(self, obj):
		if is_dataclass(obj):
			return asdict(obj)
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

	for path, mpdata in tree.resources.items():
		db.insert_resource(snapshot_time, path, mpdata.data)


	# print(json.dumps(tree, cls=DataclassEncoder, indent=2))
