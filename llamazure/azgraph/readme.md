# llamazure.azgraph : Azure Resources Graph client

The `llamazure.azgraph` package provides a usable client for the Azure Resource Graph.

Benefits:
- automatically queries all your subscriptions
- no boilerplate
- easily navigate paginated queries

## azgraph

### Usage

Create a `Graph` with the `from_credential` and any of the standard Azure credentials.

```python
from azure.identity import DefaultAzureCredential

from llamazure.azgraph.azgraph import Graph

g = Graph.from_credential(DefaultAzureCredential())
```

#### Querying

Make a simple query with the `q` method, which will return your data directly:

```python
>>> g.q("Resources | project id, name, type, location | limit 5")
[{'id': '/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg0/providers/Microsoft.Storage/storageAccounts/sa0', 'name': 'sa0', 'type': 'microsoft.storage/storageaccounts', 'location': 'canadacentral'}]
```

Or specify options with the `query` method, which will return the full result object:

```python
>>> from llamazure.azgraph.models import Req

>>> g.query(Req(query="Resources | project id, name, type, location | limit 1", subscriptions=g.subscriptions, options={"$skip": 1},))
Res(req=Req(query='Resources | project id, name, type, location | limit 1', subscriptions=('00000000-0000-0000-0000-000000000000',), facets=(), managementGroupId=None, options={'$skip': 1}), totalRecords=1, count=1, resultTruncated='false', facets=[], data=[{'id': '/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/NetworkWatcherRG/providers/Microsoft.Network/networkWatchers/NetworkWatcher_canadacentral', 'name': 'NetworkWatcher_canadacentral', 'type': 'microsoft.network/networkwatchers', 'location': 'canadacentral'}], skipToken=None)
```

#### Retries

Every query can be automatically retried by the retry policy. You can modify this by setting the `Graph.retry_policy` attribute:

```python
g.retry_policy = RetryPolicy(retries=10)
```

#### Pagination

Pagination is handled automatically. If you want to manually paginate, you can manually walk the pages:

```python
req = Req(query="Resources | project id, name, type, location | limit 5", subscriptions=g.subscriptions)

res0 = g.query_single(req)
res1 = g.query_next(req, res0)
res2 = g.query_next(req, res1)
```
