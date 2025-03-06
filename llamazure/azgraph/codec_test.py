"""Test encoding Req and decoding Res and ResErr"""

import json

from llamazure.azgraph.codec import Decoder, Encoder
from llamazure.azgraph.models import Req, Res, ResErr


class TestEncoder:
	"""Test the Encoder"""

	empty_req = Req("", ("00000000-0000-0000-0000-000000000000",))

	def test_encode(self):
		enc = json.dumps(self.empty_req, cls=Encoder)
		assert enc == '{"query": "", "subscriptions": ["00000000-0000-0000-0000-000000000000"], "facets": [], "managementGroupId": null, "options": {}}'


class TestDecoder:
	"""Test the Decoder"""

	empty_req = Req("", ("00000000-0000-0000-0000-000000000000",))

	def test_decode_syntax_error(self):
		body = {
			"error": {
				"code": "BadRequest",
				"message": "Please provide below info when asking for support: timestamp = 2023-02-19T03:50:34.1908792Z, correlationId = 00000000-0000-0000-0000-000000000000.",
				"details": [
					{
						"code": "InvalidQuery",
						"message": "Query is invalid. Please refer to the documentation for the Azure Resource Graph service and fix the error before retrying.",
					},
					{"code": "ParserFailure", "message": "ParserFailure", "line": 1, "characterPositionInLine": 12, "token": "syntax"},
					{"code": "ParserFailure", "message": "ParserFailure", "line": 1, "characterPositionInLine": 19, "token": "error"},
				],
			}
		}
		res = Decoder().decode(self.empty_req, body)

		assert isinstance(res, ResErr)
		assert len(res.details) == 3

	def test_decode_success(self):
		body = {
			"totalRecords": 7,
			"count": 3,
			"data": [
				{"id": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/it-azgraph/providers/Microsoft.Network/networkInterfaces/nic-0"},
				{"id": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/it-azgraph/providers/Microsoft.Network/networkInterfaces/nic-1"},
				{"id": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/it-azgraph/providers/Microsoft.Network/networkInterfaces/nic-2"},
			],
			"facets": [],
			"resultTruncated": "false",
			"$skipToken": "ew0KICAiJGlkIjogIjEiLA0KICAiTWF4Um93cyI6IDMsDQogICJSb3dzVG9Ta2lwIjogNCwNCiAgIkt1c3RvQ2x1c3RlclVybCI6ICJodHRwczovL2FyZy1ldXMtbmluZS1zZi5hcmcuY29yZS53aW5kb3dzLm5ldCINCn0=",  # noqa: E501
		}
		res = Decoder().decode(self.empty_req, body)

		assert isinstance(res, Res)
		assert len(res.data) == 3
		assert res.skipToken
