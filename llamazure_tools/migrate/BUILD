python_sources(
	dependencies=[":az"],
)

adhoc_tool(
	name="az",
	runnable="//llamazure/azrest/openapi.py",
	args=[
		"https://raw.githubusercontent.com/Azure/azure-rest-api-specs/main/",
		",".join(["specification/portal/resource-manager/Microsoft.Portal/preview/2020-09-01-preview/portal.json","specification/applicationinsights/resource-manager/Microsoft.Insights/stable/2023-06-01/workbooks_API.json"]),
		"llamazure_tools/migrate/az_dashboards",
	],
	output_directories=["llamazure_tools/migrate/az_dashboards"],
	root_output_directory=".",
)
