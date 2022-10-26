"""Tests for tools for working with Azure resource IDs"""
import string
from pathlib import Path
from typing import Optional, Union
from uuid import UUID

import pytest
from hypothesis import given
from hypothesis.strategies import builds, composite, recursive, text, uuids

from llamazure.rid.rid import AzObj, Resource, ResourceGroup, SubResource, Subscription, get_chain, parse, parse_chain, serialise, serialise_p

az_alnum = text(alphabet=list(string.ascii_letters + string.digits), min_size=1)

az_alnum_lower = text(alphabet=list(string.ascii_lowercase + string.digits), min_size=1)

st_subscription = builds(lambda u: Subscription(str(u)), uuids())

st_rg = builds(lambda sub, name: ResourceGroup(name, sub), st_subscription, az_alnum_lower)

st_resource_base = builds(
	lambda provider, res_type, name, rg: Resource(provider, res_type, name, rg, parent=None, sub=rg.sub),
	az_alnum_lower,
	az_alnum_lower,
	az_alnum_lower,
	st_rg,
)

st_subresource = builds(
	lambda res_type, name, rg: SubResource(res_type, name, rg, parent=None, sub=rg.sub),
	az_alnum_lower,
	az_alnum_lower,
	st_rg,
)


@composite
def complex_resource(draw, res_gen) -> Union[Resource, SubResource]:
	"""Create a resource which may have parents"""
	child = draw(res_gen)
	parent = draw(res_gen)
	if isinstance(child, Resource):
		return Resource(
			child.provider,
			child.res_type,
			child.name,
			rg=parent.rg,
			parent=parent,
			sub=parent.rg.sub,
		)
	if isinstance(child, SubResource):
		return SubResource(
			child.res_type,
			child.name,
			rg=parent.rg,
			parent=parent,
			sub=parent.rg.sub,
		)
	else:
		raise RuntimeError("AAAA")


st_resource_complex = recursive(st_resource_base | st_subresource, complex_resource)
st_resource_any = st_subscription | st_rg | st_resource_base | st_subresource | st_resource_complex


class TestRIDParse:
	"""Tests directly for resource ID types"""

	@given(uuids())
	def test_subscription(self, u: UUID):
		assert parse(f"/subscriptions/{u}") == Subscription(str(u))

	@given(st_subscription, az_alnum)
	def test_resource_group(self, sub: Subscription, rg: str):
		assert parse(f"/subscriptions/{sub.uuid}/resourceGroups/{rg}") == ResourceGroup(rg.lower(), sub)

	@given(st_rg)
	def test_resource_group_constructed(self, rg: ResourceGroup):
		assert parse(f"/subscriptions/{rg.sub.uuid}/resourceGroups/{rg.name}") == rg

	@given(st_resource_base)
	def test_simple_resource(self, res: Resource):
		assert res.rg is not None
		assert parse(f"/subscriptions/{res.rg.sub.uuid}/resourceGroups/{res.rg.name}/providers/{res.provider}/{res.res_type}/{res.name}") == res

	@given(st_resource_complex)
	def test_complex_resource(self, res: Resource):
		rid = ""
		res_remaining: Optional[Union[Resource, SubResource]] = res
		while res_remaining:
			if isinstance(res_remaining, Resource):
				rid = f"/providers/{res_remaining.provider}/{res_remaining.res_type}/{res_remaining.name}" + rid
				res_remaining = res_remaining.parent
			if isinstance(res_remaining, SubResource):
				rid = f"/{res_remaining.res_type}/{res_remaining.name}" + rid
				res_remaining = res_remaining.parent
		rg = res.rg
		assert rg is not None
		rid = f"/subscriptions/{rg.sub.uuid}/resourceGroups/{rg.name}" + rid

		assert parse(rid) == res


class TestRIDSerialise:
	"""Test directly for serialising resource IDs"""

	@given(st_subscription)
	def test_subscription(self, subscription: Subscription):
		assert serialise_p(subscription) == Path("/subscriptions/") / subscription.uuid

	@given(st_rg)
	def test_resource_group(self, rg: ResourceGroup):
		assert serialise_p(rg) == Path("/subscriptions") / rg.sub.uuid / "resourcegroups" / rg.name

	@given(st_resource_base)
	def test_simple_resource(self, res: Resource):
		assert res.rg is not None
		assert serialise_p(res) == Path("/subscriptions") / res.rg.sub.uuid / "resourcegroups" / res.rg.name / "providers" / res.provider / res.res_type / res.name


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
		assert parse(serialise(res)) == res


class TestRIDPathological:
	"""Tests using real-world pathological cases"""

	@pytest.mark.parametrize(
		"rid",
		[
			"/subscriptions/<>/resourcegroups/<>/providers/microsoft.operationalinsights/workspaces/<>/linkedservices/security",
			"/subscriptions/<>/resourcegroups/<>/providers/microsoft.storage/storageaccounts/<>/providers/microsoft.security/advancedthreatprotectionsettings/current",
		],
	)
	def test_pathological(self, rid):
		assert serialise(parse(rid)) == rid


class TestMSRestAzure:
	"""Test cases copied from the msrestazure-for-python repository"""

	@pytest.mark.parametrize(
		"rid",
		[
			"/subscriptions/fakesub/resourcegroups/testgroup/providers/Microsoft.Storage/storageAccounts/foo/providers/Microsoft.Authorization/locks/bar",
			"/subscriptions/fakesub/resourcegroups/testgroup/providers/Microsoft.Storage/storageAccounts/foo/locks/bar",
			"/subscriptions/fakesub/resourcegroups/testgroup/providers/Microsoft.Storage/storageAccounts/foo/providers/Microsoft.Authorization/locks/bar/providers/Microsoft.Network/nets/gc",
			"/subscriptions/fakesub/resourcegroups/testgroup/providers/Microsoft.Storage/storageAccounts/foo/locks/bar/nets/gc",
			"/subscriptions/mySub/resourceGroups/myRg/providers/Microsoft.Provider1/resourceType1/name1",
			"/subscriptions/mySub/resourceGroups/myRg/providers/Microsoft.Provider1/resourceType1/name1/resourceType2/name2",
			"/subscriptions/00000/resourceGroups/myRg/providers/Microsoft.RecoveryServices/vaults/vault_name/backupFabrics/fabric_name/protectionContainers/container_name/protectedItems/item_name/recoveryPoint/recovery_point_guid",
			"/subscriptions/mySub/resourceGroups/myRg/providers/Microsoft.Provider1/resourceType1/name1/resourceType2/name2/providers/Microsoft.Provider3/resourceType3/name3",
			"/subscriptions/fakesub/providers/Microsoft.Authorization/locks/foo",
			"/Subscriptions/fakesub/providers/Microsoft.Authorization/locks/foo",
			"/subscriptions/mySub/resourceGroups/myRg",
		],
	)
	def test_accept(self, rid):
		assert serialise(parse(rid)) == rid.lower()


class TestParseChain:
	"""Tests that parsing as a chain returns the same as the chain of a parsed resource"""

	@given(st_resource_any)
	def test_chain_reserialises(self, res: AzObj):
		"""Test that the chain reserialises correctly"""
		parsed_chain = parse_chain(serialise(res))

		# check that every element in the chain is the parent of the next resource
		for i, elem in list(enumerate(parsed_chain))[:-1]:  # skip the last element since we're doing pairwise comparisons
			assert serialise(parsed_chain[i + 1]).startswith(serialise(elem))

		# check that the last resource is the same as the test input
		assert parsed_chain[-1] == res

	@given(st_resource_any)
	def test_parse_chain_is_same_as_chain_of_parsed(self, res: AzObj):
		"""Test that the parse_chain method gives the same output as the chain of a normally parsed resource"""
		parsed_chain = parse_chain(serialise(res))

		chain_of_parsed = get_chain(res)

		assert parsed_chain == chain_of_parsed
