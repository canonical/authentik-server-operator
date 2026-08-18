# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

# Local cluster integration between authentik-server and authentik-worker
resource "juju_integration" "authentik_cluster" {
  application {
    name     = module.authentik_server.application.name
    endpoint = "authentik-cluster"
  }

  application {
    name     = module.authentik_worker.application.name
    endpoint = "authentik-cluster"
  }

  model_uuid = data.juju_model.this.uuid
}

# Local integration between authentik-server and authentik-ldap-outpost
resource "juju_integration" "ldap_server_info" {
  application {
    name     = module.authentik_server.application.name
    endpoint = "authentik-server-info"
  }

  application {
    name     = module.authentik_ldap_outpost.application.name
    endpoint = "authentik-server-info"
  }

  model_uuid = data.juju_model.this.uuid
}

# Database cross-model integration
resource "juju_integration" "database" {
  application {
    offer_url = data.juju_offer.database.url
  }

  application {
    name     = module.authentik_server.application.name
    endpoint = "pg-database"
  }

  model_uuid = data.juju_model.this.uuid
}

# Ingress Route cross-model integration
resource "juju_integration" "ingress_route" {
  application {
    offer_url = data.juju_offer.traefik_route.url
  }

  application {
    name     = module.authentik_server.application.name
    endpoint = "traefik-route"
  }

  model_uuid = data.juju_model.this.uuid
}

# Ingress Route cross-model integration for LDAP Outpost
resource "juju_integration" "ingress_route_ldap" {
  application {
    offer_url = data.juju_offer.traefik_route.url
  }

  application {
    name     = module.authentik_ldap_outpost.application.name
    endpoint = "traefik-route"
  }

  model_uuid = data.juju_model.this.uuid
}


# Optional COS (observability) integrations for Server
resource "juju_integration" "metrics" {
  count = var.metrics_offer_url != null ? 1 : 0

  application {
    offer_url = data.juju_offer.metrics[0].url
  }

  application {
    name     = module.authentik_server.application.name
    endpoint = "metrics-endpoint"
  }

  model_uuid = data.juju_model.this.uuid
}

resource "juju_integration" "tracing" {
  count = var.tracing_offer_url != null ? 1 : 0

  application {
    offer_url = data.juju_offer.tracing[0].url
  }

  application {
    name     = module.authentik_server.application.name
    endpoint = "tracing"
  }

  model_uuid = data.juju_model.this.uuid
}

resource "juju_integration" "logging" {
  count = var.logging_offer_url != null ? 1 : 0

  application {
    offer_url = data.juju_offer.logging[0].url
  }

  application {
    name     = module.authentik_server.application.name
    endpoint = "logging"
  }

  model_uuid = data.juju_model.this.uuid
}

resource "juju_integration" "grafana_dashboard" {
  count = var.grafana_dashboard_offer_url != null ? 1 : 0

  application {
    offer_url = data.juju_offer.grafana_dashboard[0].url
  }

  application {
    name     = module.authentik_server.application.name
    endpoint = "grafana-dashboard"
  }

  model_uuid = data.juju_model.this.uuid
}

# Optional COS (observability) integrations for Worker
resource "juju_integration" "metrics_worker" {
  count = var.metrics_offer_url != null ? 1 : 0

  application {
    offer_url = data.juju_offer.metrics[0].url
  }

  application {
    name     = module.authentik_worker.application.name
    endpoint = "metrics-endpoint"
  }

  model_uuid = data.juju_model.this.uuid
}

resource "juju_integration" "tracing_worker" {
  count = var.tracing_offer_url != null ? 1 : 0

  application {
    offer_url = data.juju_offer.tracing[0].url
  }

  application {
    name     = module.authentik_worker.application.name
    endpoint = "tracing"
  }

  model_uuid = data.juju_model.this.uuid
}

resource "juju_integration" "logging_worker" {
  count = var.logging_offer_url != null ? 1 : 0

  application {
    offer_url = data.juju_offer.logging[0].url
  }

  application {
    name     = module.authentik_worker.application.name
    endpoint = "logging"
  }

  model_uuid = data.juju_model.this.uuid
}

resource "juju_integration" "grafana_dashboard_worker" {
  count = var.grafana_dashboard_offer_url != null ? 1 : 0

  application {
    offer_url = data.juju_offer.grafana_dashboard[0].url
  }

  application {
    name     = module.authentik_worker.application.name
    endpoint = "grafana-dashboard"
  }

  model_uuid = data.juju_model.this.uuid
}

# Optional COS (observability) integrations for LDAP Outpost
resource "juju_integration" "metrics_ldap" {
  count = var.metrics_offer_url != null ? 1 : 0

  application {
    offer_url = data.juju_offer.metrics[0].url
  }

  application {
    name     = module.authentik_ldap_outpost.application.name
    endpoint = "metrics-endpoint"
  }

  model_uuid = data.juju_model.this.uuid
}

resource "juju_integration" "tracing_ldap" {
  count = var.tracing_offer_url != null ? 1 : 0

  application {
    offer_url = data.juju_offer.tracing[0].url
  }

  application {
    name     = module.authentik_ldap_outpost.application.name
    endpoint = "tracing"
  }

  model_uuid = data.juju_model.this.uuid
}

resource "juju_integration" "logging_ldap" {
  count = var.logging_offer_url != null ? 1 : 0

  application {
    offer_url = data.juju_offer.logging[0].url
  }

  application {
    name     = module.authentik_ldap_outpost.application.name
    endpoint = "logging"
  }

  model_uuid = data.juju_model.this.uuid
}

resource "juju_integration" "grafana_dashboard_ldap" {
  count = var.grafana_dashboard_offer_url != null ? 1 : 0

  application {
    offer_url = data.juju_offer.grafana_dashboard[0].url
  }

  application {
    name     = module.authentik_ldap_outpost.application.name
    endpoint = "grafana-dashboard"
  }

  model_uuid = data.juju_model.this.uuid
}
