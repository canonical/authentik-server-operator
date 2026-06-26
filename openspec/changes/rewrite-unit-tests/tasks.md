## 1. Conftest rewrite

- [x] 1.1 Rewrite `tests/unit/conftest.py` — keep existing `create_state()` factory (with `ak version` exec mock), `context` fixture, `mocked_k8s_resource_patch` autouse fixtures, and existing secret/relation fixtures
- [x] 1.2 Add missing relation fixtures to `tests/unit/conftest.py`: `ingress_relation` (with `ingress.url` JSON in remote app data), `cluster_relation`, `server_info_relation`
- [x] 1.3 Add condition mock fixtures to `tests/unit/conftest.py`: `mocked_container_connectivity`, `mocked_database_integration_exists`, `mocked_database_resource_is_created`, `mocked_secrets_is_ready`, `mocked_workload_is_running`, `mocked_workload_is_failing`
- [x] 1.4 Add `all_satisfied_conditions` composite fixture to `tests/unit/conftest.py` that activates all condition mocks at once
- [x] 1.5 Add service mock fixtures to `tests/unit/conftest.py`: `mocked_workload_service_version` (PropertyMock), `mocked_open_port`, `mocked_holistic_handler`
- [x] 1.6 Simplify `peer_relation` fixture — remove secret ID references from local app data (secrets are now looked up by label)

## 2. test_charm.py rewrite

- [x] 2.1 Rewrite `tests/unit/test_charm.py` — `TestPebbleReadyEvent` class: test that `open_port` is called, holistic handler runs, `set_version` is called
- [x] 2.2 Add `TestConfigChangedEvent` class: test that holistic handler is called
- [x] 2.3 Add `TestHolisticHandler` class: container not connected (early exit), all conditions satisfied (ActiveStatus), non-leader skips secret creation, CharmError from `_ensure_secrets` sets `can_plan=False`
- [x] 2.4 Add `TestCollectStatusEvent` class with `@pytest.mark.parametrize` for each condition: waiting for pebble, missing pg-database, waiting for database creation, waiting for secrets, missing authentik-worker, service failing, service not running, all satisfied → ActiveStatus
- [x] 2.5 Add `TestDatabaseEvents` class: database_created and endpoints_changed trigger holistic handler; relation_broken stops workload
- [x] 2.6 Add `TestIngressEvents` class: ingress ready and revoked trigger holistic handler
- [x] 2.7 Add `TestPebbleCheckEvents` class: check_failed and check_recovered with `PEBBLE_READY_CHECK_NAME` filter

## 3. test_integrations.py (new, consolidated)

- [ ] 3.1 Create `tests/unit/test_integrations.py` with `TestDatabaseConfig` class: `test_load` (valid relation data), `test_load_empty` (no relations), `test_load_no_endpoints`, `test_to_env_vars` — using `create_autospec(DatabaseRequires)`
- [ ] 3.2 Add `TestTracingData` class to `tests/unit/test_integrations.py`: `test_load` (ready), `test_load_not_ready`, `test_to_env_vars_ready`, `test_to_env_vars_not_ready` — using `create_autospec(TracingEndpointRequirer)`

## 4. test_configs.py (new)

- [ ] 4.1 Create `tests/unit/test_configs.py` with `TestCharmConfig` class: `test_to_env_vars` (full config), `test_to_env_vars_defaults` (minimal config), `test_get_missing_config_keys`

## 5. test_secret.py (new)

- [ ] 5.1 Create `tests/unit/test_secret.py` with `TestSecrets` class using `create_autospec(Model)`: `test_getitem_exists`, `test_getitem_not_found`, `test_getitem_invalid_label`, `test_setitem`, `test_setitem_invalid_label`
- [ ] 5.2 Add to `TestSecrets`: `test_is_ready_true`, `test_is_ready_false`, `test_to_env_vars`
- [ ] 5.3 Add to `TestSecrets`: property tests — `test_secret_key_property`, `test_secret_key_not_available` (raises `SecretError`), `test_bootstrap_token_property`, `test_bootstrap_token_not_available`, `test_bootstrap_password_property`, `test_bootstrap_password_not_available`

## 6. Cleanup

- [ ] 6.1 Delete `tests/unit/test_tracing_integration.py` (merged into `test_integrations.py`)
- [ ] 6.2 Delete `tests/unit/test_authentik_cluster.py` (broken library test)
- [ ] 6.3 Delete `tests/unit/test_authentik_server_info.py` (broken library test)

## 7. Validation

- [ ] 7.1 Run `tox -e fmt` and fix any formatting issues
- [ ] 7.2 Run `tox -e lint` and fix any linting errors
- [ ] 7.3 Run `tox -e unit` and verify all tests pass
