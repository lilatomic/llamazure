"""Azure Role Definitions and Assignments"""
from __future__ import annotations

from typing import Dict, List
from uuid import uuid4

from pydantic import BaseModel, Field

from llamazure.azrest.azrest import AzRest

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
	name: str = None
	properties: Properties


class AzRoleDefinitions:
	"""Interact with Azure RoleDefinitions"""

	provider_type = "Microsoft.Authorization/roleDefinitions"
	apiv = "2022-04-01"

	def __init__(self, azrest: AzRest):
		self.azrest = azrest

	def Delete(self, scope: str, roleDefinitionId: str):
		slug = f"{scope}/providers/Microsoft.Authorization/roleDefinitions/{roleDefinitionId}"
		return self.azrest.delete(slug, self.apiv)

	def Get(self, scope: str, roleDefinitionId: str):
		slug = f"{scope}/providers/Microsoft.Authorization/roleDefinitions/{roleDefinitionId}"
		ret = self.azrest.get(slug, self.apiv)
		return RoleDefinition(**ret)

	def GetById(self, roleId: str):
		slug = f"{roleId}"
		ret = self.azrest.get(slug, self.apiv)
		return RoleDefinition(**ret)

	def CreateOrUpdate(self, scope, roleDefinitionId: str, roleDefinition: RoleDefinition) -> RoleDefinition:
		slug = f"{scope}/providers/Microsoft.Authorization/roleDefinitions/{roleDefinitionId}"
		ret = self.azrest.put(slug, self.apiv, roleDefinition)
		return RoleDefinition(**ret)

	def List(self, scope: str) -> List[RoleDefinition]:
		slug = f"{scope}/providers/Microsoft.Authorization/roleDefinitions"
		ret = self.azrest.get(slug, self.apiv)
		return [RoleDefinition(**e) for e in ret["value"]]


class RoleAssignment(BaseModel):
	class Properties(BaseModel):
		roleDefinitionId: str
		principalId: str
		principalType: str
		scope: str
	rid: str = Field(alias="id", default=None)
	name: str = None
	properties: Properties


class AzRoleAssignments:
	"""Interact with Azure RoleAssignments"""

	provider_type = "Microsoft.Authorization/roleAssignments"
	apiv = "2022-04-01"

	def __init__(self, azrest: AzRest):
		self.azrest = azrest

	def ListForSubscription(self, subscriptionId: str) -> List[RoleAssignment]:
		slug = f"subscriptions/{subscriptionId}/providers/Microsoft.Authorization/roleAssignments"
		return [RoleAssignment(**e) for e in self.azrest.get(slug, self.apiv)["value"]]

	def ListForResourceGroup(self, subscriptionId: str, resourceGroupName: str) -> List[RoleAssignment]:
		slug = f"subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Authorization/roleAssignments"
		return [RoleAssignment(**e) for e in self.azrest.get(slug, self.apiv)["value"]]

	def ListForResource(self, subscriptionId: str, resourceGroupName: str, resourceProviderNamespace: str, resourceType: str, resourceName: str) -> List[RoleAssignment]:
		slug = f"subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/{resourceProviderNamespace}/{resourceType}/{resourceName}/providers/Microsoft.Authorization/roleAssignments"
		return [RoleAssignment(**e) for e in self.azrest.get(slug, self.apiv)["value"]]

	def Get(self, scope: str, roleAssignmentName: str) -> RoleAssignment:
		slug = f"{scope}/providers/Microsoft.Authorization/roleAssignments/{roleAssignmentName}"
		return RoleAssignment(**self.azrest.get(slug, self.apiv))

	def Create(self, scope: str, roleAssignmentName: str, roleAssignment: RoleAssignment) -> RoleAssignment:
		slug = f"{scope}/providers/Microsoft.Authorization/roleAssignments/{roleAssignmentName}"
		return RoleAssignment(**self.azrest.put(slug, self.apiv, roleAssignment))

	def Delete(self, scope: str, roleAssignmentName: str):
		slug = f"{scope}/providers/Microsoft.Authorization/roleAssignments/{roleAssignmentName}"
		return self.azrest.delete(slug, self.apiv)

	def ListForScope(self, scope: str) -> List[RoleAssignment]:
		slug = f"{scope}/providers/Microsoft.Authorization/roleAssignments"
		return [RoleAssignment(**e) for e in self.azrest.get(slug, self.apiv)["value"]]

	def GetById(self, roleAssignmentId: str) -> RoleAssignment:
		slug = f"/{roleAssignmentId}"
		return RoleAssignment(**self.azrest.get(slug, self.apiv))

	def CreateById(self, roleAssignmentId: str, roleAssignment: RoleAssignment) -> RoleAssignment:
		slug = f"/{roleAssignmentId}"
		return RoleAssignment(**self.azrest.put(slug, self.apiv, roleAssignment))

	def DeleteById(self, roleAssignmentId: str):
		slug = f"/{roleAssignmentId}"
		return self.azrest.delete(slug, self.apiv)


class RoleDefinitions(AzRoleDefinitions):
	"""More helpful role operations"""

	def by_name(self, scope: str):
		return {e.properties.roleName: e for e in self.List(scope)}

	def list_all_custom(self):
		"""Custom roles may not appear at the root level if they aren't defined there unless you use a custom filter"""
		slug = "/providers/Microsoft.Authorization/roleDefinitions?$filter=type+eq+\'CustomRole\'"
		ret = self.azrest.get(slug, self.apiv)
		return [RoleDefinition(**e) for e in ret["value"]]

	def get_by_name(self, name: str, scope: str = "/") -> RoleDefinition:
		return self.by_name(scope)[name]

	def put(self, role: RoleDefinition.Properties, scope: str = "/") -> RoleDefinition:
		"""Create or update a RoleDefinition, handling all the edge cases"""

		existing_role: RoleDefinition = self.by_name(scope).get(role.roleName, None)
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

		for scope in role.properties.assignableScopes:
			self.Delete(scope, role.name)

	def delete_by_name(self, name: str):
		"""Delete a RoleDefinition by name from all the places it exists"""

		role = next((e for e in self.list_all_custom() if e.properties.roleName == name), None)
		if not role:
			return
		self.delete(role)


class RoleAssignments(AzRoleAssignments):

	def list_for_role_at_scope(self, role_definition: RoleDefinition, scope: str) -> List[RoleAssignment]:
		asns_at_scope = self.ListForScope(scope)
		asns = [e for e in asns_at_scope if e.properties.roleDefinitionId == role_definition.rid]
		return asns

	def list_for_role(self, role_definition: RoleDefinition) -> List[RoleAssignment]:
		"""Find assignments of a role at all scopes"""
		asns = []
		for scope in role_definition.properties.assignableScopes:
			asns_at_scope = self.ListForScope(scope)
			asns += [e for e in asns_at_scope if e.properties.roleDefinitionId == role_definition.rid]
		return asns

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
