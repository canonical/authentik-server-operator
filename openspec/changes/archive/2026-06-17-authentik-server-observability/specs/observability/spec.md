# Observability Stack

## ADDED Requirements

### Requirement: Charm must integrate with Loki via LogForwarder

`charm.py` MUST instantiate `LogForwarder` from `charms.loki_k8s.v1.loki_push_api`
and bind it to the `logging` relation (`LOGGING_RELATION_NAME = "logging"`).
No explicit event wiring is required — `LogForwarder` handles forwarding passively.

#### Scenario: Log forwarding integration completes without error

Given the charm is deployed, when
`juju integrate authentik-server:logging loki-k8s:logging` is run, then the
integration completes without errors and Authentik logs are forwarded to Loki.

### Requirement: Charm must expose Prometheus metrics via MetricsEndpointProvider

`charm.py` MUST instantiate `MetricsEndpointProvider` from
`charms.prometheus_k8s.v0.prometheus_scrape` targeting port `SERVER_PORT` (9000)
on all units (`*:{SERVER_PORT}`). The relation name is
`PROMETHEUS_RELATION_NAME = "metrics-endpoint"`.

Authentik exposes `/-/metrics/` on the main HTTP port.

#### Scenario: Prometheus metrics integration completes without error

Given the charm is deployed, when
`juju integrate authentik-server:metrics-endpoint prometheus-k8s:metrics-endpoint`
is run, then Prometheus can scrape metrics from `/-/metrics/` on port 9000.

### Requirement: Charm must provide Grafana dashboard via GrafanaDashboardProvider

`charm.py` MUST instantiate `GrafanaDashboardProvider` from
`charms.grafana_k8s.v0.grafana_dashboard` bound to
`GRAFANA_RELATION_NAME = "grafana-dashboard"`.
A placeholder dashboard template MUST exist at
`src/grafana_dashboards/authentik-server.json.tmpl`.

#### Scenario: Grafana dashboard integration completes without error

Given `src/grafana_dashboards/authentik-server.json.tmpl` exists and the charm is
deployed, when
`juju integrate authentik-server:grafana-dashboard grafana-k8s:grafana-dashboard`
is run, then the dashboard template is sent to Grafana without errors.

### Requirement: Charm must send traces to Tempo via TracingEndpointRequirer

`charm.py` MUST instantiate `TracingEndpointRequirer` from
`charms.tempo_coordinator_k8s.v0.tracing` with `protocols=["otlp_http"]` and
`TRACING_RELATION_NAME = "tracing"`.

`integrations.py` MUST implement `TracingIntegration` implementing `EnvVarConvertible`:
- `to_env_vars()` MUST return `{}` when the tracing endpoint is not ready.
- `to_env_vars()` MUST return `{"OTEL_EXPORTER_OTLP_ENDPOINT": <endpoint>}` when ready.

`TracingIntegration` MUST be merged into the env var dict in `_reconcile()`.

#### Scenario: Tracing env vars are absent when not integrated

Given no `tracing` relation exists, when `TracingIntegration.to_env_vars()` is called,
then an empty dict `{}` is returned.

#### Scenario: Tracing env vars are set when endpoint is ready

Given a `tracing` relation is established and the endpoint is available, when
`TracingIntegration.to_env_vars()` is called, then
`{"OTEL_EXPORTER_OTLP_ENDPOINT": "<endpoint-url>"}` is returned.

#### Scenario: Tracing integration connects without error

Given the charm is deployed, when
`juju integrate authentik-server:tracing tempo-coordinator-k8s:tracing` is run,
then the integration completes and the OTLP endpoint env var is passed to the workload.

### Requirement: Prometheus and Loki alert rule files must exist

The following alert rule files MUST exist in the charm source:

- `src/prometheus_alert_rules/authentik_server.rule` — fires `AuthentikServerUnavailable`
  when the charm target is down for 5 minutes.
- `src/loki_alert_rules/authentik_server.rule` — fires `AuthentikServerErrors` when
  error-rate log entries are detected.

#### Scenario: Alert rule files are present in the charm

Given the charm is packed with `charmcraft pack`, when the resulting archive is
inspected, then both alert rule files are present at their expected paths.

### Requirement: Observability relation name constants must be defined in src/constants.py

`src/constants.py` MUST export the following constants so that `charm.py` can
reference relation names without string literals:

```python
LOGGING_RELATION_NAME = "logging"
PROMETHEUS_RELATION_NAME = "metrics-endpoint"
GRAFANA_RELATION_NAME = "grafana-dashboard"
TRACING_RELATION_NAME = "tracing"
```

#### Scenario: Constants are importable and match charmcraft.yaml relation names

Given the constants are defined in `src/constants.py`, when each constant is compared
against the corresponding relation name in `charmcraft.yaml`, then all values match.
