python_sources(
	name="msgraph",
)

python_tests(
	name="tests",
)

python_distribution(
	name="llamazure.rid",
	dependencies=[":msgraph", ":py.typed"],
	long_description_path="llamazure/msgraph/readme.md",
	provides=python_artifact(
		name="llamazure.msgraph",
		version="0.1.0",
		description="Microsoft Graph client",
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
	),
)

resource(name="py.typed", source="py.typed")
