## ADDED Requirements

### Requirement: Conftest provides create_state() factory
The `tests/unit/conftest.py` module SHALL provide a module-level `create_state()` factory function (not a fixture) that builds a complete `testing.State` with sensible defaults: `leader=True`, `can_connect=True`, a `WORKLOAD_CONTAINER` container with `ak version` exec mock, and empty relations/secrets/config.

#### Scenario: Minimal state
- **WHEN** `create_state()` is called with no arguments
- **THEN** it returns a `testing.State` with `leader=True`, `can_connect=True`, one container, and empty relations/secrets/config

#### Scenario: Custom state with relations and secrets
- **WHEN** `create_state(relations=[db_relation], secrets=[secret_key_secret], leader=False)` is called
- **THEN** it returns a `testing.State` containing the specified relations, secrets, and `leader=False`

### Requirement: Conftest provides relation fixtures for all charm relations
The `tests/unit/conftest.py` module SHALL provide a `@pytest.fixture` for every relation endpoint declared in `charmcraft.yaml`: `db_relation`, `peer_relation`, `ingress_relation`, `cluster_relation`, `server_info_relation`, `tracing_relation`, `logging_relation`, `metrics_endpoint_relation`, `grafana_dashboard_relation`.

#### Scenario: Database relation fixture
- **WHEN** the `db_relation` fixture is used
- **THEN** it returns a `testing.Relation` with endpoint `pg-database`, interface `postgresql_client`, and remote app data containing `database`, `endpoints`, `username`, and `password`

#### Scenario: Ingress relation fixture
- **WHEN** the `ingress_relation` fixture is used
- **THEN** it returns a `testing.Relation` with endpoint `ingress`, interface `ingress`, and remote app data containing an ingress URL that `IngressPerAppRequirer.url` can read

#### Scenario: Peer relation fixture
- **WHEN** the `peer_relation` fixture is used
- **THEN** it returns a `testing.PeerRelation` with endpoint `authentik-peers` and interface `authentik_peers`, with no secret IDs in local app data (secrets are looked up by label)

### Requirement: Conftest provides condition mock fixtures
The `tests/unit/conftest.py` module SHALL provide `@pytest.fixture` mocks for each condition function and service method used in `_on_collect_status` and `NOOP_CONDITIONS`: `mocked_container_connectivity`, `mocked_database_integration_exists`, `mocked_database_resource_is_created`, `mocked_secrets_is_ready`, `mocked_workload_is_running`, `mocked_workload_is_failing`.

#### Scenario: Condition mocks return satisfied values by default
- **WHEN** any condition mock fixture is activated
- **THEN** `container_connectivity` returns `True`, `database_integration_exists` returns `True`, `database_resource_is_created` returns `True`, `Secrets.is_ready` returns `True`, `WorkloadService.is_running` returns `True`, `WorkloadService.is_failing` returns `False`

### Requirement: Conftest provides all_satisfied_conditions composite fixture
The `tests/unit/conftest.py` module SHALL provide an `all_satisfied_conditions` fixture that activates all condition mock fixtures at once, so tests that want "everything works" don't need to list each mock individually.

#### Scenario: All conditions satisfied
- **WHEN** a test uses the `all_satisfied_conditions` fixture
- **THEN** all condition mocks are activated and the charm's collect-status returns `ActiveStatus`

### Requirement: Conftest provides service mock fixtures
The `tests/unit/conftest.py` module SHALL provide `@pytest.fixture` mocks for `WorkloadService.version` (PropertyMock), `WorkloadService.open_port`, and `AuthentikServerCharm._holistic_handler`.

#### Scenario: Workload version mock
- **WHEN** the `mocked_workload_service_version` fixture is used
- **THEN** `charm.WorkloadService.version` returns a fixed string (e.g. `"1.10.0"`)

### Requirement: test_charm.py covers lifecycle and holistic handler
The `tests/unit/test_charm.py` file SHALL cover pebble-ready, config-changed, the holistic handler (container not connected, all conditions satisfied, non-leader skips secrets, CharmError from _ensure_secrets), and database/ingress/pebble-check events.

#### Scenario: Pebble ready opens ports and sets version
- **WHEN** the `authentik_pebble_ready` event fires with all conditions satisfied
- **THEN** `WorkloadService.open_port` is called, the holistic handler runs, and `WorkloadService.set_version` is called

#### Scenario: Holistic handler exits early when container not connected
- **WHEN** `container_connectivity` returns `False`
- **THEN** the holistic handler returns without planning the pebble layer

#### Scenario: Non-leader skips secret creation
- **WHEN** the holistic handler runs on a non-leader unit
- **THEN** `Secrets.__setitem__` is never called

### Requirement: test_charm.py covers collect-status parametrized
The `tests/unit/test_charm.py` file SHALL use `@pytest.mark.parametrize` to test each `_on_collect_status` condition independently, overriding one condition at a time while `all_satisfied_conditions` keeps the rest satisfied.

#### Scenario: Missing database relation
- **WHEN** `database_integration_exists` returns `False`
- **THEN** collect-status reports `BlockedStatus("missing pg-database relation")`

#### Scenario: Missing authentik-worker relation
- **WHEN** the `authentik-cluster` relation is absent
- **THEN** collect-status reports `BlockedStatus("missing authentik-worker relation")`

#### Scenario: All conditions satisfied
- **WHEN** all conditions are satisfied
- **THEN** collect-status reports `ActiveStatus`

### Requirement: test_integrations.py covers DatabaseConfig and TracingData
The `tests/unit/test_integrations.py` file SHALL test `DatabaseConfig.load()`, `DatabaseConfig.to_env_vars()`, `TracingData.load()`, and `TracingData.to_env_vars()` using `create_autospec()` on library requirers.

#### Scenario: DatabaseConfig load with valid relation data
- **WHEN** `DatabaseConfig.load()` is called with a mocked `DatabaseRequires` that has relation data with `endpoints`, `username`, `password`, `database`
- **THEN** it returns a `DatabaseConfig` with parsed `host`, `port`, `user`, `password`, `name`

#### Scenario: TracingData load when not ready
- **WHEN** `TracingData.load()` is called with a mocked `TracingEndpointRequirer` where `is_ready()` returns `False`
- **THEN** it returns `TracingData()` with `is_ready=False` and empty endpoint

### Requirement: test_configs.py covers CharmConfig
The `tests/unit/test_configs.py` file SHALL test `CharmConfig.to_env_vars()` with full config and minimal config, and `CharmConfig.get_missing_config_keys()`.

#### Scenario: Full config produces all env vars
- **WHEN** `CharmConfig` is constructed with all config options set
- **THEN** `to_env_vars()` returns `AUTHENTIK_LOG_LEVEL`, `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`, and `AUTHENTIK_WEB__WORKERS`

#### Scenario: get_missing_config_keys returns empty list
- **WHEN** `get_missing_config_keys()` is called
- **THEN** it returns an empty list

### Requirement: test_secret.py covers Secrets class
The `tests/unit/test_secret.py` file SHALL test the `Secrets` class using `create_autospec(Model)`, covering `__getitem__`, `__setitem__`, `is_ready`, `to_env_vars`, and the three properties (`secret_key`, `bootstrap_token`, `bootstrap_password`) including the `SecretError` path when secrets are not available.

#### Scenario: Get secret by label
- **WHEN** `Secrets[label]` is called and the secret exists
- **THEN** it returns the secret content dict

#### Scenario: Get secret when not found
- **WHEN** `Secrets[label]` is called and the secret does not exist
- **THEN** it returns `None`

#### Scenario: Set secret creates app secret
- **WHEN** `Secrets[label] = content` is called
- **THEN** `model.app.add_secret(content, label=label)` is called

#### Scenario: Property raises SecretError when not available
- **WHEN** `Secrets.secret_key` is accessed and the secret does not exist
- **THEN** it raises `SecretError`

### Requirement: Broken library test files are deleted
The `tests/unit/test_authentik_cluster.py` and `tests/unit/test_authentik_server_info.py` files SHALL be deleted, and `tests/unit/test_tracing_integration.py` SHALL be deleted (merged into `test_integrations.py`).

#### Scenario: No broken test files remain
- **WHEN** the test suite is collected
- **THEN** `test_authentik_cluster.py`, `test_authentik_server_info.py`, and `test_tracing_integration.py` do not exist
