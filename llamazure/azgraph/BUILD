python_sources(
	name="azgraph",
)

python_tests(
	name="tests",
)

python_distribution(
	name="llamazure.azgraph",
	dependencies=[":azgraph"],
	long_description_path="llamazure/azgraph/readme.md",
	provides=python_artifact(
		name="llamazure.azgraph",
		version="0.0.1",
		description="Azure Resources Graph client",
		author="Daniel Goldman",
		classifiers=[
			"Development Status :: 3 - Alpha",
			"Programming Language :: Python :: 3.8",
			"Programming Language :: Python :: 3.9",
			"Programming Language :: Python :: 3.10",
			"Topic :: Utilities",
			"Topic :: Internet :: Log Analysis",
		],
		license="Round Robin 2.0.0",
		long_description_content_type="text/markdown",
	),
)