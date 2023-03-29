from __future__ import annotations

from typing import Dict, List

from llamazure.rbac.resources import Groups, Users


class Repository:
	def __init__(self, users: Dict, groups: Dict):
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
		return cls(
			{user["id"]: user for user in users.list()},
			{group["id"]: group for group in groups.list_with_members()},
		)
