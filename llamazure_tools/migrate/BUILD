python_sources(
	dependencies=[":az_dashboards"],
)

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

adhoc_tool(
	name="az_workbooks",
	runnable="//llamazure/azrest/openapi.py",
	args=[
		"https://raw.githubusercontent.com/Azure/azure-rest-api-specs/main/",
		"specification/applicationinsights/resource-manager/Microsoft.Insights/stable/2023-06-01/workbooks_API.json",
		"llamazure_tools/migrate/az_dashboards.py",
	],
	output_files=["llamazure_tools/migrate/az_workooks.py"],
	root_output_directory=".",
)