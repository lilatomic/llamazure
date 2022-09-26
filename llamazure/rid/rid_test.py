from uuid import UUID

from hypothesis import given
from hypothesis.strategies import text, uuids

from llamazure.rid.rid import parse, Subscription, ResourceGroup


class TestRIDTypes:

	@given(uuids())
	def test_subscription(self, u: UUID):
		assert parse(f"subscription/{u}") == Subscription(str(u))

	@given(uuids(), text())
	def test_resource_group(self, u: UUID, rg: str):
		assert parse(f"subscription/{u}/resourceGroups/{rg}") == ResourceGroup(rg.lower(), Subscription(str(u)))
