"""Migrate an Azure Dashboard to a different Log Analytics Workspace"""
import dataclasses
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import click
from azure.identity import DefaultAzureCredential

from llamazure.azrest.azrest import AzRest
from llamazure.rid import rid
from llamazure.rid.rid import Resource
from llamazure_tools.migrate.az_dashboards.portal.r.m.portal.portal import AzDashboards, Dashboard, PatchableDashboard  # pylint: disable=E0611,E0401
from llamazure_tools.migrate.util import JSONTraverser


@dataclass
class Migrator:
	"""Migrate an Azure Dashboard"""

	az: AzRest
	dashboard: Resource
	transformer: JSONTraverser
	backup_directory: Path

	def migrate(self):
		"""
		Perform the migration: get the dashboard, make a backup, transform it, and update it.
		"""
		dashboard = self.get_dashboard()
		self.make_backup(dashboard)
		transformed = self.transform(dashboard)
		self.put_dashboard(transformed)

	def get_dashboard(self) -> dict:
		"""Retrieve the current dashboard data from Azure."""
		return self.az.call(dataclasses.replace(AzDashboards.Get(self.dashboard.sub.uuid, self.dashboard.rg.name, self.dashboard.name), ret_t=dict))

	def transform(self, dashboard: dict) -> dict:
		"""Transform the dashboard data using the provided transformer."""
		return self.transformer.traverse(dashboard)

	def put_dashboard(self, transformed: dict):
		"""Update the dashboard in Azure with the transformed data."""
		d = Dashboard(**transformed)
		p = PatchableDashboard(
			properties=d.properties.model_dump(),
			tags=d.tags,
		)
		self.az.call(
			AzDashboards.Update(self.dashboard.sub.uuid, self.dashboard.rg.name, self.dashboard.name, p),
		)

	def make_backup(self, dashboard: dict):
		"""Create a backup of the current dashboard data."""
		filename = self.backup_directory / Path(self.dashboard.name + datetime.utcnow().isoformat()).with_suffix(".json")
		with open(filename, "w", encoding="utf-8") as f:
			json.dump(dashboard, f)


@click.command()
@click.option("--resource-id", help="The ID of the dashboard to migrate.")
@click.option("--replacements", help="A JSON string of the replacements to apply.")
@click.option("--backup-directory", type=click.Path(), help="The directory where backups will be stored.")
def migrate(resource_id: str, replacements: str, backup_directory: str):
	"""Migrate an Azure Dashboard to a different Log Analytics Workspace"""
	az = AzRest.from_credential(DefaultAzureCredential())

	replacements = json.loads(replacements)
	resource = rid.parse(resource_id)
	transformer = JSONTraverser(replacements)
	migrator = Migrator(az, resource, transformer, Path(backup_directory))

	migrator.migrate()


if __name__ == "__main__":
	migrate()  # pylint: disable=no-value-for-parameter
