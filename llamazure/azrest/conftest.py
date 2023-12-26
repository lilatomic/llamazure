"""Conftest"""
import os

import pytest
import yaml
from azure.identity import AzureCliCredential, ClientSecretCredential, CredentialUnavailableError


@pytest.fixture
def credential():
	"""Azure credential"""
	try:
		cli_credential = AzureCliCredential()
		cli_credential.get_token("https://management.azure.com//.default")
		return cli_credential
	except CredentialUnavailableError:
		secrets = yaml.safe_load(os.environ.get("integration_test_secrets"))
		client = secrets["azgraph"]
		return ClientSecretCredential(tenant_id=client["tenant"], client_id=client["appId"], client_secret=client["password"])


@pytest.fixture
def it_info():
	"""Fixture: Bundle of config for integration tests"""
	secrets = os.environ.get("integration_test_secrets")
	if not secrets:
		with open("cicd/secrets.yml", mode="r", encoding="utf-8") as f:
			secrets = f.read()
	return yaml.safe_load(secrets)["azrest"]


@pytest.fixture
def tmp_file(tmp_path):
	"""Fixture: a temporary file"""
	return tmp_path / "out.py"
