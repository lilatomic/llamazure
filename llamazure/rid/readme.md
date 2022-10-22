# llamazure.rid : Resource IDs you can use

The `llamazure.rid` package provides a usable resource ID parser. 

Benefits:
- quickly get the actual resource targetted and not the basemost resource (for example, easily get a lock and not the resource it's on)
- differentiate subscriptions, resource groups, resources, and child resources
- preserve resource tree while keeping resource group and subscription information available
- automatic case normalisation (seriously what's up with that) 

## Usage

Just call `parse` to turn resource IDs into objects. That's it. The resource you want is the result, all the other information is chained in.

You'll know if a resource is a child resource if it has a non-None parent resource. It is a root resource if parent is None.

## Examples

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

## Design notes

### Denormalised RG and Subscription

Denormalising the data by injecting the rg and subscription in every resource in the chain increases the usability. You can get this information directly, without having to walk up the tree. Also, not every resource has a resource group, so the data model already has to be looser to accomodate that fact. Denormalising also helps with the implementation somewhat, since we can just push forward with None in the resource group. 

### Classes for modelling

I used classes to model the type of object you get back. Sometimes this is annoying, like when you can get a Resource or a SubResource. But that's the reality of Azure.
