"""
Helpers for testing resource IDs

These helpers generate llamazure.rid.rid resources. Other implementations of resource IDs may use these for validation.
"""

import string
from typing import Union

from hypothesis.strategies import builds, composite, none, recursive, text, uuids

from llamazure.rid.rid import Resource, ResourceGroup, SubResource, Subscription

az_alnum = text(alphabet=list(string.ascii_letters + string.digits), min_size=1)
az_alnum_lower = text(alphabet=list(string.ascii_lowercase + string.digits), min_size=1)
st_subscription = builds(lambda u: Subscription(str(u)), uuids())
st_rg = builds(lambda sub, name: ResourceGroup(name, sub), st_subscription, az_alnum_lower)
st_resource_base = builds(
	lambda provider, res_type, name, rg_name, sub: Resource(provider, res_type, name, ResourceGroup(rg_name, sub) if rg_name else None, parent=None, sub=sub),
	az_alnum_lower,
	az_alnum_lower,
	az_alnum_lower,
	none() | az_alnum_lower,
	st_subscription,
)
st_subresource = builds(
	lambda res_type, name, rg_name, sub: SubResource(res_type, name, ResourceGroup(rg_name, sub) if rg_name else None, parent=None, sub=sub),
	az_alnum_lower.filter(lambda s: s not in {"subscriptions", "resourcegroups", "providers"}),  # "providers" is not valid as a subresource type and will trip up the parser
	az_alnum_lower,
	none() | az_alnum_lower,
	st_subscription,
)


@composite
def complex_resource(draw, res_gen) -> Union[Resource, SubResource]:
	"""Create a resource which may have parents"""
	child = draw(res_gen)
	parent = draw(res_gen)
	if isinstance(child, Resource):
		return parent.resource(child.provider, child.res_type, child.name)
	if isinstance(child, SubResource):
		return parent.subresource(child.res_type, child.name)
	else:
		raise RuntimeError("AAAA")


st_resource_complex = recursive(st_resource_base | st_subresource, complex_resource, max_leaves=6)
st_resource_any = st_subscription | st_rg | st_resource_base | st_subresource | st_resource_complex
