# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

data "juju_model" "this" {
  uuid = var.model
}

data "juju_offer" "database" {
  url = var.postgresql_offer_url
}

data "juju_offer" "traefik_route" {
  url = var.traefik_route_offer_url
}

data "juju_offer" "metrics" {
  count = var.metrics_offer_url != null ? 1 : 0
  url   = var.metrics_offer_url
}

data "juju_offer" "tracing" {
  count = var.tracing_offer_url != null ? 1 : 0
  url   = var.tracing_offer_url
}

data "juju_offer" "logging" {
  count = var.logging_offer_url != null ? 1 : 0
  url   = var.logging_offer_url
}

data "juju_offer" "grafana_dashboard" {
  count = var.grafana_dashboard_offer_url != null ? 1 : 0
  url   = var.grafana_dashboard_offer_url
}
