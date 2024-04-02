import os

import yaml
from azure.identity import AzureCliCredential, ClientSecretCredential, CredentialUnavailableError


def load_credentials():
	"""Load credentials for a Service Principal"""
	try:
		cli_credential = AzureCliCredential()
		cli_credential.get_token("https://management.azure.com//.default")
		return cli_credential
	except CredentialUnavailableError:
		secrets = os.environ.get("integration_test_secrets")
		if not secrets:
			with open("cicd/secrets.yml", mode="r", encoding="utf-8") as f:
				secrets = f.read()
		secrets = yaml.safe_load(secrets)

		client = secrets["auth"]

		credential = ClientSecretCredential(tenant_id=client["tenant"], client_id=client["appId"], client_secret=client["password"])
		return credential
