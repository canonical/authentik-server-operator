# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

terraform {
  required_providers {
    juju = {
      source  = "juju/juju"
      version = "~> 2.2.0"
    }
  }

  required_version = ">= 1.6"
}
