python_sources(
	name="azrest",
)

python_tests(
	name="tests",
)

python_distribution(
	name="llamazure.rid",
	dependencies=[":azrest"],
	long_description_path="llamazure/azrest/readme.md",
	provides=python_artifact(
		name="llamazure.azrest",
		version="0.1.0",
		description="Azure REST client",
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
