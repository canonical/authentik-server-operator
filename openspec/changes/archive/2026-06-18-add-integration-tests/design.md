## Context

The authentik-server-operator currently has a minimal integration test that deploys the charm in isolation (no PostgreSQL) and waits for `jubilant.all_active`. This is insufficient because the charm requires `pg-database` to reach ActiveStatus — without it, the charm blocks. The tenant-service-operator has a mature integration test suite with lifecycle stages (deploy, health, scale, integration removal, teardown) using raw `jubilant`. We want to replicate that pattern while upgrading to `pytest-jubilant` for built-in model management, markers, and CLI options.

The existing `conftest.py` manually creates a `juju` fixture with `jubilant.temp_model()`, and the `test_charm.py` has a single `test_deploy`. Both need to be replaced.

## Goals / Non-Goals

**Goals:**
- Full lifecycle integration test suite: deploy with PostgreSQL and authentik-worker, health check, scale up/down, integration removal/recreation, removal
- Use `pytest-jubilant` for model management, `juju_setup`/`juju_teardown` markers, and CLI options (`--no-juju-setup`, `--no-juju-teardown`, `--juju-model`)
- Reuse utility patterns from tenant-service (status predicates, `remove_integration` context manager, unit address helpers)
- Required dependencies only (PostgreSQL + authentik-worker) — keep the test fast and reliable

**Non-Goals:**
- Testing optional relations (`ingress`, `logging`, `tracing`, `authentik-server-info`) in the main lifecycle flow — can be added later as separate test modules
- Testing charm actions — authentik-server has no actions defined
- Testing upgrade paths

## Decisions

### 1. Use `pytest-jubilant` instead of hand-rolled model management

**Choice**: Use `pytest-jubilant>=2,<3` plugin for the `juju` fixture, markers, and CLI options.

**Rationale**: The tenant-service conftest has ~60 lines of boilerplate for `pytest_addoption`, `pytest_configure`, `pytest_collection_modifyitems`, and a manual `juju` fixture. `pytest-jubilant` provides all of this out of the box:
- `juju` fixture (module-scoped, auto temp model, auto teardown)
- `@pytest.mark.juju_setup` / `@pytest.mark.juju_teardown` markers
- `--no-juju-setup`, `--no-juju-teardown`, `--juju-model` CLI options
- `--juju-dump-logs` for CI log collection

**Alternative considered**: Keep the hand-rolled approach for consistency with tenant-service. Rejected because pytest-jubilant is the Canonical standard going forward and eliminates significant boilerplate.

### 2. Deploy PostgreSQL and authentik-worker as required dependencies

**Choice**: The setup stage deploys `postgresql-k8s` and `authentik-worker` alongside the charm-under-test, integrating both via their required relations.

**Rationale**: Authentik-server's required relations are `pg-database` and `authentik-cluster` (both `optional: false` in charmcraft.yaml). Without the worker, the charm blocks with `"missing authentik-worker relation"`. Integration removal tests cover both required relations since both affect status.

**Alternative considered**: Deploy only PostgreSQL and skip the worker. Rejected — the `authentik-cluster` relation is required and the charm will not reach ActiveStatus without it.

### 3. Copy utility patterns from tenant-service

**Choice**: Create `tests/integration/utils.py` and `tests/integration/constants.py` adapted from tenant-service, removing `juju_model_factory` (handled by pytest-jubilant).

**Rationale**: The status predicate helpers (`all_active`, `is_blocked`, `unit_number`, `and_`), `remove_integration` context manager, and `get_unit_address` are reusable patterns. Copying them maintains consistency across the Identity Platform charms.

### 4. Health check via HTTP endpoint

**Choice**: Test workload health by hitting `http://{unit_address}:9000/-/health/live/` after deployment.

**Rationale**: The charm defines `HEALTH_CHECK_URL = "http://localhost:9000/-/health/live/"` in constants. The workload exposes HTTP on port 9000. This validates the Pebble service is running and the workload is healthy — a basic smoke test.

## Risks / Trade-offs

- **[Risk]** PostgreSQL and authentik-worker charm deployments are slow (~5-8 min total) → **Mitigation**: `--no-juju-setup` allows reusing an existing model for faster iteration
- **[Risk]** `remove_integration` with `pg-database` or `authentik-cluster` may leave the charm in BlockedStatus for a long time → **Mitigation**: Use generous timeout (10 min) and the `is_blocked` status predicate to detect the expected state quickly
- **[Risk]** pytest-jubilant is newer and may have edge cases → **Mitigation**: It's a Canonical-maintained project (v2.1.1), actively used in other charms
- **[Trade-off]** Skipping optional-relation tests means we don't validate `ingress`, `logging`, `tracing`, or `authentik-server-info` end-to-end → Acceptable for initial suite; can be added later
