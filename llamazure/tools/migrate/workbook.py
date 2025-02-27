"""Migrate an Azure Workbook to a different Log Analytics Workspace"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import click
from azure.identity import DefaultAzureCredential

from llamazure.azrest.azrest import AzRest
from llamazure.azrest.models import cast_as
from llamazure.rid import rid
from llamazure.rid.rid import Resource
from llamazure.tools.migrate.applicationinsights.r.m.insights.workbooks import AzWorkbooks, Workbook, WorkbookUpdateParameters  # pylint: disable=E0611,E0401
from llamazure.tools.migrate.util import JSONTraverser, rid_params


@dataclass
class Migrator:
	"""Migrate an Azure Workbook"""

	az: AzRest
	workbook: Resource
	transformer: JSONTraverser
	backup_directory: Path

	def migrate(self):
		"""Perform the migration"""
		workbook = self.get_workbook()
		print(workbook.model_dump_json(indent=2))
		self.make_backup(workbook)
		transformed = self.transform(workbook)
		self.put_workbook(transformed)

	def get_workbook(self) -> Workbook:
		"""Retrieve the current workbook data from Azure."""
		return self.az.call(AzWorkbooks.Get(*rid_params(self.workbook), canFetchContent=True))

	def transform(self, workbook: Workbook) -> Workbook:
		"""Transform the workbook data using the provided transformer."""
		workbook.properties.serializedData = json.dumps(self.transformer.traverse(json.loads(workbook.properties.serializedData)))
		return workbook

	def put_workbook(self, transformed: Workbook):
		"""Update the dashboard in Azure with the transformed data."""
		self.az.call(
			AzWorkbooks.Update(*rid_params(self.workbook), cast_as(transformed, WorkbookUpdateParameters)),
		)

	def make_backup(self, workbook: Workbook):
		"""Create a backup of the current dashboard data."""
		filename = self.backup_directory / Path(self.workbook.name + datetime.utcnow().isoformat()).with_suffix(".json")
		with open(filename, "w") as f:
			f.write(workbook.model_dump_json(indent=2))


@dataclass
class Restorer:
	az: AzRest
	workbook: Resource
	backup: Path

	def restore(self):
		content = self.load_backup()
		self.put_dashboard(content)

	def load_backup(self):
		with open(self.backup, "r", encoding="utf-8") as f:
			return json.load(f)

	def put_dashboard(self, content: dict):
		self.az.call(
			AzWorkbooks.Update(*rid_params(self.workbook), WorkbookUpdateParameters(**content)),
		)


@click.command()
@click.option("--resource-id", help="The ID of the workbook to migrate.")
@click.option("--replacements", help="A JSON string of the replacements to apply.")
@click.option("--backup-directory", type=click.Path(), help="The directory where backups will be stored.")
def migrate(resource_id: str, replacements: str, backup_directory: str):
	"""Migrate an Azure Workbook to a different Log Analytics Workspace"""
	az = AzRest.from_credential(DefaultAzureCredential())

	replacements = json.loads(replacements)
	assert isinstance(replacements, dict)
	resource = rid.parse(resource_id)
	assert isinstance(resource, rid.Resource)
	transformer = JSONTraverser(replacements)
	migrator = Migrator(az, resource, transformer, Path(backup_directory))

	migrator.migrate()


@click.command()
@click.option("--resource-id", help="The ID of the workbook to restore.")
@click.option("--backup", type=click.Path(exists=True, file_okay=True, dir_okay=False), help="The backup of the workbook to restore")
def restore(resource_id: str, backup: str):
	"""Restore the workbook data."""
	az = AzRest.from_credential(DefaultAzureCredential())
	resource = rid.parse(resource_id)
	assert isinstance(resource, rid.Resource)
	restorer = Restorer(az, resource, Path(backup))

	restorer.restore()


if __name__ == "__main__":
	migrate()  # pylint: disable=no-value-for-parameter
