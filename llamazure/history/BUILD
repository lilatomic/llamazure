python_sources(
	name="history",
)

python_tests(
	name="tests",
)

python_distribution(
	name="llamazure.history",
	dependencies=[":history"],
	long_description_path="llamazure/history/readme.md",
	provides=python_artifact(
		name="llamazure.history",
		version="0.0.1",
		description="Build a history of an Azure tenancy",
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

python_test_utils(
	name="test_utils",
)
