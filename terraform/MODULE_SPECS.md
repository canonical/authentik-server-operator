<!-- BEGIN_TF_DOCS -->

---
## Providers

| Name | Version |
|------|---------|
| <a name="provider_juju"></a> [juju](#provider\_juju) | ~> 2.0 |
---
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.6 |
| <a name="requirement_juju"></a> [juju](#requirement\_juju) | ~> 2.0 |
---
## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_app_name"></a> [app\_name](#input\_app\_name) | Name of the application in the Juju model | `string` | `"authentik-server"` | no |
| <a name="input_base"></a> [base](#input\_base) | Operating system base for the charm (e.g. ubuntu@22.04) | `string` | `null` | no |
| <a name="input_channel"></a> [channel](#input\_channel) | Channel to use when deploying the charm | `string` | `"latest/stable"` | no |
| <a name="input_config"></a> [config](#input\_config) | Map of charm configuration options | `map(string)` | `{}` | no |
| <a name="input_constraints"></a> [constraints](#input\_constraints) | Constraints string for the deployed application | `string` | `null` | no |
| <a name="input_model_uuid"></a> [model\_uuid](#input\_model\_uuid) | UUID of the Juju model to deploy the charm into | `string` | n/a | yes |
| <a name="input_revision"></a> [revision](#input\_revision) | Charm revision to deploy. Null deploys the latest on the given channel | `number` | `null` | no |
| <a name="input_resources"></a> [resources](#input\_resources) | Map of charm resources | `map(string)` | `{}` | no |
| <a name="input_units"></a> [units](#input\_units) | Number of units to deploy | `number` | `1` | no |
---
## Outputs

| Name | Description |
|------|-------------|
| <a name="output_application"></a> [application](#output\_application) | The deployed juju\_application resource |
| <a name="output_provides"></a> [provides](#output\_provides) | Map of provides endpoint names |
| <a name="output_requires"></a> [requires](#output\_requires) | Map of requires endpoint names |
| <a name="output_offers"></a> [offers](#output\_offers) | The Juju offers that the charm provides |
<!-- END_TF_DOCS -->
