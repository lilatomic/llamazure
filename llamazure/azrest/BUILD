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
		version="0.3.0",
		description="Azure REST client",
		author="Daniel Goldman",
		classifiers=[
			"Development Status :: 3 - Alpha",
			"Programming Language :: Python :: 3.9",
			"Programming Language :: Python :: 3.10",
			"Programming Language :: Python :: 3.11",
			"Programming Language :: Python :: 3.12",
			"Programming Language :: Python :: 3.13",
			"Topic :: Utilities",
			"Topic :: Internet :: Log Analysis",
		],
		license="Round Robin 2.0.0",
		long_description_content_type="text/markdown",
		extras_require={"cli": ["click>8"]},
		entry_points={"console_scripts": ["llamazure-azrest-openapi=llamazure.azrest.openapi:main"]},
	),
)

python_test_utils(
	name="test_utils",
)
