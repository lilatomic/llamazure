from typing import Dict, Any

import pytest
from pydantic import TypeAdapter

from llamazure.azrest.azrest import AzRest
from llamazure.azrest.models import BatchReq, AzureError, Req, AzList


@pytest.fixture
def azr(credential) -> AzRest:
	return AzRest.from_credential(credential)


def sub_req(sub: str) -> Req:
	return Req.get("test-batch-single", f"{sub}/resourcegroups", "2022-09-01", AzList)

class TestBatches:
	def test_empty_batch__raises(self, azr):
		batch_req = BatchReq([])
		with pytest.raises(AzureError) as e:
			azr.call_batch(batch_req)
		assert e.value.error.code == "EmptyBatchRequest"

	def test_single_item(self, azr, it_info):
		batch_req = BatchReq([
			sub_req(it_info['scopes']['sub0'])
		])
		batch_res = azr.call_batch(batch_req)
		assert len(batch_res.responses) == 1
		for res in batch_res.responses:
			assert res.httpStatusCode == 200
			assert isinstance(res.content['value'], list)

	def test_multiple_items(self, azr, it_info):
		batch_req = BatchReq([
			sub_req(it_info['scopes']['sub0']),
			sub_req(it_info['scopes']['sub1']),
		])
		batch_res = azr.call_batch(batch_req)
		assert len(batch_res.responses) == 2
		for res in batch_res.responses:
			assert res.httpStatusCode == 200
			assert isinstance(res.content['value'], list)