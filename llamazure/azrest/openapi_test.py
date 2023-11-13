from llamazure.azrest.openapi import IR_T, IR_List, IRDef, IRTransformer, OADef


class TestTransformPrimitives:
	def test_string(self):
		p = OADef.Property(type="string", description="description0")
		assert IRTransformer({}).transform_property(p) == IR_T(t=str)


class TestTransformArray:
	def test_string_array(self):
		p = OADef.Array(
			items=OADef.Property(type="string", description="d0"),
			description="d1",
		)
		assert IRTransformer({}).ir_array(p) == IR_T(t=IR_List(items=IR_T(t=str)))


class TestTransformDef:
	def test_bag_of_props(self):
		p = OADef(
			type="t0",
			description="d0",
			properties={
				"p0": OADef.Property(type="t.p0"),
				"p1": OADef.Property(type="t.p1"),
			},
		)
		result = IRTransformer({}).transform_def("n0", p)
		expected = IRDef(
			name="n0",
			description="d0",
			properties={
				"p0": IR_T(t="t.p0"),
				"p1": IR_T(t="t.p1"),
			},
		)
		assert result == expected
