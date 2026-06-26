## Why

The `authentik-server-operator` `charmcraft.yaml` declares four observability relations (`logging`, `metrics-endpoint`, `grafana-dashboard`, `tracing`) but zero code exists to handle them. The charm also has `cpu` and `memory` config options with no Kubernetes resource patching wired. This is a production gap: operators cannot forward logs, scrape metrics, view dashboards, or collect traces from Authentik.

The Canonical Identity Platform pattern (as seen in `hydra-operator` and `tenant-service-operator`) provides a well-established set of libraries and integration points for exactly this use case.

## What Changes

- Add `LogForwarder` (Loki log forwarding — passive, no reconcile logic)
- Add `MetricsEndpointProvider` (Prometheus scrape job targeting `/-/metrics/` on `SERVER_PORT`)
- Add `GrafanaDashboardProvider` + placeholder dashboard template at `src/grafana_dashboards/authentik-server.json.tmpl`
- Add `TracingEndpointRequirer` + `TracingIntegration(EnvVarConvertible)` in `integrations.py`
- Add `KubernetesComputeResourcesPatch` wired to `cpu`/`memory` config options
- Add placeholder alert rules in `src/prometheus_alert_rules/` and `src/loki_alert_rules/`
- Fetch all required charm libs (`loki_k8s`, `grafana_k8s`, `prometheus_k8s`, `tempo_coordinator_k8s`, `observability_libs`)

## Capabilities

### New Capabilities

- `observability`: Loki log forwarding, Prometheus metrics scraping at `/-/metrics/`, Grafana dashboard, Tempo OTLP HTTP tracing, Kubernetes CPU/memory resource patching

## Non-goals

- Real Grafana dashboard content (placeholder template only; full dashboard is a follow-up)
- Real alert rule content (placeholder rules only)
- Worker or LDAP outpost observability (separate repos)

## Impact

- `src/charm.py` — 5 new initialisers in `__init__`, `_resource_reqs()`, `_on_resource_patch_failed()`
- `src/integrations.py` — add `TracingIntegration`
- `src/constants.py` — 4 new relation name constants
- `src/grafana_dashboards/authentik-server.json.tmpl` — new placeholder file
- `src/prometheus_alert_rules/authentik_server.rule` — new placeholder alert
- `src/loki_alert_rules/authentik_server.rule` — new placeholder alert
- `lib/charms/` — new fetched libs (loki, grafana, prometheus, tempo, observability_libs)
- `tests/unit/` — new tests for `TracingIntegration`

## Dependencies

Requires `authentik-server-charmcraft-and-secrets` to be merged first (correct relation names in `charmcraft.yaml`).
