## Context

The authentik-server-operator charm was recently refactored to align with the tenant-service-operator's structural patterns. The source code now uses:
- `Secrets` class (in `secret.py`) instead of `SecretsIntegration`
- `DatabaseConfig` / `TracingData` frozen dataclasses with `load()` classmethods instead of `DatabaseIntegration` / `TracingIntegration` wrapper classes
- `WorkloadService` class with `is_running()` / `is_failing()` / `set_version()` / `open_port()`
- `_on_holistic_handler` / `_holistic_handler` instead of `_on_event` / `_reconcile`
- `NOOP_CONDITIONS` tuple in `utils.py` gating the holistic handler
- `_on_collect_status` with no early returns (all `add_status` calls are unconditional)
- `KubernetesComputeResourcesPatch` (requires autouse mock in tests)

The existing unit tests target the pre-refactor API and are broken. The tenant-service-operator has a mature test suite that serves as the reference implementation.

## Goals / Non-Goals

**Goals:**
- Mirror tenant-service-operator's test structure: one file per concern, `create_state()` factory, `all_satisfied_conditions` composite fixture, condition mock fixtures, relation fixtures for every relation.
- Cover all refactored source modules: `charm.py`, `secret.py`, `integrations.py`, `configs.py`, `services.py` (via charm-level tests).
- Use `ops.testing` (Scenario) for charm lifecycle tests and `create_autospec()` for integration/config/secret wrapper tests.
- All tests pass against the current refactored `src/` API without modifying source code.

**Non-Goals:**
- Modifying `src/` files.
- Integration tests.
- Library tests for `lib/charms/authentik_server/`.
- Testing `KubernetesComputeResourcesPatch` internals (only mocked).

## Decisions

### D1: `create_state()` factory — keep module-level function, not a fixture

**Rationale**: Matches tenant-service exactly. Test files import it directly (`from conftest import create_state`). Avoids fixture parameterization complexity. The factory already exists and works; we extend it with `workload_version` support if needed.

**Alternative considered**: A fixture with `params` — rejected because tenant-service uses the function pattern and we want maximum copy-paste alignment.

### D2: `all_satisfied_conditions` composite fixture — mirror tenant-service

**Rationale**: Tests that just want "everything works" shouldn't list 6+ mock fixtures individually. The composite fixture activates all condition mocks at once. For collect-status parametrized tests, individual conditions are overridden with `patch()` in the test body (same as tenant-service).

**Conditions to mock** (matching `NOOP_CONDITIONS` + collect-status checks):
- `container_connectivity` → `True`
- `database_integration_exists` → `True`
- `database_resource_is_created` → `True`
- `Secrets.is_ready` → `True`
- `WorkloadService.is_running` → `True`
- `WorkloadService.is_failing` → `False`

### D3: `WorkloadService.is_running` / `is_failing` — mock at `charm.WorkloadService` level

**Rationale**: `testing.Container` does not expose `get_service()` / `get_checks()` directly — these are methods on the real `ops.model.Container` that Scenario instantiates during `context.run()`. Setting up `service_statuses` and `check_infos` on `testing.Container` is fragile and requires the pebble layer to be applied first. Tenant-service patches `WorkloadService.is_running` and `WorkloadService.is_failing` directly via `mocker.patch("charm.WorkloadService.is_running", return_value=True)`. We follow the same approach.

**Alternative considered**: Setting `service_statuses={WORKLOAD_SERVICE: ServiceStatus.ACTIVE}` and `check_infos=[testing.CheckInfo(PEBBLE_READY_CHECK_NAME, status=CheckStatus.UP)]` on `testing.Container` — rejected because it requires the layer to be planned first and is more brittle.

### D4: `Secrets` tests — use `create_autospec(Model)`

**Rationale**: `Secrets.__init__` takes a `Model` object. Following the tenant-service pattern for `KratosInfoData` (which also takes a `Model`), we use `create_autospec(Model)` and mock `model.get_secret()` / `model.app.add_secret()`. This is pure mock testing — no `ops.testing` needed.

### D5: `DatabaseConfig` / `TracingData` tests — use `create_autospec()` on library requirers

**Rationale**: Both dataclasses have `load()` classmethods that take library objects (`DatabaseRequires`, `TracingEndpointRequirer`). We use `create_autospec()` to mock these, exactly like tenant-service's `TestDatabaseConfig` and `TestTracingData`.

### D6: Ingress relation fixture — `remote_app_data` with `ingress.url` JSON

**Rationale**: `IngressPerAppRequirer.url` reads from the remote app databag via `IngressProviderAppData.load(databag).ingress.url`. The databag format is `{"ingress": {"url": "http://..."}}` (pydantic model serialized). The fixture must provide this format for `ingress.url` to return a value in Scenario tests.

### D7: Delete broken library tests

**Rationale**: `test_authentik_cluster.py` and `test_authentik_server_info.py` import private names (`_CLUSTER_SECRET_LABEL`, `_PASSWORD_SECRET_LABEL`) that don't exist in the library. These are library tests, not charm tests. Library tests belong with the library's own test suite. Deleting them removes broken tests without losing charm coverage.

### D8: `peer_relation` fixture — simplified (no secret IDs)

**Rationale**: The refactored `Secrets` class looks up secrets by **label** (via `model.get_secret(label=...)`), not by ID from the peer databag. The peer relation fixture no longer needs secret ID references — it just needs to exist.

## Risks / Trade-offs

- **[Risk] `IngressPerAppRequirer.url` may not work in Scenario without exact databag format** → Mitigation: Test the `_web_path` and `_authentik_host` properties via `create_autospec` on the charm's `ingress` attribute, or verify the exact databag format with a spike test before writing the full test suite.

- **[Risk] `DatabaseRequires.is_resource_created()` may behave unexpectedly in Scenario** → Mitigation: The `database_resource_is_created` condition is mocked in `all_satisfied_conditions`. Tests that need the real behavior can omit the mock.

- **[Trade-off] Mocking `WorkloadService.is_running`/`is_failing` means we don't test the real pebble check logic** → Acceptable: the real logic is thin (delegates to `container.get_service()`/`get_checks()`) and testing it would require complex Scenario state setup. The tenant-service charm makes the same trade-off.

- **[Trade-off] Deleting library tests reduces coverage of `lib/charms/authentik_server/`** → Acceptable: Library tests should live with the library. The charm's test suite should test the charm, not the library.
