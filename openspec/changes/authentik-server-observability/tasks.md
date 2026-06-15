## 1. Fetch missing charm libs

- [ ] 1.1 `charmcraft fetch-lib charms.loki_k8s.v1.loki_push_api`
- [ ] 1.2 `charmcraft fetch-lib charms.prometheus_k8s.v0.prometheus_scrape`
- [ ] 1.3 `charmcraft fetch-lib charms.grafana_k8s.v0.grafana_dashboard`
- [ ] 1.4 `charmcraft fetch-lib charms.tempo_coordinator_k8s.v0.tracing`
- [ ] 1.5 `charmcraft fetch-lib charms.observability_libs.v0.kubernetes_compute_resources_patch`

## 2. Add observability constants to `src/constants.py`

- [ ] 2.1 Add `LOGGING_RELATION_NAME = "logging"`
- [ ] 2.2 Add `PROMETHEUS_RELATION_NAME = "metrics-endpoint"`
- [ ] 2.3 Add `GRAFANA_RELATION_NAME = "grafana-dashboard"`
- [ ] 2.4 Add `TRACING_RELATION_NAME = "tracing"`

## 3. Add `TracingIntegration` to `src/integrations.py`

- [ ] 3.1 Add `TracingIntegration` class implementing `EnvVarConvertible` with `is_ready` property and `to_env_vars()` method
- [ ] 3.2 `to_env_vars()` returns `{"OTEL_EXPORTER_OTLP_ENDPOINT": endpoint}` when ready, `{}` otherwise

## 4. Wire observability in `src/charm.py`

- [ ] 4.1 Add `LogForwarder(self, relation_name=LOGGING_RELATION_NAME)` in `__init__`
- [ ] 4.2 Add `MetricsEndpointProvider(self, jobs=[...], relation_name=PROMETHEUS_RELATION_NAME)` with scrape job for `SERVER_PORT`
- [ ] 4.3 Add `GrafanaDashboardProvider(self, relation_name=GRAFANA_RELATION_NAME)` in `__init__`
- [ ] 4.4 Add `TracingEndpointRequirer(self, relation_name=TRACING_RELATION_NAME, protocols=["otlp_http"])` in `__init__`
- [ ] 4.5 Add `TracingIntegration(self._tracing)` in `__init__`; merge `to_env_vars()` into `_reconcile()` env dict
- [ ] 4.6 Add `KubernetesComputeResourcesPatch(self, CONTAINER_NAME, resource_reqs_func=self._resource_reqs)` in `__init__`
- [ ] 4.7 Add `_resource_reqs()` method: reads `cpu` and `memory` config, returns `ResourceRequirements`
- [ ] 4.8 Add `framework.observe(self._resource_patch.on.patch_failed, self._on_resource_patch_failed)` and implement `_on_resource_patch_failed()` (log warning)

## 5. Create observability resource files

- [ ] 5.1 Create `src/grafana_dashboards/authentik-server.json.tmpl` with minimal placeholder JSON dashboard
- [ ] 5.2 Create `src/prometheus_alert_rules/authentik_server.rule` with `AuthentikServerUnavailable` placeholder alert
- [ ] 5.3 Create `src/loki_alert_rules/authentik_server.rule` with `AuthentikServerErrors` placeholder alert

## 6. Unit tests

- [ ] 6.1 Test: `TracingIntegration.to_env_vars()` returns `{}` when tracing not ready
- [ ] 6.2 Test: `TracingIntegration.to_env_vars()` returns correct dict when tracing is ready
- [ ] 6.3 Run `tox -e unit` — all tests pass

## 7. Lint, format, and build

- [ ] 7.1 Run `tox -e fmt`
- [ ] 7.2 Run `tox -e lint` — no errors
- [ ] 7.3 Run `charmcraft pack` — charm builds successfully

## 8. Manual follow-up

- [ ] 8.1 Replace placeholder `authentik-server.json.tmpl` with a real Grafana dashboard once Authentik metric names are known
