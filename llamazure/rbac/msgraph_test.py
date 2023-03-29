"""Tests for the Microsoft Graph"""
# pylint: disable=redefined-outer-name
# pylint: disable=protected-access

from unittest.mock import Mock

from llamazure.rbac.models import Req, Res, ResErr
from llamazure.rbac.msgraph import Graph, RetryPolicy


def null_graph(retry_policy: RetryPolicy) -> Graph:
	"""Shim Graph instance"""
	return Graph(Mock(), retry_policy)


class TestRetries:
	"""Test retries on non-paginated queries"""

	normal_retry_policy = RetryPolicy(retries=5)
	empty_req = Req("")

	failed_res = ResErr("", "", None, {})
	successful_res = Res(empty_req, odata={}, value=[])

	def test_successful_query(self):
		"""Test that a successful query does not trigger a retry"""
		g = null_graph(self.normal_retry_policy)
		g._exec_query = Mock(return_value=self.successful_res)

		res = g.query(self.empty_req)

		assert res == self.successful_res
		g._exec_query.assert_called_once()

	def test_one_error(self):
		g = null_graph(self.normal_retry_policy)
		g._exec_query = Mock(side_effect=[self.failed_res, self.successful_res])

		res = g.query(self.empty_req)

		assert res == self.successful_res
		assert g._exec_query.call_count == 2

	def test_many_errors(self):
		"""Test that a multiple failures on the same query are retried"""
		g = null_graph(self.normal_retry_policy)
		g._exec_query = Mock(side_effect=[self.failed_res, self.failed_res, self.failed_res, self.successful_res])

		res = g.query(self.empty_req)

		assert res == self.successful_res
		assert g._exec_query.call_count == 4

	def test_too_many_errors(self):
		"""Test that exceeding the retries returns the error"""
		g = null_graph(self.normal_retry_policy)
		g._exec_query = Mock(side_effect=[self.failed_res] * 10)

		res = g.query(self.empty_req)

		assert res == self.failed_res
		assert g._exec_query.call_count == 1 + self.normal_retry_policy.retries


class TestPaginated:
	"""Test pagination works"""

	normal_retry_policy = RetryPolicy(retries=1)

	empty_req = Req("")
	res_pagination_cont = Res(empty_req, {}, [0], nextLink="my_next_link")
	res_pagination_end = Res(empty_req, {}, [1], nextLink=None)

	failed_res = ResErr("", "", None, {})

	def test_paginated_aggregates_res(self):
		"""Test that pagination requests more data"""
		g = null_graph(self.normal_retry_policy)
		g._make_http_request = Mock(side_effect=[self.res_pagination_cont, self.res_pagination_end])

		res = g.query(self.empty_req)

		assert isinstance(res, Res)
		assert len(res.value) == 2

	def test_retry_within_pagination(self):
		"""Test that a failure inside of pagination retries that request"""
		g = null_graph(self.normal_retry_policy)
		g._make_http_request = Mock(side_effect=[self.res_pagination_cont, self.failed_res, self.res_pagination_end])

		res = g.query(self.empty_req)

		assert isinstance(res, Res)
		assert len(res.value) == 2

	def test_failure_within_pagination(self):
		"""Test that a failure exceeding retries causes the failure to be propagated"""
		g = null_graph(self.normal_retry_policy)
		g._make_http_request = Mock(side_effect=[self.res_pagination_cont] * 2 + [self.failed_res] * 4 + [self.res_pagination_end])

		res = g.query(self.empty_req)

		assert isinstance(res, ResErr)
		assert g._make_http_request.call_count == 3 + self.normal_retry_policy.retries
