# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

/**
 * # Terraform module for the authentik-server charm
 *
 * This is a Terraform module facilitating the deployment of the authentik-server
 * charm using the Juju Terraform provider.
 */

resource "juju_application" "authentik_server" {
  name        = var.app_name
  model_uuid  = var.model_uuid
  config      = var.config
  constraints = var.constraints
  resources   = var.resources
  units       = var.units
  trust       = true

  charm {
    name     = "authentik-server"
    base     = var.base
    channel  = var.channel
    revision = var.revision
  }
}

resource "juju_offer" "oauth" {
  name             = "oauth"
  model_uuid       = var.model_uuid
  application_name = juju_application.authentik_server.name
  endpoints        = ["oauth"]
}

