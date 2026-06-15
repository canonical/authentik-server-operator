# Observability Stack

## Integrations

### 1. Log Forwarding (Loki)

```python
from charms.loki_k8s.v1.loki_push_api import LogForwarder

self._log_forwarder = LogForwarder(self, relation_name=LOGGING_RELATION_NAME)
```

Passive — no further wiring required. `LOGGING_RELATION_NAME = "logging"`.

### 2. Metrics (Prometheus)

```python
from charms.prometheus_k8s.v0.prometheus_scrape import MetricsEndpointProvider

self._metrics_endpoint = MetricsEndpointProvider(
    self,
    jobs=[{"static_configs": [{"targets": [f"*:{SERVER_PORT}"]}]}],
    relation_name=PROMETHEUS_RELATION_NAME,
)
```

Authentik exposes `/-/metrics/` on the main HTTP port (9000). `PROMETHEUS_RELATION_NAME = "metrics-endpoint"`.

### 3. Grafana Dashboard

```python
from charms.grafana_k8s.v0.grafana_dashboard import GrafanaDashboardProvider

self._grafana_dashboard = GrafanaDashboardProvider(self, relation_name=GRAFANA_RELATION_NAME)
```

Requires `src/grafana_dashboards/authentik-server.json.tmpl` to exist. Placeholder content is acceptable. `GRAFANA_RELATION_NAME = "grafana-dashboard"`.

### 4. Tracing (Tempo)

```python
from charms.tempo_coordinator_k8s.v0.tracing import TracingEndpointRequirer

self._tracing = TracingEndpointRequirer(
    self, relation_name=TRACING_RELATION_NAME, protocols=["otlp_http"]
)
```

`TRACING_RELATION_NAME = "tracing"`. Env vars are passed via `TracingIntegration` (see below).

### 5. Kubernetes Resource Patch

```python
from charms.observability_libs.v0.kubernetes_compute_resources_patch import (
    K8sResourcePatchFailedEvent,
    KubernetesComputeResourcesPatch,
    ResourceRequirements,
)

self._resource_patch = KubernetesComputeResourcesPatch(
    self, CONTAINER_NAME, resource_reqs_func=self._resource_reqs
)
self.framework.observe(self._resource_patch.on.patch_failed, self._on_resource_patch_failed)
```

`_resource_reqs()` reads `self.config["cpu"]` and `self.config["memory"]` and returns a `ResourceRequirements`. `_on_resource_patch_failed()` logs a warning (following hydra pattern).

## TracingIntegration in `integrations.py`

```python
class TracingIntegration:
    """Wraps TracingEndpointRequirer to implement EnvVarConvertible."""

    def __init__(self, tracing: TracingEndpointRequirer) -> None:
        self._tracing = tracing

    @property
    def is_ready(self) -> bool:
        return self._tracing.is_ready()

    def to_env_vars(self) -> EnvVars:
        if not self.is_ready:
            return {}
        endpoint = self._tracing.get_endpoint("otlp_http")
        if not endpoint:
            return {}
        return {"OTEL_EXPORTER_OTLP_ENDPOINT": endpoint}
```

Instantiated in `charm.__init__` as `self._tracing_integration = TracingIntegration(self._tracing)`. Merged into the env var dict in `_reconcile()`.

## Resource Files

### `src/grafana_dashboards/authentik-server.json.tmpl`

Minimal valid Grafana dashboard JSON. Full content is a follow-up task.

```json
{
  "title": "Authentik Server",
  "uid": "authentik-server",
  "panels": [],
  "schemaVersion": 36,
  "version": 1
}
```

### `src/prometheus_alert_rules/authentik_server.rule`

```yaml
groups:
- name: authentik_server
  rules:
  - alert: AuthentikServerUnavailable
    expr: up{juju_charm="authentik-server-operator"} == 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Authentik server is unavailable"
```

### `src/loki_alert_rules/authentik_server.rule`

```yaml
groups:
- name: authentik_server_logs
  rules:
  - alert: AuthentikServerErrors
    expr: |
      sum(rate({juju_charm="authentik-server-operator"} |= "ERROR" [5m])) > 0
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Authentik server is emitting errors"
```

## Constants

Add to `src/constants.py`:
```python
LOGGING_RELATION_NAME = "logging"
PROMETHEUS_RELATION_NAME = "metrics-endpoint"
GRAFANA_RELATION_NAME = "grafana-dashboard"
TRACING_RELATION_NAME = "tracing"
```

## Lib Fetch Commands

```bash
charmcraft fetch-lib charms.loki_k8s.v1.loki_push_api
charmcraft fetch-lib charms.prometheus_k8s.v0.prometheus_scrape
charmcraft fetch-lib charms.grafana_k8s.v0.grafana_dashboard
charmcraft fetch-lib charms.tempo_coordinator_k8s.v0.tracing
charmcraft fetch-lib charms.observability_libs.v0.kubernetes_compute_resources_patch
```

## Acceptance Criteria

- `juju integrate authentik-server:logging loki-k8s:logging` works
- `juju integrate authentik-server:metrics-endpoint prometheus-k8s:metrics-endpoint` works
- `juju integrate authentik-server:grafana-dashboard grafana-k8s:grafana-dashboard` works
- `juju integrate authentik-server:tracing tempo-coordinator-k8s:tracing` works
- `TracingIntegration.to_env_vars()` returns `{}` when not ready; correct dict when ready
- `tox -e lint unit` passes
