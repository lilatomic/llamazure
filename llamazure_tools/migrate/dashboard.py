import dataclasses
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import click

from llamazure.azrest.azrest import AzRest
from llamazure.rid import rid
from llamazure.rid.rid import Resource
from llamazure_tools.migrate.az_dashboards import AzDashboards, Dashboard, PatchableDashboard


@dataclass
class JSONTraverser:
	replacements: Dict[str, str]

	def traverse(self, obj: Any) -> Any:
		if isinstance(obj, dict):
			return {key: self.traverse(value) for key, value in obj.items()}
		elif isinstance(obj, list):
			return [self.traverse(item) for item in obj]
		elif isinstance(obj, str):
			return self.replacements.get(obj, obj)
		else:
			return obj


@dataclass
class Migrator:
	az: AzRest
	dashboard: Resource
	transformer: JSONTraverser
	root_directory: Path

	def migrate(self):
		dashboard = self.get_dashboard()
		self.make_backup(dashboard)
		transformed = self.transform(dashboard)
		self.put_dashboard(transformed)

	def get_dashboard(self) -> dict:
		return self.az.call(dataclasses.replace(AzDashboards.Get(self.dashboard.sub, self.dashboard.rg, self.dashboard.name), ret_t=dict))

	def transform(self, dashboard: dict) -> dict:
		return self.transformer.traverse(dashboard)

	def put_dashboard(self, transformed: dict):
		d = Dashboard(**transformed)
		p = PatchableDashboard(
			properties=d.properties,
			tags=d.tags,
		)
		self.az.call(
			AzDashboards.Update(self.dashboard.sub, self.dashboard.rg, self.dashboard.name, p),
		)

	def make_backup(self, dashboard):
		filename = Path(self.dashboard.name + datetime.utcnow().isoformat()).with_suffix(".json")
		with open(filename, "w") as f:
			json.dump(dashboard, f)


@click.command()
@click.argument("dashboard_id", help="The ID of the dashboard to migrate.")
@click.argument("replacements", help="A JSON string of the replacements to apply.")
@click.argument("backup_directory", type=click.Path(), help="The directory where backups will be stored.")
def migrate(dashboard_id: str, replacements: str, backup_directory: str):
	from azure.identity import DefaultAzureCredential

	az = AzRest.from_credential(DefaultAzureCredential())

	replacements = json.loads(replacements)
	resource = rid.parse(dashboard_id)
	transformer = JSONTraverser(replacements)
	migrator = Migrator(az, resource, transformer, Path(backup_directory))

	migrator.migrate()


if __name__ == "__main__":
	migrate()  # pylint: disable=no-value-for-parameter
