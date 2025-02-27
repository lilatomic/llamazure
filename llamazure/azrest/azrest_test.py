"""Integration tests for AzRest"""

import random
from typing import Dict

# pylint: disable=redefined-outer-name
import pytest
from pydantic import BaseModel, ValidationError

from llamazure.azrest.azrest import AzRest
from llamazure.azrest.models import AzList, AzureError, BatchReq, Req, cast_as, ensure


@pytest.fixture
def azr(credential) -> AzRest:
	return AzRest.from_credential(credential)


def sub_req(sub: str) -> Req:
	return Req.get("test-batch-single", f"{sub}/resourcegroups", "2022-09-01", AzList)


class TestList:
	"""Test AzRest's handling of Lists of things"""

	def test_nothing(self):
		"""Prevent collection problems for partitions"""

	@pytest.mark.integration
	def test_paginated(self, azr, it_info):
		"""Test following the pagination"""
		scope = it_info["scopes"]["sub0"]
		ret_t = AzList[Dict]
		req = Req.get(name="Resources.List", path=f"/{scope}/resources", apiv="2021-04-01", ret_t=ret_t).add_params({"$top": "1"})
		res = azr.call(req)

		assert len(res) > 5


class TestBatches:
	"""Test AzRest's implementation of the secret Batch api"""

	def test_nothing(self):
		"""Prevent collection problems for partitions"""

	@pytest.mark.integration
	def test_empty_batch__raises(self, azr):
		"""An empty batch raises and error with Azure"""
		batch_req = BatchReq.gather([])
		with pytest.raises(AzureError) as e:
			azr.call_batch(batch_req)
		assert e.value.error.code == "EmptyBatchRequest"

	@pytest.mark.integration
	def test_single_item(self, azr, it_info):
		"""A single item in a batch"""
		batch_req = BatchReq.gather([sub_req(it_info["scopes"]["sub0"])])
		batch_res = azr.call_batch(batch_req)
		assert len(batch_res) == 1
		for res in batch_res.values():
			assert isinstance(res, AzList)

	@pytest.mark.integration
	def test_multiple_items(self, azr, it_info):
		"""Multiple items in a batch."""
		batch_req = BatchReq.gather(
			[
				sub_req(it_info["scopes"]["sub0"]),
				sub_req(it_info["scopes"]["sub1"]),
			]
		)
		batch_res = azr.call_batch(batch_req)
		assert len(batch_res) == 2
		for res in batch_res.values():
			assert isinstance(res, AzList)

		assert len(list(batch_res.values())[0].value) > 0, "responses were not returned in order"

	@pytest.mark.integration
	def test_custom_names(self, azr, it_info):
		"""Test that custom-named reqs are reassembled correctly"""
		# reqs are out-of-order so we know it's not an ordering thing
		batch_req = BatchReq(
			{
				"test-req-1": sub_req(it_info["scopes"]["sub1"]),
				"test-req-0": sub_req(it_info["scopes"]["sub0"]),
			}
		)
		batch_res = azr.call_batch(batch_req)
		assert len(batch_res) == 2
		for res in batch_res.values():
			assert isinstance(res, AzList)

		assert len(batch_res["test-req-0"].value) > 0


class TestLongPoll:
	def test_nothing(self):
		"""Prevent collection problems for partitions"""

	@pytest.mark.integration
	def test_longpoll(self, azr, it_info):
		"""Test that we follow longpolls"""
		scope = it_info["resources"]["longpoll0"]

		tgt = f"10.0.{random.randint(0, 255)}.0/24"
		existing = azr.call(Req.get(name="test longpoll", path=scope, apiv="2022-01-01", ret_t=dict))
		existing["properties"]["addressSpace"]["addressPrefixes"] = [tgt]
		res = azr.call_long_operation(Req.put(name="test longpoll", path=scope, apiv="2022-01-01", body=existing, ret_t=dict))
		assert res == {"status": "Succeeded"}  # TODO: deserialise from spec
		updated = azr.call(Req.get(name="test longpoll", path=scope, apiv="2022-01-01", ret_t=dict))
		assert updated["properties"]["addressSpace"]["addressPrefixes"] == [tgt]


# Example Pydantic models
class Foo(BaseModel):
	id: int
	name: str


class FooUpdateParameters(BaseModel):
	name: str


class TestCastAs:
	def test_cast_foo_to_fooupdateparameters(self):
		foo = Foo(id=1, name="test")
		foo_update = cast_as(foo, FooUpdateParameters)
		assert foo_update.name == foo.name
		assert not hasattr(foo_update, "id")

	def test_cast_fooupdateparameters_to_foo(self):
		foo_update = FooUpdateParameters(name="updated_name")
		with pytest.raises(ValidationError):
			cast_as(foo_update, Foo)  # This should raise an error since 'id' is missing

	def test_cast_with_additional_fields(self):
		class Bar(BaseModel):
			name: str
			extra_field: int

		foo = Foo(id=1, name="test")
		with pytest.raises(ValueError):
			cast_as(foo, Bar)  # This should raise an error since 'extra_field' is missing

	def test_cast_with_missing_fields(self):
		class FooPartial(BaseModel):
			id: int

		foo = Foo(id=1, name="test")
		foo_partial = cast_as(foo, FooPartial)
		assert foo_partial.id == foo.id
		assert not hasattr(foo_partial, "name")


class TestEnsure:
	def test_ensure_not_none(self):
		assert ensure(5) == 5
		assert ensure("test") == "test"
		assert ensure([1, 2, 3]) == [1, 2, 3]

	def test_ensure_none_raises(self):
		with pytest.raises(TypeError, match="value was None"):
			ensure(None)
