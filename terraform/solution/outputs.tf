# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

output "authentik_server_app_name" {
  description = "The name of the deployed Authentik Server application"
  value       = module.authentik_server.application.name
}

output "authentik_worker_app_name" {
  description = "The name of the deployed Authentik Worker application"
  value       = module.authentik_worker.application.name
}

output "authentik_ldap_outpost_app_name" {
  description = "The name of the deployed Authentik LDAP Outpost application"
  value       = module.authentik_ldap_outpost.application.name
}
