import ast
import os
from pathlib import Path
from textwrap import dedent

import pytest

from llamazure.azrest import openapi
from llamazure.azrest.openapi import IRTransformer, OADef, OARef, Reader, RefCache


class TestLoading:
	def test_load_url(self):
		root = "https://raw.githubusercontent.com/Azure/azure-rest-api-specs/main/"
		path = Path("specification/authorization/resource-manager/Microsoft.Authorization/stable/2022-04-01/authorization-RoleAssignmentsCalls.json")

		reader = Reader(root=root, path=path, openapi={}, reader_cache={})

		_, r = reader.load_relative("../../../../../common-types/resource-management/v2/types.json#/parameters/SubscriptionIdParameter")
		assert r is not None
		assert r["name"] == "subscriptionId"


class TestTransformDefs:
	prop = OADef.Property(type="integer", description="A property")

	prop_nested_properties = OARef(**{"$ref": "#/definitions/MyClassProperties", "description": "Properties for My Class"})

	def test_simple_def(self):
		"""Test a plain Definition"""
		oa_defs = {"MyClass": OADef(type="object", description="BlahBlah MyClass", properties={"my_property": self.prop})}

		tx = IRTransformer(oa_defs, {}, Reader("", Path(), {}, {}), RefCache())

		r = tx.transform_definitions()

		assert (
			r.strip()
			== dedent(
				'''\
			class MyClass(BaseModel):
				"""BlahBlah MyClass"""

				my_property: Optional[int] = None

				def __eq__(self, o) -> bool:
					return (
						isinstance(o, self.__class__)
						and self.my_property == o.my_property
					)



			MyClass.model_rebuild()
			'''
			).strip()
		)

	def test_def_with_nested_properties_class(self):
		oa_defs = {
			"MyClass": OADef(type="object", properties={"properties": self.prop_nested_properties}),
			"MyClassProperties": OADef(type="object", properties={"my_property": self.prop}),
		}
		tx = IRTransformer(oa_defs, {}, Reader("", Path(), {"definitions": oa_defs, "paths": {}}, {}), RefCache())

		r = tx.transform_definitions()

		assert (
			r.strip()
			== dedent(
				'''\
			class MyClass(BaseModel):
				"""None"""
				class Properties(BaseModel):
					"""None"""

					my_property: Optional[int] = None

					def __eq__(self, o) -> bool:
						return (
							isinstance(o, self.__class__)
							and self.my_property == o.my_property
						)


				properties: Properties

				def __eq__(self, o) -> bool:
					return (
						isinstance(o, self.__class__)
						and self.properties == o.properties
					)



			MyClass.model_rebuild()
			'''
			).strip()
		)


def traverse_and_apply(root_dir, func):
	"""
	Traverse all directories starting from root_dir and apply a function to the content of each file found.

	Parameters:
	root_dir (str): The root directory from where the traversal starts.
	func (function): A lambda function to apply to the content of each file.
	"""
	for dirpath, dirnames, filenames in os.walk(root_dir):
		for filename in filenames:
			file_path = os.path.join(dirpath, filename)
			with open(file_path, "r") as file:
				content = file.read()
				func(content)


class TestScript:
	def assert_parses(self, output):
		assert len(output) > 0
		parsed = ast.parse(output)
		assert isinstance(parsed, ast.Module)
		assert len(parsed.body) > 0

	root_package = "my.package"

	@pytest.mark.parametrize(
		"spec_path",
		[
			"specification/applicationinsights/resource-manager/Microsoft.Insights/stable/2023-06-01/workbooks_API.json",
			"specification/authorization/resource-manager/Microsoft.Authorization/stable/2022-04-01/authorization-RoleAssignmentsCalls.json",
			"specification/portal/resource-manager/Microsoft.Portal/preview/2020-09-01-preview/portal.json",
			",".join(
				[
					"specification/authorization/resource-manager/Microsoft.Authorization/stable/2022-04-01/authorization-RoleAssignmentsCalls.json",
					"specification/authorization/resource-manager/Microsoft.Authorization/stable/2022-04-01/authorization-RoleDefinitionsCalls.json",
				]
			),
		],
	)
	def test_run_includes_nested_defs(self, spec_path, tmp_path):
		"""Test running the script with a spec that contains nested defs"""
		tmp_file = tmp_path / "tmp_file"

		openapi.main(
			"https://raw.githubusercontent.com/Azure/azure-rest-api-specs/main/",
			spec_path,
			tmp_file,
			self.root_package,
		)

		traverse_and_apply(tmp_file, self.assert_parses)
