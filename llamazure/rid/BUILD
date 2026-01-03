python_sources(
	name="rid",
)

python_tests(
	name="tests",
)

python_distribution(
	name="llamazure.rid",
	dependencies=[":rid", ":py.typed"],
	long_description_path="llamazure/rid/readme.md",
	provides=python_artifact(
		name="llamazure.rid",
		version="0.1.1",
		description="Azure Resource IDs you can use",
		author="Daniel Goldman",
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
		license="Round Robin 2.0.0",
		long_description_content_type="text/markdown",
	),
)

python_test_utils(
	name="test_utils",
)

resource(name="py.typed", source="py.typed")
