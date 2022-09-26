import string
from uuid import UUID

from hypothesis import given
from hypothesis.strategies import builds, composite, recursive, text, uuids

from llamazure.rid.rid import Resource, ResourceGroup, Subscription, parse

az_alnum = text(alphabet=list(string.ascii_letters + string.digits), min_size=1)

az_alnum_lower = text(alphabet=list(string.ascii_lowercase + string.digits), min_size=1)

st_subscription = builds(lambda u: Subscription(str(u)), uuids())

st_rg = builds(
	lambda sub, name: ResourceGroup(name, sub), st_subscription, az_alnum_lower
)

st_resource_base = builds(
	lambda provider, res_type, name, rg: Resource(
		provider, res_type, name, rg, parent=None
	),
	az_alnum_lower,
	az_alnum_lower,
	az_alnum_lower,
	st_rg,
)


@composite
def complex_resource(draw, res_gen) -> Resource:
	child = draw(res_gen)
	parent = draw(res_gen)
	imprinted_child = Resource(
		child.provider, child.res_type, child.name, rg=parent.rg, parent=parent
	)
	return imprinted_child


st_complex_resource = recursive(st_resource_base, complex_resource)


class TestRIDTypes:
	@given(uuids())
	def test_subscription(self, u: UUID):
		assert parse(f"/subscriptions/{u}") == Subscription(str(u))

	@given(st_subscription, az_alnum)
	def test_resource_group(self, sub: Subscription, rg: str):
		assert parse(f"/subscriptions/{sub.uuid}/resourceGroups/{rg}") == ResourceGroup(
			rg.lower(), sub
		)

	@given(st_rg)
	def test_resource_group_constructed(self, rg: ResourceGroup):
		assert (
			parse(f"/subscriptions/{rg.subscription.uuid}/resourceGroups/{rg.name}")
			== rg
		)

	@given(st_resource_base)
	def test_simple_resource(self, res: Resource):
		assert (
			parse(
				f"/subscriptions/{res.rg.subscription.uuid}/resourceGroups/{res.rg.name}/providers/{res.provider}/{res.res_type}/{res.name}"
			)
			== res
		)

	@given(st_complex_resource)
	def test_complex_resource(self, res: Resource):
		rid = ""
		res_remaining = res
		while res_remaining:
			rid = (
				f"/providers/{res_remaining.provider}/{res_remaining.res_type}/{res_remaining.name}"
			) + rid
			res_remaining = res_remaining.parent
		rg = res.rg
		rid = f"/subscriptions/{rg.subscription.uuid}/resourceGroups/{rg.name}" + rid

		assert parse(rid) == res
