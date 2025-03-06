"""Test and examples for the network helpers"""

import json

from llamazure.tf.models import Terraform
from llamazure.tf.network import NSG, NSGRule, OptNSGTotal


class TestRender:
	"""Test rendering"""

	def test_plural_nsgrule(self):
		"""Test that plurals render correctly"""
		a = NSGRule(
			name="n",
			access=NSGRule.Access.Allow,
			direction=NSGRule.Direction.Inbound,
			src_ports=["0", "1"],
			dst_ports=["2", "3"],
			src_addrs=["1.1.1.1/32", "1.1.1.2/32"],
			dst_addrs=["2.1.1.1/32", "2.1.1.2/32"],
		)
		e = {
			"access": "Allow",
			"description": "",
			"destination_address_prefixes": ["2.1.1.1/32", "2.1.1.2/32"],
			"destination_port_ranges": ["2", "3"],
			"destination_application_security_group_ids": [],
			"direction": "Inbound",
			"name": "n",
			"priority": 0,
			"protocol": "Tcp",
			"source_address_prefixes": ["1.1.1.1/32", "1.1.1.2/32"],
			"source_port_ranges": ["0", "1"],
			"source_application_security_group_ids": [],
			"network_security_group_name": "nsg_name",
			"resource_group_name": "rg",
		}
		assert a.render_as_subresources("nsg_name", "rg", 0) == e


class TestExample:
	"""Test the example from the Terraform provider"""

	def test_terraform_example(self):
		"""Test the example from the Terraform provider"""
		a = NSG(
			name="acceptanceTestSecurityGroup1",
			rg="example-resources",
			location="West Europe",
			rules=[NSGRule("test123", NSGRule.Access.Allow, NSGRule.Direction.Inbound)],
			tags={
				"environment": "Production",
			},
		)
		e = {
			"name": "acceptanceTestSecurityGroup1",
			"location": "West Europe",
			"resource_group_name": "example-resources",
			"security_rule": None,
			"tags": {
				"environment": "Production",
			},
		}

		assert a.render() == e

		es = [
			{
				"name": "test123",
				"priority": 100,
				"direction": "Inbound",
				"access": "Allow",
				"protocol": "Tcp",
				"source_port_range": "*",
				"destination_port_range": "*",
				"source_address_prefix": "*",
				"destination_address_prefix": "*",
				"destination_application_security_group_ids": [],
				"source_application_security_group_ids": [],
				"description": "",
				"network_security_group_name": "${azurerm_network_security_group.acceptanceTestSecurityGroup1.name}",
				"resource_group_name": "example-resources",
			}
		]
		assert [rule.render() for rule in a.subresources()] == es

	def test_opt_total(self):
		"""Test that the `opt_total` renders correctly"""

		a = NSG(
			name="acceptanceTestSecurityGroup1",
			rg="example-resources",
			location="West Europe",
			rules=[NSGRule("test123", NSGRule.Access.Allow, NSGRule.Direction.Inbound)],
			tags={
				"environment": "Production",
			},
			opt_total=OptNSGTotal(True),
		)

		e = {
			"name": "acceptanceTestSecurityGroup1",
			"location": "West Europe",
			"resource_group_name": "example-resources",
			"security_rule": [
				{
					"name": "test123",
					"priority": 100,
					"direction": "Inbound",
					"access": "Allow",
					"protocol": "Tcp",
					"source_port_range": "*",
					"destination_port_range": "*",
					"source_address_prefix": "*",
					"destination_address_prefix": "*",
					"destination_application_security_group_ids": [],
					"source_application_security_group_ids": [],
					"description": "",
				}
			],
			"tags": {
				"environment": "Production",
			},
		}
		assert a.render() == e

	def test_example(self):
		"""Test showing how to use the code generation"""

		tf = Terraform([NSG("n", "rg", "l", [])])

		assert (
			json.dumps(tf.render())
			== '{"resource": {"azurerm_network_security_group": {"n": {"name": "n", "resource_group_name": "rg", "location": "l", "security_rule": null, "tags": {}}}}}'
		)
