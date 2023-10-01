# llamazure.rbac : Azure roles, users, and assignments

The `llamazure.rbac` package provides a helpful interface to Azure RBAC.

Benefits:
- a coherent view of roles and assignments
- automatically handles internals of the Azure RBAC model. For example, deleting a role will first delete all role assignments
- automatic retries and waits for the cloud to work

## rbac

### Usage

For roles definitions and role assignments, create `RoleOps` with an `AzRest` created by its `from_credential` method:

```python
from azure.identity import DefaultAzureCredential

from llamazure.azrest.azrest import AzRest
from llamazure.rbac.roles import RoleOps

role_ops = RoleOps(AzRest.from_credential(DefaultAzureCredential()))
```

For users and groups, create a `Users` or a `Groups` with a MSGraph created by their `from_credentials` method:

```python
from azure.identity import DefaultAzureCredential

from llamazure.msgraph.msgraph import Graph
from llamazure.rbac.resources import Groups, Users

users = Users(Graph.from_credential(DefaultAzureCredential()))
groups = Groups(Graph.from_credential(DefaultAzureCredential()))
```

#### Create a role

```python
from llamazure.rbac.roles import *

role = role_ops.rds.put(
    RoleDefinition.Properties(
        roleName="llamazure-rbac-asn",
        description="test finding assignments",
        permissions=[Permission(actions=["Microsoft.Authorization/*/read"])],
    ),
    scope="/subscriptions/00000000-0000-0000-0000-000000000000",
)
```

#### Assign a role

This will also automatically add the scope of assignment to the role's assignable scopes if necessary:

```python
me = users.current()
role_ops.ras.assign(principalId=me["id"], principalType="User", role_name=role.properties.name,scope="/subscriptions/00000000-0000-0000-0000-000000000000")
```

#### Delete a role

This will also delete all role assignments before deleting a role:

```python
role_ops.delete_role(role)
```

You can also delete a role by name:

```python
role_ops.delete_by_name("llamazure-rbac-asn")
```

#### Get users with their groups

```python
users.list_with_memberOf()
```

#### Get groups with their members

```python
groups.list_with_memberships()
```