# llamazure.azrest : A REST client for the Azure API

## Usage

### Services with other domain

Some services need different hosts. For example, keyvaults use `https://myvault.vault.azure.net`.
Using these services requires creating a separate AzRest instance to execute those requests:

```python
from azure.identity import DefaultAzureCredential
from llamazure.azrest.azrest import AzRest

a = AzRest.from_credential(DefaultAzureCredential(), token_scope="https://vault.azure.net/.default", base_url="https://myvault.vault.azure.net")
```

## TODO

1. Batch API
2. Odata parameters (x-ms-odata) (I'd have to think through the common elements with llamazure.msgraph)

## Known Issues

- Pagination doesn't work if the nextLinkName is not nextLink

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
| no      | x-ms-error-response                  | priority:high General error support                                           |
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
