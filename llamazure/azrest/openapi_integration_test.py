from textwrap import dedent

from llamazure.azrest.openapi import IRTransformer, OADef, OARef


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
