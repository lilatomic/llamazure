# llamazure.rid : Resource IDs you can use

The `llamazure.tresource` package provides a way to group Azure resources into their hierarchy. 

## Usage

There are several variants of Tresources.

- Plain `Tresource` : This tresource does not store any information about the resources except for their parsed resource ID. This is best for exploration and visualisation. For example, if you wanted to display all the VMs in a tenancy, this tresource would help you show them by subscription and resource group
- `TresourceData` : This tresource includes a space to put data. An obvious choice for the data would be the serialised JSON of the resource itself, which you could get from the graphapi or from the cli or through change events. You can also use the data for other information, like whether an object exists in IAC or whether someone knows what a resource is for.

## Examples

Load all resources into a tresource, indexable by rid, including data:

```python
from azure.identity import DefaultAzureCredential

from llamazure.azgraph.azgraph import Graph
from llamazure.rid import mp
from llamazure.tresource.mp import TresourceMPData

g = Graph.from_credential(DefaultAzureCredential())
resources = g.q("Resources")

t = TresourceMPData()

for resource in resources:
    t.set_data(mp.parse(resource["id"])[1], resource)
```

## Design notes
