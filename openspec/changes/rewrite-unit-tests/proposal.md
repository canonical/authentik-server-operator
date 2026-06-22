## Why

The unit test suite is stale and broken. Two test files (`test_authentik_cluster.py`, `test_authentik_server_info.py`) fail to import because they reference private library names that no longer exist. The remaining tests (`test_charm.py`, `test_tracing_integration.py`) target the pre-refactor API (old `SecretsIntegration`, `DatabaseIntegration`, `_reconcile`) and don't cover the refactored `Secrets` class, `WorkloadService`, `DatabaseConfig`/`TracingData` dataclasses, the holistic handler, or the expanded `_on_collect_status` conditions. The `tenant-service-operator` charm has a mature, well-structured test suite that this charm should mirror.

## What Changes

- **Rewrite `tests/unit/conftest.py`**: Add all relation fixtures (ingress, cluster, server-info), condition mock fixtures (`container_connectivity`, `database_integration_exists`, `database_resource_is_created`, `secrets_is_ready`, `workload_is_running`, `workload_is_failing`), the `all_satisfied_conditions` composite fixture, and service mocks (`mocked_workload_service_version`, `mocked_open_port`, `mocked_holistic_handler`).
- **Rewrite `tests/unit/test_charm.py`**: Cover pebble-ready, config-changed, holistic handler (container not connected, all satisfied, non-leader, CharmError), collect-status (parametrized per condition), database events, ingress events, pebble-check events, and database-relation-broken.
- **Create `tests/unit/test_integrations.py`**: Consolidate `DatabaseConfig` and `TracingData` tests using `create_autospec()` on library requirers (matching tenant-service pattern).
- **Create `tests/unit/test_configs.py`**: Test `CharmConfig.to_env_vars()` (full config, defaults) and `get_missing_config_keys()`.
- **Create `tests/unit/test_secret.py`**: Test `Secrets` class using `create_autospec(Model)` — `__getitem__`, `__setitem__`, `is_ready`, `to_env_vars`, and the three properties (including `SecretError` when not available).
- **Delete `tests/unit/test_tracing_integration.py`**: Merged into `test_integrations.py`.
- **Delete `tests/unit/test_authentik_cluster.py` and `tests/unit/test_authentik_server_info.py`**: Library tests belong with the library, not the charm. They are broken and test private internals.

## Capabilities

### New Capabilities
- `unit-test-suite`: Comprehensive unit test coverage for the authentik-server charm, mirroring tenant-service-operator patterns — conftest fixtures, `create_state()` factory, condition mocks, and one-file-per-concern test organization.

### Modified Capabilities
<!-- No existing spec-level behavior changes. -->

## Impact

- **Affected files**: `tests/unit/conftest.py` (rewrite), `tests/unit/test_charm.py` (rewrite), `tests/unit/test_integrations.py` (new), `tests/unit/test_configs.py` (new), `tests/unit/test_secret.py` (new), `tests/unit/test_tracing_integration.py` (delete), `tests/unit/test_authentik_cluster.py` (delete), `tests/unit/test_authentik_server_info.py` (delete).
- **No source code changes**: All tests target the existing refactored `src/` API. No `src/` files are modified.
- **Dependencies**: No new dependencies. Uses existing `ops[testing]`, `pytest`, `pytest-mock`.

## Non-goals

- Fixing or modifying source code in `src/` — tests must work against the current API.
- Integration tests (`tests/integration/`) — out of scope.
- Library tests for `lib/charms/authentik_server/` — these belong in the library's own test suite.
- Testing the `KubernetesComputeResourcesPatch` library itself — only mocked via autouse fixture.
