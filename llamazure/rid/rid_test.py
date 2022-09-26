import string
from uuid import UUID

from hypothesis import given
from hypothesis.strategies import text, uuids, builds

from llamazure.rid.rid import parse, Subscription, ResourceGroup


az_alnum = text(alphabet=list(string.ascii_letters + string.digits))

az_alnum_lower = text(alphabet=list(string.ascii_lowercase + string.digits))

st_subscription = builds(lambda u: Subscription(str(u)), uuids())

st_rg = builds(lambda sub, name: ResourceGroup(name, sub), st_subscription, az_alnum_lower)

class TestRIDTypes:

	@given(uuids())
	def test_subscription(self, u: UUID):
		assert parse(f"subscription/{u}") == Subscription(str(u))

	@given(st_subscription, az_alnum)
	def test_resource_group(self, sub: Subscription, rg: str):
		assert parse(f"subscription/{sub.uuid}/resourceGroups/{rg}") == ResourceGroup(rg.lower(), sub)

	@given(st_rg)
	def test_resource_group_constructed(self, rg: ResourceGroup):
		assert parse(f"subscription/{rg.subscription.uuid}/resourceGroups/{rg.name}") == rg