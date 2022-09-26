"""Tests for tools for working with Azure resource IDs"""
import string
from pathlib import Path
from uuid import UUID

from hypothesis import given
from hypothesis.strategies import builds, composite, recursive, text, uuids

from llamazure.rid.rid import Resource, ResourceGroup, Subscription, parse, serialise_p

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
	"""Create a resource which may have parents"""
	child = draw(res_gen)
	parent = draw(res_gen)
	imprinted_child = Resource(
		child.provider, child.res_type, child.name, rg=parent.rg, parent=parent
	)
	return imprinted_child


st_resource_complex = recursive(st_resource_base, complex_resource)


class TestRIDParse:
	"""Tests directly for resource ID types"""

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

	@given(st_resource_complex)
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


class TestRIDSerialise:
	"""Test directly for serialising resource IDs"""

	@given(st_subscription)
	def test_subscription(self, subscription: Subscription):
		assert serialise_p(subscription) == Path("/subscriptions/") / subscription.uuid

	@given(st_rg)
	def test_resource_group(self, rg: ResourceGroup):
		assert (
			serialise_p(rg)
			== Path("/subscriptions")
			/ rg.subscription.uuid
			/ "resourcegroups"
			/ rg.name
		)

	@given(st_resource_base)
	def test_simple_resource(self, res: Resource):
		assert (
			serialise_p(res)
			== Path("/subscriptions")
			/ res.rg.subscription.uuid
			/ "resourcegroups"
			/ res.rg.name
			/ "providers"
			/ res.provider
			/ res.res_type
			/ res.name
		)


class TestRIDCyclic:
	"""Test that parsing and reserialising is invariant"""

	@given(st_subscription)
	def test_subscription(self, subscription: Subscription):
		assert parse(str(serialise_p(subscription))) == subscription

	@given(st_rg)
	def test_resource_group(self, rg: ResourceGroup):
		assert parse(str(serialise_p(rg))) == rg

	@given(st_resource_base)
	def test_simple_resource(self, res: Resource):
		assert parse(str(serialise_p(res))) == res

	@given(st_resource_complex)
	def test_complex_resource(self, res: Resource):
		assert parse(str(serialise_p(res))) == res
