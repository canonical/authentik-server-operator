# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

output "application" {
  description = "The deployed juju_application resource"
  value       = juju_application.authentik_server
}

output "provides" {
  description = "Map of provides endpoint names"
  value = {
    metrics-endpoint      = "metrics-endpoint"
    grafana-dashboard     = "grafana-dashboard"
    authentik-cluster     = "authentik-cluster"
    authentik-server-info = "authentik-server-info"
    oauth                 = "oauth"
  }
}

output "requires" {
  description = "Map of requires endpoint names"
  value = {
    logging         = "logging"
    tracing         = "tracing"
    pg-database     = "pg-database"
    ingress         = "ingress"
    receive-ca-cert = "receive-ca-cert"
    smtp            = "smtp"
  }
}
