from __future__ import annotations

from typing import Dict

from llamazure.rbac.resources import Groups, Users

GroupsT = Dict
UsersT = Dict


class Repository:
	def __init__(self, users: Dict[str, UsersT], groups: Dict[str, GroupsT]):
		self.users = users
		self.groups = groups

	@classmethod
	def initialise(cls, users: Users, groups: Groups) -> Repository:
		"""
		Create a repository from raw clients

		```python
		graph = Graph.from_credential(DefaultAzureCredential())
		repository = Repository.initialise(Users(graph), Groups(graph))
		```
		"""

		keyed_users = {user["id"]: user for user in users.list_with_memberOf()}
		keyed_groups = {group["id"]: group for group in groups.list_with_memberships()}

		return cls(
			*(
				keyed_users,
				keyed_groups,
			)
		)
