python_distribution(
	name="llamazure.tools",
	dependencies=[
		"//llamazure/tools/migrate:migrate",
	],
	long_description_path="llamazure/tools/readme.md",
	provides=python_artifact(
		name="llamazure.tools",
		version="0.2.2",
		description="A bundle of helpful tools for dealing with Azure",
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
		entry_points={"console_scripts": ["llamazure-migrate=llamazure.tools.migrate.__main__:migrate"]},
	),
)
