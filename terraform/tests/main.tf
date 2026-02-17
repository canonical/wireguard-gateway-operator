# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

terraform {
  required_providers {
    juju = {
      version = "> 1.1.0"
      source  = "juju/juju"
    }
  }
}

provider "juju" {}

resource "juju_model" "test_model" {
  name = "test-wireguard-${formatdate("YYYYMMDDhhmmss", timestamp())}"
}

module "wireguard" {
  source     = "./.."
  app_name   = "wireguard"
  channel    = "latest/edge"
  model_uuid = juju_model.test_model.uuid
  # renovate: depName="wireguard-gateway"
  revision   = 3
}
