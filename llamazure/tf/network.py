from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

from llamazure.tf.models import AnyTFResource, TFResource, _pluralise


class Counter:
	"""Incrementing counter, useful for generating priorities"""

	def __init__(self, initial_value=0):
		self._initial_value = initial_value
		self._counter: dict[str, int] = defaultdict(lambda: initial_value)

	def incr(self, name: str):
		"""Get the current value and increment the counter for the given name"""
		v = self._counter[name]
		self._counter[name] += 1
		return v


def _pluralise_for_azurerm(k: str, v: list[str], pluralise: str = "s") -> dict[str, str]:
	"""Azure needs both the plural and singular form. Sucks"""
	if len(v) == 1:
		return {k: v[0], k + pluralise: []}
	else:
		return {k: None, k + pluralise: v}


@dataclass
class NSG(TFResource):
	"""An azurerm_network_security_group resource"""

	name: str
	rg: str
	location: str
	rules: list[NSGRule]
	tags: dict[str, str] = field(default_factory=dict)

	@property
	def t(self) -> str:
		return "azurerm_network_security_group"

	def render(self) -> dict:
		"""Render for tf-json"""
		return {
			"name": self.name,
			"resource_group_name": self.rg,
			"location": self.location,
			"security_rule": [],
			"tags": self.tags,
		}

	def subresources(self) -> list[TFResource]:
		counter = Counter(initial_value=100)

		return [
			AnyTFResource(
				name="%s-%s" % (self.name, rule.name),
				t="azurerm_network_security_rule",
				props=rule.render("${%s.%s.name}" % (self.t, self.name), self.rg, counter.incr(rule.direction)),
			)
			for rule in self.rules
		]


@dataclass
class NSGRule:
	"""An azurerm_network_security_rule resource"""

	name: str
	access: Access
	direction: Direction

	protocol: str = "Tcp"
	src_ports: list[str] = field(default_factory=lambda: ["*"])
	src_addrs: list[str] = field(default_factory=lambda: ["*"])
	src_sgids: list[str] = field(default_factory=lambda: [])
	dst_ports: list[str] = field(default_factory=lambda: ["*"])
	dst_addrs: list[str] = field(default_factory=lambda: ["*"])
	dst_sgids: list[str] = field(default_factory=lambda: [])

	description: str = ""

	class Access(Enum):
		"""Access type"""

		Allow: str = "Allow"
		Deny: str = "Deny"

	class Direction(Enum):
		"""Direction type"""

		Inbound: str = "Inbound"
		Outbound: str = "Outbound"

	def render(self, nsg_name: str, rg: str, priority: int):
		"""Render for tf-json"""
		return {
			"name": self.name,
			"description": self.description,
			"protocol": self.protocol,
			**_pluralise("source_port_range", self.src_ports),
			**_pluralise("destination_port_range", self.dst_ports),
			**_pluralise("source_address_prefix", self.src_addrs, pluralise="es"),
			**_pluralise("destination_address_prefix", self.dst_addrs, pluralise="es"),
			"source_application_security_group_ids": self.src_sgids,
			"destination_application_security_group_ids": self.dst_sgids,
			"access": self.access.value,
			"priority": priority,
			"direction": self.direction.value,
			"resource_group_name": rg,
			"network_security_group_name": nsg_name,
		}
