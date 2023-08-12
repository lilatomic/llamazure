"""Azure Role Definitions and Assignments"""
from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field

from llamazure.azrest.azrest import AzRest

RoleDefT = Dict
RoleAsnT = Dict


class Permission(BaseModel):
	actions: List[str]
	notActions: List[str]
	dataActions: List[str]
	notDataActions: List[str]


class RoleDefinition(BaseModel):
	class Properties(BaseModel):
		roleName: str
		type_: str = Field(alias="type")
		description: str
		permissions: List[Permission]
		assignableScopes: List[str]

	rid: str = Field(alias="id")
	name: str
	type_: str = Field(alias="type")
	properties: Properties


class RoleDefinitions:
	"""Interact with Azure RoleDefinitions"""

	provider_type = "Microsoft.Authorization/roleDefinitions"
	apiv = "2022-04-01"

	def __init__(self, azrest: AzRest):
		self.azrest = azrest

	def Delete(self, scope: str, roleDefinitionId: str):
		slug = f"/{scope}/providers/Microsoft.Authorization/roleDefinitions/{roleDefinitionId}"
		return self.azrest.delete(slug, self.apiv)

	def Get(self, scope: str, roleDefinitionId: str):
		slug = f"/{scope}/providers/Microsoft.Authorization/roleDefinitions/{roleDefinitionId}"
		ret = self.azrest.get(slug, self.apiv)
		return RoleDefinition(**ret)

	def GetById(self, roleId: str):
		slug = f"{roleId}"
		ret = self.azrest.get(slug, self.apiv)
		return RoleDefinition(**ret)

	def CreateOrUpdate(self, scope, roleDefinitionId: str, roleDefinition: RoleDefinition):
		slug = f"/{scope}/providers/Microsoft.Authorization/roleDefinitions/{roleDefinitionId}"
		return self.azrest.put(slug, self.apiv, roleDefinition)

	def List(self, scope: str):
		slug = f"/{scope}/providers/Microsoft.Authorization/roleDefinitions"
		return self.azrest.get(slug, self.apiv)
