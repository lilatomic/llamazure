"""Test and examples for the network helpers"""
import json

from llamazure.tf.models import Terraform
from llamazure.tf.network import NSG, NSGRule


class TestRender:
	def test_plural_nsgrule(self):
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
			"direction": "Inbound",
			"name": "n",
			"priority": 0,
			"protocol": "Tcp",
			"source_address_prefixes": ["1.1.1.1/32", "1.1.1.2/32"],
			"source_port_ranges": ["0", "1"],
		}
		assert a.render(0) == e


class TestExample:
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
			"security_rule": [
				{
					"name": "test123",
					"priority": 100,
					"direction": "Inbound",
					"access": "Allow",
					"protocol": "Tcp",
					"source_port_range": ["*"],
					"destination_port_range": ["*"],
					"source_address_prefix": ["*"],
					"destination_address_prefix": ["*"],
					"description": "",
				}
			],
			"tags": {
				"environment": "Production",
			},
		}

		assert a.render() == e

	def test_example(self):
		"""Test showing how to use the code"""

		tf = Terraform([
			NSG("n", "rg", "l", [])
		])

		assert json.dumps(tf.render()) == '{"resource": {"azurerm_network_security_group": {"n": {"name": "n", "resource_group_name": "rg", "location": "l", "security_rule": [], "tags": {}}}}}'