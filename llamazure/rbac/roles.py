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
			print(f"delete {scope} {role}")
			self.Delete(scope, role.name)

	def delete_by_name(self, name: str):
		"""Delete a RoleDefinition by name from all the places it exists"""

		role = next((e for e in self.list_all_custom() if e.properties.roleName == name), None)
		if not role:
			return
		self.delete(role)

