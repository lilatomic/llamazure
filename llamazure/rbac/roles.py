"""Azure Role Definitions and Assignments"""
from __future__ import annotations

import dataclasses
from typing import Dict, List, cast
from uuid import uuid4

from pydantic import BaseModel, Field

from llamazure.azrest.azrest import AzRest
from llamazure.azrest.models import AzList, Req
from llamazure.rid import rid

RoleDefT = Dict
RoleAsnT = Dict


class Permission(BaseModel):
	actions: List[str] = []
	notActions: List[str] = []
	dataActions: List[str] = []
	notDataActions: List[str] = []


class RoleDefinition(BaseModel):
	class Properties(BaseModel):
		roleName: str
		type_: str = Field(alias="type", default="CustomRole")
		description: str
		permissions: List[Permission]
		assignableScopes: List[str] = []

	rid: str = Field(alias="id", default=None)
	name: str
	properties: Properties


class AzRoleDefinitions:
	"""Interact with Azure RoleDefinitions"""

	provider_type = "Microsoft.Authorization/roleDefinitions"
	apiv = "2022-04-01"

	def __init__(self, azrest: AzRest):
		self.azrest = azrest

	def Delete(self, scope: str, roleDefinitionId: str):
		req = Req.delete(
			f"{scope}/providers/Microsoft.Authorization/roleDefinitions/{roleDefinitionId}",
			self.apiv,
		)
		return self.azrest.call(req)

	def Get(self, scope: str, roleDefinitionId: str):
		req = Req.get(f"{scope}/providers/Microsoft.Authorization/roleDefinitions/{roleDefinitionId}", self.apiv, RoleDefinition)
		return self.azrest.call(req)

	def GetById(self, roleId: str):
		req = Req.get(f"{roleId}", self.apiv, RoleDefinition)
		return self.azrest.call(req)

	def CreateOrUpdate(self, scope, roleDefinitionId: str, roleDefinition: RoleDefinition) -> RoleDefinition:
		req = Req.put(f"{scope}/providers/Microsoft.Authorization/roleDefinitions/{roleDefinitionId}", self.apiv, roleDefinition, RoleDefinition)
		return self.azrest.call(req)

	def List(self, scope: str) -> List[RoleDefinition]:
		req = Req.get(f"{scope}/providers/Microsoft.Authorization/roleDefinitions", self.apiv, AzList[RoleDefinition])
		return self.azrest.call(req)


class RoleAssignment(BaseModel):
	class Properties(BaseModel):
		roleDefinitionId: str
		principalId: str
		principalType: str
		scope: str

	rid: str = Field(alias="id", default=None)
	name: str
	properties: Properties


class AzRoleAssignments:
	"""Interact with Azure RoleAssignments"""

	provider_type = "Microsoft.Authorization/roleAssignments"
	apiv = "2022-04-01"

	def __init__(self, azrest: AzRest):
		self.azrest = azrest

	def ListForSubscription(self, subscriptionId: str) -> List[RoleAssignment]:
		req = Req.get(
			f"subscriptions/{subscriptionId}/providers/Microsoft.Authorization/roleAssignments",
			self.apiv,
			AzList[RoleAssignment],
		)
		return self.azrest.call(req)

	def ListForResourceGroup(self, subscriptionId: str, resourceGroupName: str) -> List[RoleAssignment]:
		req = Req.get(
			f"subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Authorization/roleAssignments",
			self.apiv,
			AzList[RoleAssignment],
		)
		return self.azrest.call(req)

	def ListForResource(self, subscriptionId: str, resourceGroupName: str, resourceProviderNamespace: str, resourceType: str, resourceName: str) -> List[RoleAssignment]:
		req = Req.get(
			f"subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/{resourceProviderNamespace}/{resourceType}/{resourceName}/providers/Microsoft.Authorization/roleAssignments",
			self.apiv,
			AzList[RoleAssignment],
		)
		return self.azrest.call(req)

	def Get(self, scope: str, roleAssignmentName: str) -> RoleAssignment:
		req = Req.get(f"{scope}/providers/Microsoft.Authorization/roleAssignments/{roleAssignmentName}", self.apiv, RoleAssignment)
		return self.azrest.call(req)

	def Create(self, scope: str, roleAssignmentName: str, roleAssignment: RoleAssignment) -> RoleAssignment:
		req = Req.put(f"{scope}/providers/Microsoft.Authorization/roleAssignments/{roleAssignmentName}", self.apiv, roleAssignment, RoleAssignment)
		return self.azrest.call(req)

	def Delete(self, scope: str, roleAssignmentName: str):
		req = Req.delete(f"{scope}/providers/Microsoft.Authorization/roleAssignments/{roleAssignmentName}", self.apiv)
		return self.azrest.call(req)

	def ListForScope(self, scope: str) -> List[RoleAssignment]:
		req = Req.get(f"{scope}/providers/Microsoft.Authorization/roleAssignments", self.apiv, AzList[RoleAssignment])
		return self.azrest.call(req)

	def GetById(self, roleAssignmentId: str) -> RoleAssignment:
		req = Req.get(
			f"/{roleAssignmentId}",
			self.apiv,
			RoleAssignment,
		)
		return self.azrest.call(req)

	def CreateById(self, roleAssignmentId: str, roleAssignment: RoleAssignment) -> RoleAssignment:
		req = Req.put(f"/{roleAssignmentId}", self.apiv, roleAssignment, RoleAssignment)
		return self.azrest.call(req)

	def DeleteById(self, roleAssignmentId: str):
		req = Req.delete(
			f"/{roleAssignmentId}",
			self.apiv,
		)
		return self.azrest.call(req)


class RoleDefinitions(AzRoleDefinitions):
	"""More helpful role operations"""

	@staticmethod
	def rescope(role: RoleDefinition, scope: str):
		"""Rescope a role for the target scope"""
		role_obj = cast(rid.Resource, rid.parse(role.rid))

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
		return role.model_copy(update={"rid": new_rid})

	@staticmethod
	def by_name(roles: List[RoleDefinition]):
		return {e.properties.roleName.lower(): e for e in roles}

	def list_all_custom(self) -> List[RoleDefinition]:
		"""Custom roles may not appear at the root level if they aren't defined there unless you use a custom filter"""
		req = Req.get("/providers/Microsoft.Authorization/roleDefinitions", self.apiv, AzList[RoleDefinition]).add_params({"$filter": "type eq 'CustomRole'"})
		return self.azrest.call(req)

	def get_by_name(self, name: str) -> RoleDefinition:
		return self.by_name(self.list_all())[name]

	def list_all(self) -> List[RoleDefinition]:
		"""Find any type of role anywhere"""
		return [*self.list_all_custom(), *self.List("/")]

	def put(self, role: RoleDefinition.Properties, scope: str = "/") -> RoleDefinition:
		"""Create or update a RoleDefinition, handling all the edge cases"""

		# we search for all custom roles in case it exists but not at our desired scope
		existing_role: RoleDefinition = self.by_name(self.list_all_custom()).get(role.roleName, None)
		if existing_role:
			target_role = existing_role.model_copy(update={"properties": role})
			# copy assignable scopes
			if not role.assignableScopes:
				target_role.properties.assignableScopes = existing_role.properties.assignableScopes
		else:
			name = str(uuid4())
			target_role = RoleDefinition(name=name, properties=role)

		# ensure that the role definition scope is in the assignable scopes
		if scope not in target_role.properties.assignableScopes:
			target_role.properties.assignableScopes.append(scope)

		res = self.CreateOrUpdate(scope, target_role.name, target_role)
		return res

	def delete(self, role: RoleDefinition):
		"""Delete a RoleDefinition from all the places it exists"""

		# TODO: use batchable api
		for scope in role.properties.assignableScopes:
			self.Delete(scope, role.name)

	def delete_by_name(self, name: str):
		"""Delete a RoleDefinition by name from all the places it exists"""

		role = next((e for e in self.list_all_custom() if e.properties.roleName == name), None)
		if not role:
			return
		self.delete(role)


class RoleAssignments(AzRoleAssignments):
	def __init__(self, azrest: AzRest):
		self._role_definitions = RoleDefinitions(azrest)
		super().__init__(azrest)

	def list_for_role_at_scope(self, role_definition: RoleDefinition, scope: str) -> List[RoleAssignment]:
		rid_at_scope = self._role_definitions.rescope(role_definition, scope)
		asns_at_scope = self.ListForScope(scope)
		asns = [e for e in asns_at_scope if e.properties.roleDefinitionId.lower() == rid_at_scope.rid]
		return asns

	def list_for_role(self, role_definition: RoleDefinition) -> List[RoleAssignment]:
		"""Find assignments of a role at all scopes"""
		asns = []
		for scope in role_definition.properties.assignableScopes:
			rid_at_scope = self._role_definitions.rescope(role_definition, scope)
			asns_at_scope = self.ListForScope(scope)
			asns += [e for e in asns_at_scope if e.properties.roleDefinitionId.lower() == rid_at_scope.rid]
		return asns

	def assign(self, principalId: str, principalType: str, role_name: str, scope: str) -> RoleAssignment:
		"""Just grant a Principal a Role at a Scope, the way you always wanted"""
		# we need to search everywhere because the role might exist but not in our subscription yet
		role = self._role_definitions.get_by_name(role_name)

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

		existing = next((e for e in self.ListForScope(assignment.scope) if e.properties.roleDefinitionId == assignment.roleDefinitionId), None)
		if existing:
			target = existing.model_copy(update={"properties": assignment})
		else:
			name = str(uuid4())
			target = RoleAssignment(name=name, properties=assignment)

		res = self.Create(target.properties.scope, target.name, target)
		return res

	def remove_all_assignments(self, role_definition: RoleDefinition):
		"""
		Remove all assignments attached to a role.
		Useful for running before deleting a role
		"""
		asns = self.list_for_role(role_definition)
		for asn in asns:
			self.DeleteById(asn.rid)


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
