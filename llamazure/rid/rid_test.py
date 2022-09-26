import string
from uuid import UUID

from hypothesis import given
from hypothesis.strategies import builds, text, uuids

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
