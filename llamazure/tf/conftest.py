import os

import pytest
import yaml


@pytest.fixture
def it_info():
	"""Fixture: Bundle of config for integration tests"""
	secrets = os.environ.get("integration_test_secrets")
	if not secrets:
		with open("cicd/secrets.yml", mode="r", encoding="utf-8") as f:
			secrets = f.read()
	return yaml.safe_load(secrets)
