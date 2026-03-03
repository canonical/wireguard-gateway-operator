# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variables {
  channel = "latest/edge"
  # renovate: depName="wireguard-gateway"
  revision = 1
}

run "basic_deploy" {
  module {
    source = "./tests"
  }

  assert {
    condition     = module.wireguard.app_name == "wireguard"
    error_message = "wireguard app_name did not match expected"
  }
}
