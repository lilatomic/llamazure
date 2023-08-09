"""Azure Role Definitions and Assignments"""
from __future__ import annotations

from typing import Dict, Sequence

from llamazure.azrest.azrest import AzRest

RoleDefT = Dict
RoleAsnT = Dict


class RoleDefs:
	"""Interact with Azure RoleDefinitions"""

	provider_type = "Microsoft.Authorization/roleDefinitions"
	provider_slug = "/subscriptions/{subscription_id}/providers/Microsoft.Authorization/roleDefinitions"

	def __init__(self, azrest: AzRest):
		self.azrest = azrest

	def list_at_subscription(self, subscription_id) -> Sequence[RoleDefT]:
		"""Get roles at a subscription"""
		url = self.provider_slug.format(subscription_id=subscription_id)
		return self.azrest.get(url)
