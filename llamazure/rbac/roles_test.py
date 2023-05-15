"""Tests for Azure Role Definitions and Assignments"""
import os

import pytest as pytest
import yaml
from azure.identity import ClientSecretCredential

from llamazure.rbac.roles import AzRest, RoleDefs


@pytest.fixture
def az_rest():
	secrets = yaml.safe_load(os.environ.get("integration_test_secrets"))
	client = secrets["azgraph"]

	credential = ClientSecretCredential(tenant_id=client["tenant"], client_id=client["appId"], client_secret=client["password"])

	return AzRest.from_credential(credential)


@pytest.fixture
def target_subscription():
	return os.environ.get("integration_test_subscription")


class TestRoles:
	def test_none(self):
		...

	@pytest.mark.integration
	def test_get_for_subscription(self, az_rest, target_subscription):
		iroles = RoleDefs(az_rest)

		roles = iroles.list_at_subscription(target_subscription)
		assert len(roles) > 0
