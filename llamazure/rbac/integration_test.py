"""Integration tests for roles"""
import os
from typing import Any

import pytest

from llamazure.rbac.roles import Permission, RoleAssignment, RoleAssignments, RoleDefinition, RoleDefinitions


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
	def test_all(self, rds: RoleDefinitions, ras: RoleAssignments, scopes):
		"""Test a whole cycle of things"""

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
		role = rds.get_by_name("llamazure-rbac", scope)
		assert role
		assert role == response

		asn = ras.put(RoleAssignment.Properties(roleDefinitionId=role.rid, principalId="094238bf-5cf8-412e-8773-8e2a39c45616", principalType="User", scope=scope))
		assert asn
		ras.DeleteById(asn.rid)

		rds.delete_by_name(role.properties.roleName)
