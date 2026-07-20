# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

module "authentik_server" {
  source = "../"

  model_uuid  = data.juju_model.this.uuid
  app_name    = var.authentik_server.name
  units       = var.authentik_server.units
  channel     = var.authentik_server.channel
  base        = var.authentik_server.base
  config      = var.authentik_server.config
  constraints = var.authentik_server.constraints
  revision    = var.authentik_server.revision
  resources   = var.authentik_server.resources
}

module "authentik_worker" {
  source = "github.com/canonical/authentik-worker-operator//terraform"

  model_uuid  = data.juju_model.this.uuid
  app_name    = var.authentik_worker.name
  units       = var.authentik_worker.units
  channel     = var.authentik_worker.channel
  base        = var.authentik_worker.base
  config      = var.authentik_worker.config
  constraints = var.authentik_worker.constraints
  revision    = var.authentik_worker.revision
  resources   = var.authentik_worker.resources
}

module "authentik_ldap_outpost" {
  source = "github.com/canonical/authentik-ldap-outpost-operator//terraform"

  model_uuid  = data.juju_model.this.uuid
  app_name    = var.authentik_ldap_outpost.name
  units       = var.authentik_ldap_outpost.units
  channel     = var.authentik_ldap_outpost.channel
  base        = var.authentik_ldap_outpost.base
  config      = var.authentik_ldap_outpost.config
  constraints = var.authentik_ldap_outpost.constraints
  revision    = var.authentik_ldap_outpost.revision
  resources   = var.authentik_ldap_outpost.resources
}
