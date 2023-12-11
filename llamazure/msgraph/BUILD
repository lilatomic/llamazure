python_sources(
	name="msgraph",
)

python_tests(
	name="tests",
)

python_distribution(
	name="llamazure.rid",
	dependencies=[":msgraph"],
	long_description_path="llamazure/msgraph/readme.md",
	provides=python_artifact(
		name="llamazure.msgraph",
		version="0.0.3",
		description="Microsoft Graph client",
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