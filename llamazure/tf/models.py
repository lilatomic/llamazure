from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass


class TFResource(ABC):
	"""A Terraform resource"""

	name: str
	t: str

	@abstractmethod
	def render(self) -> dict:
		"""Render the resource as JSON-serialisable data"""

	def subresources(self) -> list[TFResource]:
		"""Child resources"""
		return []


@dataclass
class AnyTFResource(TFResource):
	t: str
	name: str
	props: dict

	def render(self) -> dict:
		return self.props


@dataclass
class Terraform:
	resource: list[TFResource]

	def render(self):
		"""Render the terraform resources"""
		rendered_resources = defaultdict(dict)

		def register(resource: TFResource):
			rendered_resources[resource.t][resource.name] = resource.render()
			for subresource in resource.subresources():
				register(subresource)

		for resource in self.resource:
			register(resource)

		return {
			"resource": rendered_resources,
		}


def _pluralise(k: str, v: list[str], pluralise: str = "s") -> dict[str, str | list[str]]:
	"""Format the k-v pair, pluralising the k if necessary"""
	if len(v) == 1:
		return {k: v[0]}
	else:
		return {k + pluralise: v}
