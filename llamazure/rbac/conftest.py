"""Conftest"""
import os
import shutil

import pytest
import yaml
from azure.identity import AzureCliCredential, ClientSecretCredential

from llamazure.azrest.azrest import AzRest
from llamazure.rbac.roles import RoleAssignments, RoleDefinitions


@pytest.fixture
def credential():
	"""Azure credential"""
	if shutil.which("az"):
		return AzureCliCredential()
	else:
		secrets = yaml.safe_load(os.environ.get("integration_test_secrets"))
		client = secrets["azgraph"]
		return ClientSecretCredential(tenant_id=client["tenant"], client_id=client["appId"], client_secret=client["password"])


@pytest.fixture
def scopes():
	return yaml.safe_load(os.environ.get("integration_test_secrets"))["rbac"]["scopes"]


@pytest.fixture
def rds(credential) -> RoleDefinitions:
	"""Fixture: RoleDefinitions"""
	return RoleDefinitions(AzRest.from_credential(credential))


@pytest.fixture
def ras(credential) -> RoleAssignments:
	"""Fixture: RoleAssignments"""
	return RoleAssignments(AzRest.from_credential(credential))
