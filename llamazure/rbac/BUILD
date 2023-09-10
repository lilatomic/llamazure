python_sources(
	name="rbac",
)

python_tests(
	name="tests",
)

python_tests(
	name="integration-tests",
	sources=["integration_test.py"],
	tags=["integration"],
)

python_test_utils(
    name="test_utils",
)

python_distribution(
	name="llamazure.rbac",
	dependencies=[":rbac"],
	long_description_path="llamazure/rbac/readme.md",
	provides=python_artifact(
		name="llamazure.rbac",
		version="0.0.1",
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
