python_sources()

adhoc_tool(
	name="az_dashboards",
	runnable="//llamazure/azrest/openapi.py",
	args=[
		"https://raw.githubusercontent.com/Azure/azure-rest-api-specs/main/",
		"specification/portal/resource-manager/Microsoft.Portal/preview/2020-09-01-preview/portal.json",
		"llamazure_tools/migrate/az_dashboards.py",
	],
	output_files=["llamazure_tools/migrate/az_dashboards.py"],
	root_output_directory=".",
)