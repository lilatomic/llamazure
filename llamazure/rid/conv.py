"""Converters for different resource types"""

from llamazure.rid import mp, rid


def rid2mp(rid_obj: rid.AzObj) -> mp.AzObj:
	"""Convert a `rid` resource into its corresponding `mp` resource"""
	return mp.parse(rid.serialise(rid_obj))[1]


def mp2rid(mp_obj: mp.AzObj) -> rid.AzObj:
	"""Convert an `mp` resource into its corresponding `rid` resource"""
	return rid.parse(mp.serialise(mp_obj))
