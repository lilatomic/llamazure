"""Conftest"""
import os
from time import sleep
from typing import Callable, Set, Type, TypeVar, Union

import pytest
import yaml
from azure.identity import AzureCliCredential, ClientSecretCredential, CredentialUnavailableError

from llamazure.azrest.azrest import AzRest
from llamazure.msgraph.msgraph import Graph
from llamazure.rbac.resources import Groups, Users
from llamazure.rbac.roles import RoleAssignments, RoleDefinitions, RoleOps


@pytest.fixture
def credential():
	"""Azure credential"""
	try:
		return AzureCliCredential()
	except CredentialUnavailableError:
		secrets = yaml.safe_load(os.environ.get("integration_test_secrets"))
		client = secrets["azgraph"]
		return ClientSecretCredential(tenant_id=client["tenant"], client_id=client["appId"], client_secret=client["password"])


@pytest.fixture
def scopes():
	secrets = os.environ.get("integration_test_secrets")
	if not secrets:
		with open("cicd/secrets.yml", mode="r", encoding="utf-8") as f:
			secrets = f.read()
	return yaml.safe_load(secrets)["rbac"]["scopes"]


@pytest.fixture
def rds(credential) -> RoleDefinitions:
	"""Fixture: RoleDefinitions"""
	return RoleDefinitions(AzRest.from_credential(credential))


@pytest.fixture
def ras(credential) -> RoleAssignments:
	"""Fixture: RoleAssignments"""
	return RoleAssignments(AzRest.from_credential(credential))


@pytest.fixture
def role_ops(credential) -> RoleOps:
	"""Fixture: RoleOps"""
	return RoleOps(AzRest.from_credential(credential))


@pytest.fixture
def users(credential) -> Users:
	"""Fixture: Users"""
	return Users(Graph.from_credential(credential))


@pytest.fixture
def groups(credential) -> Groups:
	"""Fixture: Users"""
	return Groups(Graph.from_credential(credential))


@pytest.fixture
def me(users):
	"""Fixture: the current user"""
	return users.current()


T = TypeVar("T")


def retry(
	fn: Callable[[], T],
	catching: Union[Type[Exception], Set[Type[Exception]]],
	attempts=20,
) -> T:
	"""Retry a function catching specific exceptions. Useful for waiting for changes to propagate in Azure"""
	if isinstance(catching, type) and issubclass(catching, Exception):
		catching = {catching}

	i = 0
	while True:
		i += 1
		try:
			return fn()
		except Exception as e:
			if type(e) not in catching or i >= attempts:
				raise
			sleep(1)
