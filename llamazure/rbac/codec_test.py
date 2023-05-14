from llamazure.rbac import codec
from llamazure.rbac.models import QueryOpts, Req, Res, ResErr


class TestEncoder:
	"""Test the Encoder"""

	def test_encode(self):
		req = Req("empty", options=QueryOpts(top=5))
		enc = codec.Encoder().encode(req)
		assert enc == (req.query, {"$top": 5})


class TestDecoder:
	"""Test the Decoder"""

	empty_req = Req("empty")

	def test_decode_error(self):
		raw = {
			"error": {
				"code": "BadRequest",
				"message": "Resource not found for the segment 'aaaaaa'.",
				"innerError": {"date": "2023-03-27T01:54:21", "request-id": "78ac718a-0db7-4b97-8bd3-7448748164eb", "client-request-id": "78ac718a-0db7-4b97-8bd3-7448748164eb"},
			}
		}

		res = codec.Decoder().decode(self.empty_req, raw)

		assert isinstance(res, ResErr)
		assert res.innerError is None
		assert set(res.error_metadata.keys()) == {"date", "request-id", "client-request-id"}

	def test_decode_success(self):
		raw = {
			"@odata.context": "https://graph.microsoft.com/v1.0/$metadata#groups",
			"@odata.nextLink": "https://graph.microsoft.com/v1.0/groups?$top=1&$skiptoken=RFNwdAIAAQAAACpHcm91cF82MjI2ZDljZi03NzIzLTQwYjEtYTRlOC04MzEwZWNiOWY0OTkqR3JvdXBfNjIyNmQ5Y2YtNzcyMy00MGIxLWE0ZTgtODMxMGVjYjlmNDk5AAAAAAAAAAAAAAA",
			"value": [
				{
					"id": "00000000-0000-0000-0000-000000000000",
					"deletedDateTime": None,
					"classification": None,
					"createdDateTime": "2023-03-26T18:28:13Z",
					"creationOptions": [],
					"description": "Target group for integration tests",
					"displayName": "it-target-group-00",
					"expirationDateTime": None,
					"groupTypes": [],
					"isAssignableToRole": None,
					"mail": None,
					"mailEnabled": False,
					"mailNickname": "be45cfab-4",
					"membershipRule": None,
					"membershipRuleProcessingState": None,
					"onPremisesDomainName": None,
					"onPremisesLastSyncDateTime": None,
					"onPremisesNetBiosName": None,
					"onPremisesSamAccountName": None,
					"onPremisesSecurityIdentifier": None,
					"onPremisesSyncEnabled": None,
					"preferredDataLocation": None,
					"preferredLanguage": None,
					"proxyAddresses": [],
					"renewedDateTime": "2023-03-26T18:28:13Z",
					"resourceBehaviorOptions": [],
					"resourceProvisioningOptions": [],
					"securityEnabled": True,
					"securityIdentifier": "S-0-00-0-0000000000-0000000000-000000000-0000000000",
					"theme": None,
					"visibility": None,
					"onPremisesProvisioningErrors": [],
				}
			],
		}
		res = codec.Decoder().decode(self.empty_req, raw)

		assert isinstance(res, Res)
