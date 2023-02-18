"""Integration test against a real, live Azure"""
import yaml
from azure.identity import ClientSecretCredential

from llamazure.azgraph.azgraph import Graph


def run():
	"""Run integration test"""
	with open("cicd/secrets.yml", encoding="utf-8") as secrets_file:
		client = yaml.safe_load(secrets_file.read())["azgraph"]

	credential = ClientSecretCredential(tenant_id=client["tenant"], client_id=client["appId"], client_secret=client["password"])

	g = Graph.from_credential(credential)

	print(g.q("Resources | project name, type | limit 5"))


if __name__ == "__main__":
	run()
