# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

variable "certificates" {
  description = "The configurations of the self-signed-certificates application."
  type = object({
    units   = optional(number, 1)
    trust   = optional(bool, true)
    config  = optional(map(string), {})
    channel = optional(string, "1/stable")
    base    = optional(string, "ubuntu@22.04")
  })
  default = {}
}

variable "traefik" {
  description = "The configurations of the Traefik application."
  type = object({
    units   = optional(number, 1)
    trust   = optional(bool, true)
    config  = optional(map(string), {})
    channel = optional(string, "latest/edge")
    base    = optional(string, "ubuntu@22.04")
  })
  default = {}
}

variable "postgresql" {
  description = "The configurations of the PostgreSQL application."
  type = object({
    units   = optional(number, 1)
    trust   = optional(bool, true)
    config  = optional(map(string), {})
    channel = optional(string, "14/stable")
    base    = optional(string, "ubuntu@22.04")
  })
  default = {}
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
