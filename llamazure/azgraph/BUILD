python_sources(
	name="azgraph",
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

python_distribution(
	name="llamazure.azgraph",
	repositories=["@llamazure.azgraph"],
	dependencies=[":azgraph", ":py.typed"],
	long_description_path="llamazure/azgraph/readme.md",
	provides=python_artifact(
		name="llamazure.azgraph",
		version="0.1.0",
		description="Azure Resources Graph client",
		author="Daniel Goldman",
		classifiers=[
			"Development Status :: 3 - Alpha",
			"Programming Language :: Python :: 3.10",
			"Programming Language :: Python :: 3.11",
			"Programming Language :: Python :: 3.12",
			"Programming Language :: Python :: 3.13",
			"Programming Language :: Python :: 3.14",
			"Topic :: Utilities",
		],
		license="Round Robin 2.0.0",
		long_description_content_type="text/markdown",
	),
)

resource(name="py.typed", source="py.typed")
