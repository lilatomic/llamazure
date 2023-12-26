"""Azure Role Definitions and Assignments"""
from __future__ import annotations

import dataclasses
import logging
from typing import List, Optional, cast
from uuid import uuid4

from llamazure.azrest.azrest import AzOps, AzRest, rid_eq
from llamazure.azrest.models import AzList, Req
from llamazure.rbac.role_asn import AzRoleAssignments, RoleAssignment, RoleAssignmentCreateParameters
from llamazure.rbac.role_def import AzRoleDefinitions, RoleDefinition
from llamazure.rid import rid

l = logging.getLogger(__name__)


class RoleDefinitions(AzRoleDefinitions, AzOps):
	"""More helpful role definitions operations"""

	@staticmethod
	def rescope_id(role: str, scope: str) -> str:
		"""
		Rescope a role's ID to belong to the correct scope.

		Roles are tenancy-wide, but have a different id
		based on which subscription the assignment is in
		(or if it targets a management group)
		"""
		role_obj = cast(rid.Resource, rid.parse(role))

		# Get the first segment of the path.
		# This is enough to tell us if we're in a subscription (the subscription or a resource in it)
		# or if we're targeting a management group
		target = next(rid.parse_gen(scope))
		if isinstance(target, rid.Subscription):
			# change select the version of the role in the subscription by setting its sub value
			role_obj_for_taget_scope = dataclasses.replace(role_obj, sub=target)
		else:
			# use the version of the role with no subscription
			role_obj_for_taget_scope = dataclasses.replace(role_obj, sub=None)
		new_rid = rid.serialise(role_obj_for_taget_scope)
		return new_rid

	@staticmethod
	def rescope(role: RoleDefinition, scope: str) -> RoleDefinition:
		"""Rescope a role for the target scope"""
		if not role.rid:
			raise TypeError(f"attempt to rescope role with no rid name={role.name}")
		new_rid = RoleDefinitions.rescope_id(role.rid, scope)
		rescoped_role = role.model_copy(update={"rid": new_rid})
		return rescoped_role

	@staticmethod
	def by_name(roles: List[RoleDefinition]):
		"""Index RoleDefinitions by their name"""
		return {e.properties.roleName.lower(): e for e in roles}  # type: ignore[union-attr]

	def list_all_custom(self) -> Req[List[RoleDefinition]]:
		"""Custom roles may not appear at the root level if they aren't defined there unless you use a custom filter"""
		return Req.get("list_all_custom_RoleDefinition", "/providers/Microsoft.Authorization/roleDefinitions", self.apiv, AzList[RoleDefinition]).add_params(
			{"$filter": "type eq 'CustomRole'"}
		)

	def get_by_name(self, name: str) -> RoleDefinition:
		"""Get a role by its name"""
		return self.by_name(self.list_all())[name]

	def list_all(self) -> List[RoleDefinition]:
		"""Find any type of role anywhere"""
		return [*self.run(self.list_all_custom()), *self.run(self.List("/"))]

	def put(self, role: RoleDefinition.Properties, scope: str = "/") -> RoleDefinition:
		"""Create or update a RoleDefinition, handling all the edge cases"""

		# we search for all custom roles in case it exists but not at our desired scope
		existing_role: RoleDefinition = self.by_name(self.run(self.list_all_custom())).get(role.roleName, None)
		if existing_role:
			l.debug(f"found RoleDefinition rid={existing_role.rid}")
			target_role = existing_role.model_copy(update={"properties": role})
			# copy assignable scopes
			if not role.assignableScopes:
				target_role.properties.assignableScopes = existing_role.properties.assignableScopes
		else:
			name = str(uuid4())
			l.debug(f"did not find RoleDefinition, using name={name}")
			target_role = RoleDefinition(name=name, properties=role)

		# ensure that the role definition scope is in the assignable scopes
		if scope not in target_role.properties.assignableScopes:
			l.debug("adding scope to RoleDefinition")
			target_role.properties.assignableScopes.append(scope)

		assert target_role.name, "typeguard failed guard=target_role.name"
		res = self.run(self.CreateOrUpdate(scope, target_role.name, target_role))
		return res

	def delete(self, role: RoleDefinition):
		"""Delete a RoleDefinition from all the places it exists"""

		# TODO: use batchable api
		for scope in role.properties.assignableScopes:
			assert role.name
			self.run(self.Delete(scope, role.name))

	def delete_by_name(self, name: str):
		"""Delete a RoleDefinition by name from all the places it exists"""

		role = next((e for e in self.run(self.list_all_custom()) if e.properties.roleName == name), None)
		if not role:
			return
		self.delete(role)


class RoleAssignments(AzRoleAssignments, AzOps):
	"""More helpful role assignment operations"""

	def __init__(self, azrest: AzRest):
		self._role_definitions = RoleDefinitions(azrest)
		super().__init__(azrest)

	def list_for_role_at_scope(self, role_definition: RoleDefinition, scope: str) -> List[RoleAssignment]:
		"""List assignments for a role at a given scope"""
		rid_at_scope = self._role_definitions.rescope(role_definition, scope)
		asns_at_scope = self.ListForScope(scope)
		asns = [e for e in self.run(asns_at_scope) if e.properties.roleDefinitionId.lower() == rid_at_scope.rid]  # type: ignore[union-attr]
		return asns

	def list_for_role(self, role_definition: RoleDefinition) -> List[RoleAssignment]:
		"""Find assignments of a role at all scopes"""
		asns = []
		for scope in role_definition.properties.assignableScopes:
			rid_at_scope = self._role_definitions.rescope(role_definition, scope)
			asns_at_scope = self.ListForScope(scope)
			asns += [e for e in self.run(asns_at_scope) if rid_eq(e.properties.roleDefinitionId, rid_at_scope.rid)]
		return asns

	def assign(self, principalId: str, principalType: str, role_name: str, scope: str) -> RoleAssignment:
		"""Just grant a Principal a Role at a Scope, the way you always wanted"""
		# we need to search everywhere because the role might exist but not in our subscription yet
		role = self._role_definitions.get_by_name(role_name)
		if not role.properties.assignableScopes:
			raise TypeError(f"Existing role {role.rid} did not have any assignable scopes")  # TODO: custom error type for preconditions

		# we might need to update the assignable scopes
		if scope not in role.properties.assignableScopes:
			role = self._role_definitions.put(
				role.properties.model_copy(update={"assignableScopes": [scope, *role.properties.assignableScopes]}),
				scope=role.properties.assignableScopes[0],  # we take one of the existing assignable scopes. They all work
			)

		assignment = RoleAssignment.Properties(
			roleDefinitionId=self._role_definitions.rescope(role, scope).rid,
			principalId=principalId,
			principalType=principalType,
			scope=scope,
		)
		return self.put(assignment)

	def put(self, assignment: RoleAssignment.Properties) -> RoleAssignment:
		"""Create or update a role assignment"""
		if not assignment.scope:  # TODO: Azure mandatory
			raise TypeError("RoleAssignment did not have a scope")
		if not assignment.roleDefinitionId:  # TODO: Azure mandatory
			raise TypeError("RoleAssignment did not have a roleDefinitionId")

		target_role_id = self._role_definitions.rescope_id(assignment.roleDefinitionId, assignment.scope)
		assignments_at_scope = self.run(self.ListForScope(assignment.scope))
		existing: Optional[RoleAssignment] = next(
			(e for e in assignments_at_scope if rid_eq(e.properties.roleDefinitionId, target_role_id) and e.properties.principalId == assignment.principalId),
			None,
		)
		if existing:
			target_name = existing.name
			l.debug(f"found existing role assignment rid={existing.rid}")
			target = existing.model_copy(update={"properties": assignment})
		else:
			target_name = str(uuid4())
			l.debug(f"did not find existing role assignment, trying for name={target_name}")
			target = RoleAssignment(name=target_name, properties=assignment)

		scope = target.properties.scope
		if scope is None or target_name is None:
			raise ValueError(f"invalid target was unassignable {scope=} {target_name=}")
		res = self.run(self.Create(scope, target_name, RoleAssignmentCreateParameters(properties=RoleAssignmentCreateParameters.Properties(**target.properties.model_dump()))))
		return res

	def remove_all_assignments(self, role_definition: RoleDefinition):
		"""
		Remove all assignments attached to a role.
		Useful for running before deleting a role
		"""
		asns = self.list_for_role(role_definition)
		l.debug(f"delete assignments for role name={role_definition.properties.roleName} count={len(asns)}")
		for asn in asns:
			if asn.rid:
				self.run(self.DeleteById(asn.rid))
			else:
				l.warning("asked to delete RoleAssignment with no rid")


class RoleOps:
	"""The most helpful operations, roles and role assignments working together"""

	def __init__(self, azrest: AzRest):
		self.ras = RoleAssignments(azrest)
		self.rds = RoleDefinitions(azrest)

	def delete_role(self, role: RoleDefinition):
		"""Delete a role properly by removing its assignments beforehand"""
		self.ras.remove_all_assignments(role)
		self.rds.delete(role)

	def delete_by_name(self, role_name: str):
		"""Delete a role by name properly by removing its assignments beforehand"""
		try:
			role = self.rds.get_by_name(role_name)
			self.delete_role(role)
		except KeyError:
			# already gone
			pass
