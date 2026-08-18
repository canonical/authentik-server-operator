# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

variable "model" {
  description = "The UUID of the Juju model to deploy the Authentik services into."
  type        = string
}

variable "postgresql_offer_url" {
  description = "PostgreSQL Juju Offer URL (cross-model DB endpoint)"
  type        = string
}

variable "traefik_route_offer_url" {
  description = "Traefik Route Juju Offer URL (cross-model Ingress endpoint)"
  type        = string
}

variable "authentik_server" {
  description = "The configurations of the Authentik Server application."
  type = object({
    name        = optional(string, "authentik-server")
    units       = optional(number, 1)
    channel     = optional(string, "latest/stable")
    base        = optional(string, null)
    trust       = optional(bool, true)
    config      = optional(map(string), {})
    constraints = optional(string, null)
    revision    = optional(number, null)
    resources   = optional(map(string), {})
  })
  default = {}
}

variable "authentik_worker" {
  description = "The configurations of the Authentik Worker application."
  type = object({
    name        = optional(string, "authentik-worker")
    units       = optional(number, 1)
    channel     = optional(string, "latest/stable")
    base        = optional(string, null)
    trust       = optional(bool, true)
    config      = optional(map(string), {})
    constraints = optional(string, null)
    revision    = optional(number, null)
    resources   = optional(map(string), {})
  })
  default = {}
}

variable "authentik_ldap_outpost" {
  description = "The configurations of the Authentik LDAP Outpost application."
  type = object({
    name        = optional(string, "authentik-ldap-outpost")
    units       = optional(number, 1)
    channel     = optional(string, "latest/stable")
    base        = optional(string, null)
    trust       = optional(bool, true)
    config      = optional(map(string), {})
    constraints = optional(string, null)
    revision    = optional(number, null)
    resources   = optional(map(string), {})
  })
  default = {}
}

variable "metrics_offer_url" {
  description = "Optional Metrics Offer URL for COS integration"
  type        = string
  default     = null
}

variable "tracing_offer_url" {
  description = "Optional Tracing Offer URL for COS integration"
  type        = string
  default     = null
}

variable "logging_offer_url" {
  description = "Optional Logging Offer URL for COS integration"
  type        = string
  default     = null
}

variable "grafana_dashboard_offer_url" {
  description = "Optional Grafana Dashboard Offer URL for COS integration"
  type        = string
  default     = null
}
