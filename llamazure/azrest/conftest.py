import os
import shutil

import pytest
import yaml
from azure.identity import AzureCliCredential, ClientSecretCredential


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
def it_info():
	secrets = os.environ.get("integration_test_secrets")
	if not secrets:
		with open("cicd/secrets.yml", mode="r", encoding="utf-8") as f:
			secrets = f.read()
	return yaml.safe_load(secrets)["azrest"]
