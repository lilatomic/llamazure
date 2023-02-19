"""Integration test against a real, live Azure"""
import yaml
from azure.identity import ClientSecretCredential

from llamazure.azgraph.azgraph import Graph
from llamazure.azgraph.models import Req


def run():
	"""Run integration test"""

	with open("cicd/secrets.yml", encoding="utf-8") as secrets_file:
		client = yaml.safe_load(secrets_file.read())["azgraph"]

	credential = ClientSecretCredential(tenant_id=client["tenant"], client_id=client["appId"], client_secret=client["password"])

	g = Graph.from_credential(credential)
	run_simple(g)
	run_paginated(g)


def run_simple(g: Graph):
	"""Run simple query"""
	print("simple", g.q("Resources | project id, name, type, location | limit 5"))


def run_paginated(g: Graph):
	"""Run a paginted request. Forces smol pagination"""
	print(
		"paginated",
		g.query(
			Req(
				query="Resources | project id",
				subscriptions=g.subscriptions,
				options={"$top": 3, "$skip": 1},
			)
		),
	)


def test_shim():
	"""Make pytest succeed"""
	...


if __name__ == "__main__":
	run()
