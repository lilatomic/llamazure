# llamazure.msgraph : Microsoft Graph client

The `llamazure.azgraph` package provides a usable client for the Microsoft Graph.

Benefits:
- no boilerplate
- easily navigate paginated queries

## msgraph

### Usage

Create a `Graph` with the `from_credential` and any of the standard Azure credentials.

```python
from azure.identity import DefaultAzureCredential

from llamazure.msgraph.msgraph import Graph

g = Graph.from_credential(DefaultAzureCredential())
```

#### Querying

Make a simple query with the `q` method, which will return your data directly:

```python
>>> g.q("me")
Res(req=Req(query='me', options=QueryOpts(count=None, expand=set(), filter=None, format=None, orderby=None, search=None, select=None, skip=None, top=None)), odata={'@odata.context': 'https://graph.microsoft.com/v1.0/$metadata#users/$entity'}, value={...}, nextLink=None)
```

Or specify options with the `query` method, which will return the full result object:

```python
>>> from llamazure.msgraph.models import Req

>>> g.query(Req("me", options=QueryOpts(expand={"memberOf"})))
Res(req=Req(query='me', options=QueryOpts(count=None, expand={'memberOf'}, filter=None, format=None, orderby=None, search=None, select=None, skip=None, top=None)), odata={'@odata.context': 'https://graph.microsoft.com/v1.0/$metadata#users(memberOf())/$entity'}, value={...}, nextLink=None)
```

#### Retries

Every query can be automatically retried by the retry policy. You can modify this by setting the `Graph.retry_policy` attribute:

```python
g.retry_policy = RetryPolicy(retries=10)
```

#### Pagination

Pagination is handled automatically. If you want to manually paginate, you can manually walk the pages:

```python
req = Req(query="users")

res0 = g.query_single(req)
res1 = g.query_next(req, res0)
res2 = g.query_next(req, res1)
```
