# llamazure.azrest : A REST client for the Azure API

## Usage

llamazure.azrest has 3 primary components:
1. an Engine for running requests
2. an OpenAPI Generator for creating bindings for Azure services
3. the Bindings created by the Generator and submitted to the Engine

The general workflow is:
1. use the Generator to codegen Bindings
2. create an Engine
3. use the Bindings to create requests
4. run those requests with the Engine

You only need to run regenrate the bindings to upgrade the version of llamazure or to change the version of the Azure API you're targeting.
If you're using the shell, you can use:

```shell
python3 llamazure-azrest-openapi 'https://raw.githubusercontent.com/Azure/azure-rest-api-specs/main/' 'specification/authorization/resource-manager/Microsoft.Authorization/stable/2022-04-01/authorization-RoleAssignmentsCalls.json' 'my/module/role_asn.py' 
```

If you're using the Pants build system, try something like:

```python
adhoc_tool(
	name="role_asn",
	runnable="//llamazure/azrest/openapi.py",  # TODO: adapt for out-of-tree
	args=[
		"https://raw.githubusercontent.com/Azure/azure-rest-api-specs/main/",
		"specification/authorization/resource-manager/Microsoft.Authorization/stable/2022-04-01/authorization-RoleAssignmentsCalls.json",
		"my/module/az",
	],
	output_directories=["my/module/az"],
	root_output_directory=".",
)

experimental_wrap_as_python_sources(
	name="azgen",
	inputs=[
		":role_asn",
        ...
	],
)
```

And then in your code:
```python
from azure.identity import DefaultAzureCredential
from llamazure.azrest.azrest import AzRest

from my.module.role_asn import AzRoleAssignments
# create the Engine
az = AzRest.from_credential(DefaultAzureCredential())

# use the Bindings to create the request
req = AzRoleAssignments.ListForScope(scope="/")

# run the request
role_assignments = az.call(req)
```

### Using the secret batching API

Azure lets you batch several requests into one request. This can save you round-trip time.

```python
from azure.identity import DefaultAzureCredential
from llamazure.azrest.azrest import AzRest
from llamazure.azrest.models import BatchReq

from my.module.role_asn import AzRoleAssignments

az = AzRest.from_credential(DefaultAzureCredential())
query_subscriptions: list[str] = [...]

# use the bindings to create multiple requests
reqs = [AzRoleAssignments.ListForSubscription(sub) for sub in query_subscriptions]
# gather those into a batch
# the `BatchReq.gather` method automatically assigns them IDs
batch_req = BatchReq.gather(reqs)
# you can also name them explicitly
named_reqs = {sub: AzRoleAssignments.ListForSubscription(sub) for sub in query_subscriptions}
batch_req = BatchReq(named_reqs)

az.call_batch(batch_req)
```

### Services with other domain

Some services need different hosts. For example, keyvaults use `https://myvault.vault.azure.net`.
Using these services requires creating a separate AzRest instance to execute those requests:

```python
from azure.identity import DefaultAzureCredential
from llamazure.azrest.azrest import AzRest

a = AzRest.from_credential(DefaultAzureCredential(), token_scope="https://vault.azure.net/.default", base_url="https://myvault.vault.azure.net")
```

### Manually constructing requests

You can build requests yourself

```python
from llamazure.azrest.models import Req

req = Req.get(
    name="List my spacecraft",  # this is a meaningful name for you. It will appear in logs
    path="/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/spaaaaaaaace/providers/Microsoft.Orbital/spacecrafts/potato",
    apiv="2022-11-01",
    ret_t=dict, # This is the return type you expect. You can use a Pydantic BaseModel. A Pydantic TypeAdapter is used to deserialise the return. 
)
```

For requests that expect a body, use a Pydantic BaseModel.

You can also modify existing requests. There are even some builtin helpers:

```python
from my.module.role_asn import AzRoleAssignments

secure_rg = "secure-rg"

my_req = AzRoleAssignments.ListForResourceGroup(my_subscription, secure_rg).named("list role assignments on secure rg")
```


## TODO

1. Odata parameters (x-ms-odata) (I'd have to think through the common elements with llamazure.msgraph)
2. Better retries of Batch elements
3. Enums (x-ms-enum)
4. Nullable (x-nullable)
5. Support path-level `parameters`

## Known Issues

- Pagination doesn't work if the nextLinkName is not "nextLink"

## X-MS Support

| support | extension                            | comments                                                                      |
|---------|--------------------------------------|-------------------------------------------------------------------------------| 
| no      | x-ms-skip-url-encoding               | priority:low really, supporting url encoding is the priority                  |
| no      | x-ms-enum                            | priority:hig                                                                  |
| no      | x-ms-parameter-grouping              | priority:low                                                                  |
| no      | x-ms-parameter-location              | priority:low                                                                  |
| yes     | x-ms-paths                           |                                                                               |
| no      | x-ms-client-name                     | priority:med will cause breaking changes in object names                      |
| no      | x-ms-external                        | priority:low                                                                  |
| no      | x-ms-discriminator-value             | priority:low The resources that require this are not priorities for me        |
| never   | x-ms-client-flatten                  | In all my experience with the API, this makes it harder to use in any context |
| mostly  | x-ms-parameterized-host              | supported, requires a separate AzRest instance                                |
| no      | x-ms-mutability                      | priority:low                                                                  |
| never   | x-ms-examples                        | No need for examples in code                                                  |
| yes     | x-ms-error-response                  | General error support                                                         |
| no      | x-ms-text                            | priority:low (only in file and blob operations)                               |
| no      | x-ms-client-default                  | priority:low You can do this with filters                                     |
| mostly  | x-ms-pageable                        |                                                                               |
| no      | x-ms-long-running-operation          | priority:mid                                                                  |
| no      | x-ms-long-running-operation-options  | priority:mid                                                                  |
| no      | x-nullable                           | priority:hig                                                                  |
| never   | x-ms-header-collection-prefix        | I think this isn't for me                                                     |
| never   | x-ms-internal                        | Rude (although it's not used... in the public api)                            |
| no      | x-ms-odata                           | priority:hig actually useful                                                  |
| never   | x-ms-azure-resource                  | I'm not generating Terraform providers... yet                                 |
| no      | x-ms-request-id                      | priority:low I think this might be necessary for some long operations         |
| no      | x-ms-client-request-id               | priority:low I think this might be necessary for some long operations         |
| no      | x-ms-arm-id-details                  | priority:mid Might be nice to accept/convert the real resource                |
| no      | x-ms-secret                          | priority:low seems more design-by-contract                                    |
| no      | x-ms-identifiers                     | priority:low                                                                  |
| never   | x-ms-azure-rbac-permissions-required | Not for me                                                                    |
