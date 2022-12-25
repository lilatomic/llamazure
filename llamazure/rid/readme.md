# llamazure.rid : Resource IDs you can use

The `llamazure.rid` package provides a usable resource ID parser. 

Benefits:
- quickly get the actual resource targetted and not the basemost resource (for example, easily get a lock and not the resource it's on)
- differentiate subscriptions, resource groups, resources, and child resources
- preserve resource tree while keeping resource group and subscription information available
- automatic case normalisation (seriously what's up with that) 

This library includes several implementations of resource ID parsing. `rid` produces object-based resources; `mp` produces materialised-path based resources. Which to use? The `mp` makes it easy to traverse the bodies of Azure resources to reference other Azure resources. For example, if you have a Microsoft.Network/virtualNetworks and you want to show all of its ipConfigurations: You might get the virtualNetwork, list all ipConfigurations, and then join on the resource ID. In contrast, `rid` is harder to traverse azure resource data but easier to traverse the hierarchy. For example, it is very easy to get information about the target of a lock from the lock itself. It's also convenient to place `rid` into a tree structure, such as `llamazure.rid.tresource`; while `mp` use the materialised-path format for representing tree structures in relational systems.

## rid : object-based resources

### Usage

Just call `parse` to turn resource IDs into objects. That's it. The resource you want is the result, all the other information is chained in.
You can also ask for the chain directly using the `parse_chain` method. This returns a list of all the parents of the resource, starting at the subscription. Having the chain is useful if you intend to use the hierarchy of resources, like pushing resources into a `Tresource` for the tree structure.

You'll know if a resource is a child resource if it has a non-None parent resource. It is a root resource if parent is None.

### Examples

```python
from llamazure.rid.rid import parse, Resource, ResourceGroup, Subscription
p = parse("/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/example/providers/Microsoft.Example/example_type/example_resource")

assert p == Resource(provider='microsoft.example',
         res_type='example_type',
         name='example_resource',
         rg=ResourceGroup(name='example',
                          sub=Subscription(uuid='00000000-0000-0000-0000-000000000000')),
         sub=Subscription(uuid='00000000-0000-0000-0000-000000000000'),
         parent=None)
```

## mp : materialised-path-based resources

### Usage

Just call `parse` to turn resource IDs into tuples of the path and the object. That's it. 
You can also get the parsed chain directly by using the `parse_chain` method. Having the chain might be less useful for `mp` than for `rid`. Materialised paths are often used to avoid having to join on parents, so having the parents may not be as helpful.

### Examples

Parse the resource ID:

```python
from llamazure.rid.mp import parse, Resource
path, resource = parse("/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/example/providers/Microsoft.Example/example_type/example_resource")

assert resource == Resource(
    path=path,
    provider='microsoft.example',
    res_type='example_type',
    name='example_resource',
    rg="/subscriptions/00000000-0000-0000-0000-000000000000/resourcegroups/example",
    sub="/subscriptions/00000000-0000-0000-0000-000000000000"
)
```

Parse many resource IDs and convert them into a lookup table:

```python
from llamazure.rid.mp import parse
resource_ids = [f"/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/example/providers/Microsoft.Example/example_type/example_resource{i}" for i in range(10)]

resources = dict(parse(rid) for rid in resource_ids)
```


## Design notes

### Denormalised RG and Subscription

Denormalising the data by injecting the rg and subscription in every resource in the chain increases the usability. You can get this information directly, without having to walk up the tree. Also, not every resource has a resource group, so the data model already has to be looser to accomodate that fact. Denormalising also helps with the implementation somewhat, since we can just push forward with None in the resource group. 

### Classes for modelling

I used classes to model the type of object you get back. Sometimes this is annoying, like when you can get a Resource or a SubResource. But that's the reality of Azure.
