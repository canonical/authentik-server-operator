
---
## Providers

| Name | Version |
|------|---------|
| <a name="provider_juju"></a> [juju](#provider\_juju) | ~> 1.0.0 |
---
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.6 |
| <a name="requirement_juju"></a> [juju](#requirement\_juju) | ~> 1.0.0 |
---
## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_model"></a> [model](#input\_model) | The UUID of the Juju model to deploy the Authentik services into. | `string` | n/a | yes |
| <a name="input_postgresql_offer_url"></a> [postgresql\_offer\_url](#input\_postgresql\_offer\_url) | PostgreSQL Juju Offer URL (cross-model DB endpoint) | `string` | n/a | yes |
| <a name="input_traefik_route_offer_url"></a> [traefik\_route\_offer\_url](#input\_traefik\_route\_offer\_url) | Traefik Route Juju Offer URL (cross-model Ingress endpoint) | `string` | n/a | yes |
| <a name="input_authentik_server"></a> [authentik\_server](#input\_authentik\_server) | The configurations of the Authentik Server application. | <pre>object({<br/>    name        = optional(string, "authentik-server")<br/>    units       = optional(number, 1)<br/>    channel     = optional(string, "latest/stable")<br/>    base        = optional(string, null)<br/>    trust       = optional(bool, true)<br/>    config      = optional(map(string), {})<br/>    constraints = optional(string, null)<br/>    revision    = optional(number, null)<br/>    resources   = optional(map(string), {})<br/>  })</pre> | `{}` | no |
| <a name="input_authentik_worker"></a> [authentik\_worker](#input\_authentik\_worker) | The configurations of the Authentik Worker application. | <pre>object({<br/>    name        = optional(string, "authentik-worker")<br/>    units       = optional(number, 1)<br/>    channel     = optional(string, "latest/edge")<br/>    base        = optional(string, null)<br/>    trust       = optional(bool, true)<br/>    config      = optional(map(string), {})<br/>    constraints = optional(string, null)<br/>    revision    = optional(number, null)<br/>    resources   = optional(map(string), {})<br/>  })</pre> | `{}` | no |
| <a name="input_authentik_ldap_outpost"></a> [authentik\_ldap\_outpost](#input\_authentik\_ldap\_outpost) | The configurations of the Authentik LDAP Outpost application. | <pre>object({<br/>    name        = optional(string, "authentik-ldap-outpost")<br/>    units       = optional(number, 1)<br/>    channel     = optional(string, "latest/stable")<br/>    base        = optional(string, null)<br/>    trust       = optional(bool, true)<br/>    config      = optional(map(string), {})<br/>    constraints = optional(string, null)<br/>    revision    = optional(number, null)<br/>    resources   = optional(map(string), {})<br/>  })</pre> | `{}` | no |
| <a name="input_metrics_offer_url"></a> [metrics\_offer\_url](#input\_metrics\_offer\_url) | Optional Metrics Offer URL for COS integration | `string` | `null` | no |
| <a name="input_tracing_offer_url"></a> [tracing\_offer\_url](#input\_tracing\_offer\_url) | Optional Tracing Offer URL for COS integration | `string` | `null` | no |
| <a name="input_logging_offer_url"></a> [logging\_offer\_url](#input\_logging\_offer\_url) | Optional Logging Offer URL for COS integration | `string` | `null` | no |
| <a name="input_grafana_dashboard_offer_url"></a> [grafana\_dashboard\_offer\_url](#input\_grafana\_dashboard\_offer\_url) | Optional Grafana Dashboard Offer URL for COS integration | `string` | `null` | no |
---
## Outputs

| Name | Description |
|------|-------------|
| <a name="output_authentik_server_app_name"></a> [authentik\_server\_app\_name](#output\_authentik\_server\_app\_name) | The name of the deployed Authentik Server application |
| <a name="output_authentik_worker_app_name"></a> [authentik\_worker\_app\_name](#output\_authentik\_worker\_app\_name) | The name of the deployed Authentik Worker application |
| <a name="output_authentik_ldap_outpost_app_name"></a> [authentik\_ldap\_outpost\_app\_name](#output\_authentik\_ldap\_outpost\_app\_name) | The name of the deployed Authentik LDAP Outpost application |
