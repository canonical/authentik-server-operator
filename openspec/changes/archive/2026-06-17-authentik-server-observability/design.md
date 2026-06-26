## Context

Four observability relations are declared in `charmcraft.yaml` but no code handles them. The reference implementations are `hydra-operator/src/charm.py` and `tenant-service-operator/src/charm.py`, both of which wire the same five integrations.

## Goals

- All four observability relations are functional
- `cpu` and `memory` config options take effect via Kubernetes resource patching
- `TracingIntegration` follows the `EnvVarConvertible` protocol so tracing env vars flow naturally into the existing `_reconcile()` env var merge

## Decisions

### D1: All five integrations initialised in `charm.__init__` only

`LogForwarder`, `MetricsEndpointProvider`, `GrafanaDashboardProvider`, and `TracingEndpointRequirer` are self-contained — they handle their own relation events internally. Only `KubernetesComputeResourcesPatch` requires an additional event observer (`on.patch_failed`). No `_reconcile()` changes needed for the passive integrations.

### D2: Tracing env vars flow via `TracingIntegration(EnvVarConvertible)`

```python
class TracingIntegration:
    def __init__(self, tracing: TracingEndpointRequirer) -> None: ...
    @property
    def is_ready(self) -> bool: ...
    def to_env_vars(self) -> EnvVars:
        if not self.is_ready:
            return {}
        endpoint = self._tracing.get_endpoint("otlp_http")
        return {"OTEL_EXPORTER_OTLP_ENDPOINT": endpoint} if endpoint else {}
```

This keeps `_reconcile()` consistent — it merges env vars from all `EnvVarConvertible` sources without knowing about tracing specifically.

### D3: Metrics scrape job targets `SERVER_PORT` (`:9000`)

Authentik exposes Prometheus metrics at `/-/metrics/` on the main HTTP port. No separate metrics port is needed.

### D4: Placeholder dashboard template — real content is follow-up

A minimal valid JSON template satisfies `GrafanaDashboardProvider` without committing to specific panel content before understanding Authentik's metric names. Full dashboard is tracked as a manual follow-up task.

### D5: Placeholder alert rules — follow hydra pattern

One `AuthentikServerUnavailable` alert for Prometheus and one log-based alert for Loki. Content is placeholder. Following hydra's file naming convention.

### D6: Fetch libs via `charmcraft fetch-lib`

Required new libs: `charms.loki_k8s.v1.loki_push_api`, `charms.prometheus_k8s.v0.prometheus_scrape`, `charms.grafana_k8s.v0.grafana_dashboard`, `charms.tempo_coordinator_k8s.v0.tracing`, `charms.observability_libs.v0.kubernetes_compute_resources_patch`. Fetch commands are explicit tasks.
