"""Integration tests for network resources"""

import json
import random
import subprocess

import pytest
from _pytest.fixtures import fixture

from llamazure.tf.models import Terraform
from llamazure.tf.network import NSG, NSGRule, OptNSGTotal


def test_shim():
	"""Make pytest succeed even when no tests are selected"""


@fixture
def random_nsg():
	"""Generate the name of a random NSG"""
	return "llamazure-tf-{:06d}".format(random.randint(0, int(1e6)))


def versions_tf(subscription_id):
	return (
		"""\
terraform {
	required_providers {
		azurerm = {
			source	= "hashicorp/azurerm"
			version = "=4.0.0"
		}
	}
}

provider "azurerm" {
	resource_provider_registrations = "none"
	subscription_id = "%s"
	features {}
}
"""
		% subscription_id
	)


class TestNetworkIntegration:
	"""Integration tests for network resources"""

	@pytest.mark.integration
	@pytest.mark.parametrize("opt_total", [OptNSGTotal(True), OptNSGTotal(False)])
	def test_network_integration(self, random_nsg, tmp_path, it_info, opt_total: OptNSGTotal):
		tf = Terraform(
			[
				NSG(
					random_nsg,
					"llamazure-tf-test",
					"Canada Central",
					rules=[
						NSGRule(name="Single", access=NSGRule.Access.Allow, direction=NSGRule.Direction.Outbound, src_addrs=["1.1.1.1/32"], src_ports=["443"]),
						NSGRule(name="Plural", access=NSGRule.Access.Allow, direction=NSGRule.Direction.Outbound, src_addrs=["1.1.1.1/32", "1.1.1.2/32"], src_ports=["80", "443"]),
					],
				)
			]
		)

		basedir = tmp_path / "tf"
		basedir.mkdir()

		with open(basedir / "versions.tf", mode="w", encoding="utf-8") as f:
			f.write(versions_tf(subscription_id=it_info["tf"]["subscription"]))

		with open(basedir / "nsg.tf.json", mode="w", encoding="utf-8") as f:
			json.dump(tf.render(), f, indent="\t")

		def run_tf(argv: list[str]):
			try:
				subprocess.run(["terraform", f"-chdir={basedir}", *argv], check=True, capture_output=True, text=True)
			except subprocess.CalledProcessError as e:
				print(json.dumps({"stdout": e.stdout, "stderr": e.stderr}, indent=2))
				raise AssertionError("deploying TF failed") from e

		run_tf(["init"])
		run_tf(["apply", "-auto-approve"])
		run_tf(["apply", "-destroy", "-auto-approve"])
