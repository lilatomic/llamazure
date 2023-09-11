"""Integration tests for roles"""
import itertools
import os
from time import sleep
from typing import Any

import pytest

from llamazure.azrest.azrest import AzureError
from llamazure.rbac.conftest import retry
from llamazure.rbac.roles import Permission, RoleAssignment, RoleAssignments, RoleDefinition, RoleDefinitions, RoleOps

attempts = 5


def print_output(name: str, output: Any):
	"""Print output if requested, so we don't always print potentially sensitive information to the logs"""
	should_print = os.environ.get("INTEGRATION_PRINT_OUTPUT", "False") == "True"
	if should_print:
		print(name, output)


class TestRoles:
	"""Test combined aspects of roles"""

	def test_nothing(self):
		"""Prevent collection problems for partitions"""

	@pytest.mark.integration
	def test_initialises(self, rds: RoleDefinitions, ras: RoleAssignments):
		"""Test that thing initialise"""
		pass

	@pytest.mark.integration
	def test_all(self, rds: RoleDefinitions, ras: RoleAssignments, role_ops: RoleOps, scopes):
		"""Test a whole cycle of things"""

		# try to purge role
		retry(lambda: role_ops.delete_by_name("llamazure-rbac"), AzureError)

		scope = scopes["sub0"]
		scope_other = scopes["sub1"]

		response = rds.put(
			RoleDefinition.Properties(
				roleName="llamazure-rbac",
				description="Test creating a role",
				permissions=[Permission(actions=["Microsoft.Authorization/*/read"])],
				assignableScopes=[scope, scope_other],
			),
			scope=scope,
		)

		def assert_role_created():
			role = rds.get_by_name("llamazure-rbac")
			assert role
			# compare the properties because that's what matters and `get_by_name` gives the root scope
			assert role.properties == response.properties
			return role

		role = retry(assert_role_created, {KeyError})

		def assert_role_assigned():
			asn = ras.put(RoleAssignment.Properties(roleDefinitionId=role.rid, principalId="094238bf-5cf8-412e-8773-8e2a39c45616", principalType="User", scope=scope))
			assert asn
			return asn

		asn = retry(assert_role_assigned, AzureError)

		ras.DeleteById(asn.rid)

		rds.delete_by_name(role.properties.roleName)

	@pytest.mark.integration
	def test_assign(self, rds: RoleDefinitions, ras: RoleAssignments, role_ops: RoleOps, me, scopes):
		role_name = "llamazure-rbac-asn"
		retry(lambda: role_ops.delete_by_name(role_name), AzureError)

		sub0, sub1 = scopes["sub0"], scopes["sub1"]

		role = rds.put(
			RoleDefinition.Properties(
				roleName="llamazure-rbac-asn",
				description="test finding assignments",
				permissions=[Permission(actions=["Microsoft.Authorization/*/read"])],
			),
			scope=sub0,
		)
		assert role
		assert role.rid.startswith(sub0)

		def mk_asn(scope):
			return dict(role_name=role.properties.roleName, principalId=me["id"], principalType="User", scope=scope)

		# Check assigning the roles and finding them
		def assert_assigned_on_sub0():
			ras.assign(**mk_asn(sub0))
			assignments = ras.list_for_role(role)
			assert len(assignments) == 1
			assert assignments[0].properties.scope == sub0

		retry(assert_assigned_on_sub0, {AssertionError, AzureError, KeyError})

		def assert_assigned_on_sub1():
			ras.assign(**mk_asn(sub1))
			role = rds.get_by_name(role_name)
			assignments = ras.list_for_role(role)
			assert len(assignments) == 2
			assert any(asn.properties.scope == sub1 for asn in assignments)
			return assignments

		retry(assert_assigned_on_sub1, {AssertionError, AzureError, KeyError})

		def exercise_listing_at_scope():
			role = rds.get_by_name(role_name)
			assignments_on_sub1 = ras.list_for_role_at_scope(role, sub1)
			assert len(assignments_on_sub1) == 1

		retry(exercise_listing_at_scope, {AssertionError, AzureError})

		# check removing assignments
		ras.remove_all_assignments(role)

		# cleanup
		role_ops.delete_by_name(role_name)
