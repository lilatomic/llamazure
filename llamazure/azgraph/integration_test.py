"""Integration test against a real, live Azure"""
# pylint: disable=redefined-outer-name

import os
from typing import Any

import pytest
import yaml
from azure.identity import ClientSecretCredential

from llamazure.azgraph.azgraph import Graph
from llamazure.azgraph.models import Req, Res, ResErr


def print_output(name: str, output: Any):
	should_print = os.environ.get("INTEGRATION_PRINT_OUTPUT", "False") == "True"
	if should_print:
		print(name, output)


@pytest.fixture()
def graph():
	"""Run integration test"""

	secrets = os.environ.get("integration_test_secrets")
	if not secrets:
		with open("cicd/secrets.yml", mode="r", encoding="utf-8") as f:
			secrets = f.read()
	secrets = yaml.safe_load(secrets)
	client = secrets["azgraph"]

	credential = ClientSecretCredential(tenant_id=client["tenant"], client_id=client["appId"], client_secret=client["password"])

	g = Graph.from_credential(credential)
	return g


@pytest.mark.integration
def test_simple(graph: Graph):
	"""Run simple query"""
	res = graph.q("Resources | project id, name, type, location | limit 5")
	print_output("simple", res)
	matches_type = isinstance(res, list)
	assert matches_type  # q returns data


@pytest.mark.integration
def test_full(graph: Graph):
	"""Run simple query using the full query interface"""
	res = graph.query(
		Req(
			"Resources | project id, name, type, location | limit 1",
			subscriptions=graph.subscriptions,
			options={"$skip": 1},
		)
	)
	print_output("full", res)
	matches_type = isinstance(res, Res)
	assert matches_type


@pytest.mark.integration
def test_paginated(graph: Graph):
	"""Run a paginted request. Forces smol pagination"""
	res = graph.query(
		Req(
			query="Resources | project id",
			subscriptions=graph.subscriptions,
			options={"$top": 3, "$skip": 1},
		)
	)
	print_output("paginated", res)
	matches_type = isinstance(res, Res)
	assert matches_type


@pytest.mark.integration
def test_error(graph: Graph):
	"""Run a query that results in an error"""
	res = graph.q("Resources | syntax error")
	print_output("error", res)
	matches_type = isinstance(res, ResErr)
	assert matches_type


def test_shim():
	"""Make pytest succeed even when no tests are selected"""
	...
