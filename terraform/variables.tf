# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

variable "app_name" {
  description = "Name of the application in the Juju model"
  type        = string
  default     = "authentik-server"
}

variable "base" {
  description = "Operating system base for the charm (e.g. ubuntu@22.04)"
  type        = string
  default     = null
}

variable "channel" {
  description = "Channel to use when deploying the charm"
  type        = string
  default     = "latest/stable"
}

variable "config" {
  description = "Map of charm configuration options"
  type        = map(string)
  default     = {}
}

variable "constraints" {
  description = "Constraints string for the deployed application"
  type        = string
  default     = null
}

variable "model_uuid" {
  description = "UUID of the Juju model to deploy the charm into"
  type        = string
  nullable    = false
}

variable "revision" {
  description = "Charm revision to deploy. Null deploys the latest on the given channel"
  type        = number
  default     = null
}

variable "resources" {
  description = "Map of charm resources"
  type        = map(string)
  default     = {}
}

variable "units" {
  description = "Number of units to deploy"
  type        = number
  default     = 1
}
