# Terraform Modules for Charmed Authentik

This directory contains Terraform modules to easily deploy, configure, and manage Charmed Authentik and its dependencies on Kubernetes using Juju.

---

## Module Directory Structure

Our Terraform integrations are designed in three distinct layers to support everything from simple charm provisioning to complete production-ready stack deployments:

1. **[Core Module](./)** (this folder):
   Deploys only the core `authentik-server` application itself into an existing Juju model.
2. **[Solution Module](./solution/)**:
   A composite solution module that deploys the entire Authentik suite (`authentik-server`, `authentik-worker`, and `authentik-ldap-outpost`) and integrates them via cross-model Juju Offers with database, routing, and observability dependencies.
3. **[Tutorial / Example Scenario](./solution/examples/tutorial/)**:
   A complete, runnable scenario demonstrating how to provision the entire stack from scratch—including models, PostgreSQL, Traefik, certificates, and the Authentik solution suite—using a single `terraform apply`.

---

## Tutorial: Deploy the Full Authentik Stack (Single Command)

The quickest way to get a full, production-ready Authentik stack running is by executing our pre-configured tutorial/example deployment.

### Prerequisites
- [Terraform](https://www.terraform.io/downloads) >= 1.6
- [MicroK8s](https://microk8s.io/) or any Kubernetes cluster configured with Juju
- [Juju Controller](https://juju.is/) bootstrapped and active

### Step-by-Step Guide

1. **Navigate to the Tutorial Directory**:
   ```bash
   cd terraform/solution/examples/tutorial
   ```

2. **Initialize Terraform**:
   Initialize and download the required Juju provider and child modules:
   ```bash
   terraform init
   ```

3. **Deploy the Stack**:
   Execute the deployment. This will automatically:
   * Create a `core` Juju model.
   * Deploy PostgreSQL, Traefik Route, and self-signed SSL certificate managers.
   * Create an `authentik` Juju model.
   * Deploy and provision the complete Authentik solution suite (`authentik-server`, `authentik-worker`, and `authentik-ldap-outpost`).
   * Create Juju Offers and establish cross-model relations to stitch the components together.

   ```bash
   terraform apply -auto-approve
   ```

4. **Monitor the Progress**:
   You can monitor the Juju status of the newly created models:
   ```bash
   juju status -m core --watch
   juju status -m authentik --watch
   ```

---

## Solution Module Configuration (`terraform/solution`)

To consume the `solution` module directly within your own existing infrastructure code, declare it like this:

```hcl
module "authentik_stack" {
  source = "github.com/canonical/authentik-server-operator//terraform/solution"

  model                   = var.my_model_uuid
  postgresql_offer_url    = "admin/core.postgresql-k8s"
  traefik_route_offer_url = "admin/core.traefik-public"

  # Optional Observability Integrations
  metrics_offer_url           = "admin/cos.prometheus"
  logging_offer_url           = "admin/cos.loki"
  grafana_dashboard_offer_url = "admin/cos.grafana"
}
```

### Core Inputs

| Name | Description | Type | Required |
|------|-------------|------|:--------:|
| `model` | UUID of the Juju model to deploy the Authentik suite into | `string` | **Yes** |
| `postgresql_offer_url` | Offer URL of the PostgreSQL database application | `string` | **Yes** |
| `traefik_route_offer_url` | Offer URL of the Traefik Route ingress controller | `string` | **Yes** |
| `metrics_offer_url` | Offer URL of the Prometheus scrape metrics endpoint | `string` | No |
| `logging_offer_url` | Offer URL of the Loki logging endpoint | `string` | No |
| `grafana_dashboard_offer_url` | Offer URL of the Grafana dashboard import endpoint | `string` | No |

---

## Core Module Configuration (`terraform`)

To deploy only the `authentik-server` application itself without the worker or outposts, declare it like this:

```hcl
module "authentik_server" {
  source = "github.com/canonical/authentik-server-operator//terraform"

  model_uuid = var.model_uuid
  app_name   = "authentik-server"
  channel    = "latest/stable"
  units      = 1
}
```

For a full list of configuration options, variables, and schema attributes, refer to the generated specifications:
* [Core Module Specs](./MODULE_SPECS.md)
* [Solution Module Specs](./solution/MODULE_SPECS.md)
* [Tutorial Specs](./solution/examples/tutorial/MODULE_SPECS.md)
