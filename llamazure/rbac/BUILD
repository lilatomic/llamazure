python_sources(
	name="rbac",
	dependencies=[":azgen"],
)

python_tests(
	name="tests",
	sources=["*_test.py", "!integration*"],
)

python_tests(
	name="integration-tests",
	sources=["integration_test.py"],
	tags=["integration"],
)

python_test_utils(
	name="test_utils",
)

adhoc_tool(
	name="role_asn",
	runnable="//llamazure/azrest/openapi.py",
	args=["https://raw.githubusercontent.com/Azure/azure-rest-api-specs/main/", "specification/authorization/resource-manager/Microsoft.Authorization/stable/2022-04-01/authorization-RoleAssignmentsCalls.json", "llamazure/rbac/role_asn.py"],
	output_files=["llamazure/rbac/role_asn.py"],
	root_output_directory='.',
)

adhoc_tool(
	name="role_def",
	runnable="//llamazure/azrest/openapi.py",
	args=["https://raw.githubusercontent.com/Azure/azure-rest-api-specs/main/", "specification/authorization/resource-manager/Microsoft.Authorization/stable/2022-04-01/authorization-RoleDefinitionsCalls.json", "llamazure/rbac/role_def.py"],
	output_files=["llamazure/rbac/role_def.py"],
	root_output_directory='.',
)

experimental_wrap_as_python_sources(
    name="azgen",
    inputs=[
        ":role_asn",
        ":role_def",
    ],
)

python_distribution(
	name="llamazure.rbac",
	dependencies=[":rbac"],
	long_description_path="llamazure/rbac/readme.md",
	provides=python_artifact(
		name="llamazure.rbac",
		version="0.0.2",
		description="Azure roles, users, and assignments",
		author="Daniel Goldman",
		classifiers=[
			"Development Status :: 3 - Alpha",
			"Programming Language :: Python :: 3.8",
			"Programming Language :: Python :: 3.9",
			"Programming Language :: Python :: 3.10",
			"Programming Language :: Python :: 3.11",
			"Topic :: Utilities",
			"Topic :: Internet :: Log Analysis",
		],
		license="Round Robin 2.0.0",
		long_description_content_type="text/markdown",
	),
)
