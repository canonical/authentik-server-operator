---
description: "Use when writing or modifying unit tests, integration tests, test fixtures, or conftest files for the charm. Covers test file structure, create_state() factory, ops.testing (Scenario) usage, and test organization."
applyTo: "tests/**"
---

# Testing Guidelines

## File Structure

One file per concern:

| File | Scope |
|------|-------|
| `test_charm.py` | Lifecycle events, `_reconcile()`, collect-status, relation events |
| `test_integrations.py` | Integration wrapper classes tested in isolation |
| `test_configs.py` | `CharmConfig` validation and env var output |
| `test_libs.py` | Charm libraries owned by this repo (`authentik_cluster`, `authentik_server_info`) |

## Unit Tests (`tests/unit/`)

- **Framework**: `ops.testing` (Scenario). Do not use legacy `Harness`.
- **State factory**: Use `create_state()` — a **module-level factory function** in `conftest.py` (NOT a fixture). Import it directly in test files.
- **Do NOT** use `dataclasses.replace()` to modify states. Always create a fresh state via `create_state()`.
- Group tests in classes by event or feature (e.g., `TestPebbleReadyEvent`, `TestCollectStatusEvent`).

### `create_state()` Factory Pattern

```python
from unit.conftest import create_state

# Minimal state (leader=True, can_connect=True, no relations)
state = create_state()

# Custom state
state = create_state(
    leader=False,
    relations=[db_relation, peer_relation],
    secrets=[secret_key_secret],
    config={"log_level": "debug"},
    can_connect=False,
)
```

Supported kwargs: `leader`, `secrets`, `relations`, `containers`, `config`, `can_connect`.
The factory builds a complete `testing.State` with sensible defaults (leader=True, can_connect=True).

### Mocking Rules

- **`mocked_k8s_resource_patch`** — Autouse fixture that mocks `KubernetesComputeResourcesPatch`.
- **`mocked_get_missing_config_keys`** — Included in `all_satisfied_conditions`; patches `CharmConfig.get_missing_config_keys` to return `[]`.
- For `collect-unit-status` tests, mock integration `is_ready()` methods to control status path.
- Use `create_autospec()` for library objects in integration wrapper tests.
- **`mocker.patch.object` on charm handlers DOES NOT WORK** — `ops.Framework.observe()` rejects MagicMock observers. Library event tests must use state-based assertions instead.

### Relation Fixtures

Build reusable relation objects for the charm's standard relations:

```python
@pytest.fixture
def db_relation() -> testing.Relation:
    return testing.Relation(
        "pg-database",
        remote_app_data={
            "database": "authentik",
            "endpoints": "test-host:5432",
            "username": "test-user",
            "password": "test-pass",
        },
    )

@pytest.fixture
def peer_relation() -> testing.Relation:
    return testing.Relation(
        "authentik-peers",
        local_app_data={
            "secret_key_secret_id": "secret://test-key",
            "bootstrap_token_secret_id": "secret://test-token",
            "bootstrap_password_secret_id": "secret://test-password",
        },
    )
```

### Integration Wrapper Test Pattern

Test wrappers in isolation using `create_autospec()` for library objects:
- `to_env_vars()`: verify correct env var keys and values
- `is_ready()`: test true/false paths

These are pure mock tests — no `create_state()` needed.

```python
def test_database_integration_env_vars() -> None:
    db = create_autospec(DatabaseRequires)
    db.fetch_relation_data.return_value = {
        1: {"endpoints": "host:5432", "username": "u", "password": "p", "database": "authentik"}
    }
    integration = DatabaseIntegration(db)
    env = integration.to_env_vars()
    assert env["AUTHENTIK_POSTGRESQL__HOST"] == "host"
    assert env["AUTHENTIK_POSTGRESQL__PORT"] == "5432"
```

## Integration Tests (`tests/integration/`)

- **Framework**: `jubilant` library.
- **Lifecycle order**: deploy → health check → scale up → integrations → scale down → removal.
- **Skippable**: Deploy (`--no-deploy`) and removal (`--keep-models`) must be skippable.
- Use `conftest.py` for model/charm fixtures, `constants.py` for app names, `utils.py` for helpers.
