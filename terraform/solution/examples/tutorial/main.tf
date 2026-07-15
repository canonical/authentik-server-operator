# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

resource "juju_model" "core" {
  name = "core"
}

module "certificates" {
  source = "github.com/canonical/self-signed-certificates-operator//terraform?ref=rev443"

  model_uuid = juju_model.core.uuid
  app_name   = "self-signed-certificates"

  config  = var.certificates.config
  units   = var.certificates.units
  channel = var.certificates.channel
  base    = var.certificates.base

  depends_on = [juju_model.core]
}

module "traefik" {
  source = "github.com/canonical/traefik-k8s-operator//terraform?ref=rev259"

  model_uuid = juju_model.core.uuid
  app_name   = "traefik-public"

  config  = var.traefik.config
  units   = var.traefik.units
  channel = var.traefik.channel

  depends_on = [juju_model.core, module.certificates]
}

module "postgresql" {
  source = "github.com/canonical/postgresql-k8s-operator//terraform"

  model_uuid = juju_model.core.uuid
  app_name   = "postgresql-k8s"

  units   = var.postgresql.units
  config  = var.postgresql.config
  channel = var.postgresql.channel
  base    = var.postgresql.base

  storage_directives = {
    pgdata = "10G"
  }

  depends_on = [juju_model.core]
}

resource "juju_model" "authentik" {
  name = "authentik"
}

module "authentik" {
  source = "../../" # Referencing the parent solution module (terraform/solution)
  model  = juju_model.authentik.uuid

  postgresql_offer_url    = juju_offer.postgresql.url
  traefik_route_offer_url = juju_offer.traefik_route.url

  authentik_server       = var.authentik_server
  authentik_worker       = var.authentik_worker
  authentik_ldap_outpost = var.authentik_ldap_outpost

  depends_on = [juju_model.authentik]
}
