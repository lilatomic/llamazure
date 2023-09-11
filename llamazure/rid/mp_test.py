"""Tests for MP resource IDs"""

import dataclasses
from typing import Union

import pytest
from hypothesis import assume, given

from llamazure.rid import rid
from llamazure.rid.conftest import st_resource_base, st_resource_complex, st_rg, st_subscription
from llamazure.rid.mp import Path, Resource, ResourceGroup, SubResource, Subscription, parse


class TestMPParse:
	"""Tests directly for MP parsing"""

	def test_invalid(self):
		with pytest.raises(ValueError):
			parse("/hihello")

	@given(st_subscription)
	def test_subscriptions(self, sub: rid.Subscription):
		res_id = Path(rid.serialise(sub))
		mp = parse(res_id)
		assert mp[0] == res_id == mp[1].path
		assert mp[1] == Subscription(res_id, sub.uuid)

	@given(st_rg)
	def test_rg(self, rg: rid.ResourceGroup):
		res_id = Path(rid.serialise(rg))
		mp = parse(res_id)
		assert mp[0] == res_id == mp[1].path
		assert mp[1] == ResourceGroup(res_id, rg.name, Path(rid.serialise(rg.sub)))

	@given(st_resource_base)
	def test_simple_resource(self, res: rid.Resource):
		assume(res.sub is not None)
		assume(res.rg is not None)
		assert res.sub is not None
		assert res.rg is not None

		res_id = Path(rid.serialise(res))
		mp = parse(res_id)
		assert mp[0] == res_id == mp[1].path
		assert mp[1] == Resource(
			res_id,
			provider=res.provider,
			res_type=res.res_type,
			name=res.name,
			rg=Path(rid.serialise(res.rg)),
			sub=Path(rid.serialise(res.sub)),
		)

	@given(st_resource_base)
	def test_resource_no_rg(self, res: rid.Resource):
		assume(res.sub is not None)
		res = dataclasses.replace(res, rg=None)
		assert res.sub is not None
		assert res.rg is None

		res_id = Path(rid.serialise(res))
		mp = parse(res_id)
		assert mp[0] == res_id == mp[1].path
		assert mp[1] == Resource(
			res_id,
			provider=res.provider,
			res_type=res.res_type,
			name=res.name,
			rg=None,
			sub=Path(rid.serialise(res.sub)),
		)

	@given(st_resource_complex)
	def test_complex_resource(self, res: Union[rid.Resource, rid.SubResource]):
		assume(res.sub is not None)
		assume(res.rg is not None)
		assert res.sub is not None
		assert res.rg is not None

		res_id = Path(rid.serialise(res))
		mp = parse(res_id)
		assert mp[0] == res_id == mp[1].path
		parent_path = Path(rid.serialise(res.parent)) if res.parent else None
		if isinstance(res, rid.Resource):
			assert mp[1] == Resource(res_id, res.provider, res.res_type, res.name, Path(rid.serialise(res.rg)), Path(rid.serialise(res.sub)), parent=parent_path)
		if isinstance(res, rid.SubResource):
			assert mp[1] == SubResource(res_id, res.res_type, res.name, Path(rid.serialise(res.rg)), Path(rid.serialise(res.sub)), parent=parent_path)
