import ast
from pathlib import Path
from textwrap import dedent

from llamazure.azrest import openapi
from llamazure.azrest.openapi import IRTransformer, OADef, OARef, Reader


class TestLoading:
	def test_load_url(self):
		root = "https://raw.githubusercontent.com/Azure/azure-rest-api-specs/main/"
		path = Path("specification/authorization/resource-manager/Microsoft.Authorization/stable/2022-04-01/authorization-RoleAssignmentsCalls.json")

		reader = Reader(root=root, path=path, openapi={})

		r = reader.load_relative("../../../../../common-types/resource-management/v2/types.json#/parameters/SubscriptionIdParameter")
		assert r is not None
		assert r["name"] == "subscriptionId"


class TestTransformDefs:

	prop = OADef.Property(type="int", description="A property")

	prop_nested_properties = OARef(**{"$ref": "#/definitions/MyClassProperties", "description": "Properties for My Class"})

	def test_simple_def(self):
		"""Test a plain Definition"""
		oa_defs = {"MyClass": OADef(type="object", description="BlahBlah MyClass", properties={"my_property": self.prop})}

		tx = IRTransformer(oa_defs, None)

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
		tx = IRTransformer(oa_defs, None)

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


class TestTransformPaths:
	def test_all_contained(self):
		"""Test an OpenAPI Path with no refs to objects in other files"""
		paths = {
			"/path0/{arg0}": {
				"put": {
					"tags": [],
					"operationId": "Ops0_Op0",
					"description": "Description of op0.",
					"parameters": [
						{"name": "arg0", "in": "path", "required": True, "type": "string", "description": "Unused"},
						{"name": "arg1", "in": "body", "required": True, "description": "Unused", "schema": {"$ref": "#/definitions/Def0"}},
					],
					"responses": {"200": {"description": "Unused", "schema": {"$ref": "#/definitions/Ret0"}}},
				}
			}
		}
		oa_defs = {}

		tx = IRTransformer(oa_defs, None)

		r = tx.transform_paths(paths, "apiv0")

		assert (
			r.strip()
			== dedent(
				'''\
			class AzOps0:
				apiv = "apiv0"
				@staticmethod
				def Op0(arg0: str, arg1: Def0) -> Req[Ret0]:
					"""Description of op0."""
					return Req.put(
						name="Ops0.Op0",
						path=f"/path0/{arg0}",
						apiv="apiv0",
						body=arg1,
						ret_t=Ret0
					)
		'''
			).strip()
		)


class TestScript:
	def test_run(self, tmp_file):
		"""Test running the script"""
		openapi.main(
			"https://raw.githubusercontent.com/Azure/azure-rest-api-specs/main/",
			"specification/authorization/resource-manager/Microsoft.Authorization/stable/2022-04-01/authorization-RoleAssignmentsCalls.json",
			tmp_file,
		)

		with open(tmp_file, mode="r", encoding="utf-8") as output_file:
			output = output_file.read()
			assert len(output) > 0

		parsed = ast.parse(output)
		assert isinstance(parsed, ast.Module)
		assert len(parsed.body) > 0
