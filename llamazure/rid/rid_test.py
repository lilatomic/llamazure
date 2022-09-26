import string
from uuid import UUID

from hypothesis import given
from hypothesis.strategies import text, uuids, builds

from llamazure.rid.rid import parse, Subscription, ResourceGroup


az_alnum = text(alphabet=list(string.ascii_letters + string.digits))

st_subscription = builds(lambda u: Subscription(str(u)), uuids())


class TestRIDTypes:

	@given(uuids())
	def test_subscription(self, u: UUID):
		assert parse(f"subscription/{u}") == Subscription(str(u))

	@given(st_subscription, az_alnum)
	def test_resource_group(self, sub: Subscription, rg: str):
		assert parse(f"subscription/{sub.uuid}/resourceGroups/{rg}") == ResourceGroup(rg.lower(), sub)
