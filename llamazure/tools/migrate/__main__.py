import click

from llamazure.tools.migrate import dashboard, workbook


@click.group()
def migrate():
	pass


migrate.add_command(dashboard.migrate, name="dashboard")
migrate.add_command(dashboard.restore, name="dashboard-restore")
migrate.add_command(workbook.migrate, name="workbook")
migrate.add_command(workbook.restore, name="workbook-restore")

if __name__ == "__main__":
	migrate()
