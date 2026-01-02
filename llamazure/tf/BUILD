python_sources(
	name="tf",
)

python_tests(
	name="tests",
)

python_test_utils(
	name="test_utils",
)

python_distribution(
	name="llamazure.tf",
	repositories=["@llamazure.tf"],
	dependencies=[":tf", ":py.typed"],
	long_description_path="llamazure/tf/readme.md",
	provides=python_artifact(
		name="llamazure.tf",
		version="0.2.0",
		description="Generate some azurerm resources without the headache",
		author="Daniel Goldman",
		maintainer="Daniel Goldman",
		classifiers=[
			"Development Status :: 3 - Alpha",
			"Programming Language :: Python :: 3.10",
			"Programming Language :: Python :: 3.11",
			"Programming Language :: Python :: 3.12",
			"Programming Language :: Python :: 3.13",
			"Programming Language :: Python :: 3.14",
			"Topic :: Utilities",
			"Topic :: Internet :: Log Analysis",
		],
		project_urls={
			"Homepage": "https://github.com/lilatomic/llamazure",
			"Repository": "https://github.com/lilatomic/llamazure",
			"Changelog": "https://github.com/lilatomic/llamazure/blob/main/llamazure/tf/changelog.md",
			"Issues": "https://github.com/lilatomic/llamazure/issues",
		},
		license="Round Robin 2.0.0",
		long_description_content_type="text/markdown",
	),
)

resource(name="py.typed", source="py.typed")
