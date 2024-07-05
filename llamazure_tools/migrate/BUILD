python_sources(
	dependencies=[":az"],
)

adhoc_tool(
	name="azgen",
	runnable="//llamazure/azrest/openapi.py",
	args=[
		"https://raw.githubusercontent.com/Azure/azure-rest-api-specs/main/",
		",".join(
			[
				"specification/portal/resource-manager/Microsoft.Portal/preview/2020-09-01-preview/portal.json",
				"specification/applicationinsights/resource-manager/Microsoft.Insights/stable/2023-06-01/workbooks_API.json",
			]
		),
		"llamazure_tools/migrate",
	],
	output_directories=["llamazure_tools/migrate"],
	root_output_directory=".",
)

experimental_wrap_as_python_sources(
	name="az",
	inputs=[":azgen"],
)
