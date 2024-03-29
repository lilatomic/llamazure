from llamazure.rid import mp
from llamazure.tresource.mp import MPData


def reformat_resources_for_tresource(resources):
	"""Reformat mp_resources for TresourceMPData"""
	for r in resources:
		path, azobj = mp.parse(r["id"])
		mpdata = MPData(azobj, r)
		yield path, mpdata
