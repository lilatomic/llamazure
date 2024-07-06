import json
import os
from pathlib import Path
from typing import Dict

import pytest
import yaml
from azure.identity import AzureCliCredential, ClientSecretCredential, CredentialUnavailableError

from llamazure.azrest.azrest import AzRest
from llamazure.rid import rid
from llamazure_tools.migrate import dashboard, workbook
from llamazure_tools.migrate.applicationinsights.r.m.insights.workbooks import Workbook  # pylint: disable=E0611,E0401
from llamazure_tools.migrate.util import JSONTraverser


def test_shim():
	"""Make pytest succeed even when no tests are selected"""


@pytest.fixture
def it_info():
	"""Fixture: Bundle of config for integration tests"""
	secrets = os.environ.get("integration_test_secrets")
	if not secrets:
		with open("cicd/secrets.yml", mode="r", encoding="utf-8") as f:
			secrets = f.read()
	return yaml.safe_load(secrets)["tools_migrate"]


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


class TestDashboard:
	@pytest.mark.integration
	def test_dashboard(self, it_info, credential, tmp_path):
		az = AzRest.from_credential(credential)

		resource = rid.parse(it_info["dashboard"])
		assert isinstance(resource, rid.Resource)

		m = dashboard.Migrator(az, resource, JSONTraverser({"aaa": "bbb", "bbb": "aaa"}), Path(tmp_path))

		old = m.get_dashboard()
		m.migrate()
		new = m.get_dashboard()

		def get_replacement(d: Dict):
			return d["properties"]["lenses"][0]["parts"][1]["metadata"]["settings"]["content"]["title"]

		assert get_replacement(new) != get_replacement(old)


class TestWorkbook:
	@pytest.mark.integration
	def test_workbook(self, it_info, credential, tmp_path):
		az = AzRest.from_credential(credential)

		resource = rid.parse(it_info["workbook"])
		assert isinstance(resource, rid.Resource)

		m = workbook.Migrator(az, resource, JSONTraverser({"aaa": "bbb", "bbb": "aaa"}), Path(tmp_path))

		old = m.get_workbook()
		m.migrate()
		new = m.get_workbook()

		def get_replacement(w: Workbook):
			return json.loads(w.properties.serializedData)["items"][0]["content"]["query"]

		assert get_replacement(old) != get_replacement(new)
