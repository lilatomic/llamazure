python_sources(
	name="tresource",
)

python_tests(
	name="tests",
)

python_distribution(
	name="llamazure.tresource",
	dependencies=[":tresource", ":py.typed"],
	long_description_path="llamazure/tresource/readme.md",
	provides=python_artifact(
		name="llamazure.tresource",
		version="0.1.0",
		description="Group Azure resources into their hierarchy",
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
