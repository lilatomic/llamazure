"""Integration test against a real, live Azure"""
# pylint: disable=redefined-outer-name

import pytest

from llamazure.azgraph.azgraph import Graph
from llamazure.azgraph.models import Req, Res, ResErr
from llamazure.test.credentials import load_credentials
from llamazure.test.inspect import print_output


@pytest.fixture()
@pytest.mark.integration
def graph():
	"""Run integration test"""
	credential = load_credentials()
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
