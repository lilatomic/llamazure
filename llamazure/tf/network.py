from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

from llamazure.tf.models import _pluralise, TFResource


class Counter:
	def __init__(self, initial_value=0):
		self._initial_value = initial_value
		self._counter: dict[str, int] = defaultdict(lambda: initial_value)

	def incr(self, name: str):
		v = self._counter[name]
		self._counter[name] += 1
		return v


@dataclass
class NSG(TFResource):
	name: str
	rg: str
	location: str
	rules: list[NSGRule]
	tags: dict[str, str] = field(default_factory=dict)

	@property
	def t(self) -> str:
		return "azurerm_network_security_group"

	def render(self) -> dict:
		counter = Counter(initial_value=100)
		rendered_rules = []

		for rule in self.rules:
			rendered_rules.append(rule.render(counter.incr(rule.direction)))

		return {
			"name": self.name,
			"resource_group_name": self.rg,
			"location": self.location,
			"security_rule": rendered_rules,
			"tags": self.tags,
		}


@dataclass
class NSGRule:
	name: str
	access: Access
	direction: Direction

	protocol: str = "Tcp"
	src_ports: list[str] = field(default_factory=lambda: ["*"])
	src_addrs: list[str] = field(default_factory=lambda: ["*"])
	dst_ports: list[str] = field(default_factory=lambda: ["*"])
	dst_addrs: list[str] = field(default_factory=lambda: ["*"])

	description: str = ""

	class Access(Enum):
		Allow: str = "Allow"
		Deny: str = "Deny"

	class Direction(Enum):
		Inbound: str = "Inbound"
		Outbound: str = "Outbound"

	def render(self, priority: int):
		return {
			"name": self.name,
			"description": self.description,
			"protocol": self.protocol,
			**_pluralise("source_port_range", self.src_ports),
			**_pluralise("destination_port_range", self.dst_ports),
			**_pluralise("source_address_prefix", self.src_addrs, pluralise="es"),
			**_pluralise("destination_address_prefix", self.dst_addrs, pluralise="es"),
			"access": self.access.value,
			"priority": priority,
			"direction": self.direction.value,
		}
