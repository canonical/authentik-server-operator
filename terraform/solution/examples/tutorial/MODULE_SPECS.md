
---
## Providers

| Name | Version |
|------|---------|
| <a name="provider_juju"></a> [juju](#provider\_juju) | 1.0.0 |
---
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.6 |
| <a name="requirement_juju"></a> [juju](#requirement\_juju) | >= 1.0 |
---
## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_certificates"></a> [certificates](#input\_certificates) | The configurations of the self-signed-certificates application. | <pre>object({<br/>    units   = optional(number, 1)<br/>    trust   = optional(bool, true)<br/>    config  = optional(map(string), {})<br/>    channel = optional(string, "1/stable")<br/>    base    = optional(string, "ubuntu@22.04")<br/>  })</pre> | `{}` | no |
| <a name="input_traefik"></a> [traefik](#input\_traefik) | The configurations of the Traefik application. | <pre>object({<br/>    units   = optional(number, 1)<br/>    trust   = optional(bool, true)<br/>    config  = optional(map(string), {})<br/>    channel = optional(string, "latest/edge")<br/>    base    = optional(string, "ubuntu@22.04")<br/>  })</pre> | `{}` | no |
| <a name="input_postgresql"></a> [postgresql](#input\_postgresql) | The configurations of the PostgreSQL application. | <pre>object({<br/>    units   = optional(number, 1)<br/>    trust   = optional(bool, true)<br/>    config  = optional(map(string), {})<br/>    channel = optional(string, "14/stable")<br/>    base    = optional(string, "ubuntu@22.04")<br/>  })</pre> | `{}` | no |
| <a name="input_authentik_server"></a> [authentik\_server](#input\_authentik\_server) | The configurations of the Authentik Server application. | <pre>object({<br/>    name        = optional(string, "authentik-server")<br/>    units       = optional(number, 1)<br/>    channel     = optional(string, "latest/stable")<br/>    base        = optional(string, null)<br/>    trust       = optional(bool, true)<br/>    config      = optional(map(string), {})<br/>    constraints = optional(string, null)<br/>    revision    = optional(number, null)<br/>    resources   = optional(map(string), {})<br/>  })</pre> | `{}` | no |
| <a name="input_authentik_worker"></a> [authentik\_worker](#input\_authentik\_worker) | The configurations of the Authentik Worker application. | <pre>object({<br/>    name        = optional(string, "authentik-worker")<br/>    units       = optional(number, 1)<br/>    channel     = optional(string, "latest/edge")<br/>    base        = optional(string, null)<br/>    trust       = optional(bool, true)<br/>    config      = optional(map(string), {})<br/>    constraints = optional(string, null)<br/>    revision    = optional(number, null)<br/>    resources   = optional(map(string), {})<br/>  })</pre> | `{}` | no |
| <a name="input_authentik_ldap_outpost"></a> [authentik\_ldap\_outpost](#input\_authentik\_ldap\_outpost) | The configurations of the Authentik LDAP Outpost application. | <pre>object({<br/>    name        = optional(string, "authentik-ldap-outpost")<br/>    units       = optional(number, 1)<br/>    channel     = optional(string, "latest/stable")<br/>    base        = optional(string, null)<br/>    trust       = optional(bool, true)<br/>    config      = optional(map(string), {})<br/>    constraints = optional(string, null)<br/>    revision    = optional(number, null)<br/>    resources   = optional(map(string), {})<br/>  })</pre> | `{}` | no |
---
## Outputs

No outputs.
