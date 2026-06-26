## Why

The authentik-server-operator has only a skeleton integration test (`test_deploy`) that deploys the charm without any dependencies and waits for active status. This is insufficient — the charm requires PostgreSQL to function, and we need to validate the full lifecycle (deploy with dependencies, scale up/down, integration removal/recreation, removal). The tenant-service-operator has a mature integration test suite using `jubilant` that we should replicate, upgrading to `pytest-jubilant` for built-in model management, markers, and CLI options.

## What Changes

- Add `pytest-jubilant>=2,<3` as an integration test dependency (replacing manual model lifecycle management)
- Create `tests/integration/constants.py` with authentik-specific app names and image references
- Create `tests/integration/utils.py` with status predicates, `remove_integration` context manager, and unit data helpers (adapted from tenant-service)
- Rewrite `tests/integration/conftest.py` to use pytest-jubilant's `juju` fixture instead of hand-rolled model management
- Rewrite `tests/integration/test_charm.py` with full lifecycle stages: deploy (with PostgreSQL + authentik-worker), health check, scale up, integration removal/recreation (pg-database + authentik-cluster), scale down, removal

## Capabilities

### New Capabilities
- `integration-test-lifecycle`: Full integration test suite covering deploy, health validation, scaling, integration removal/recreation, and teardown using pytest-jubilant

### Modified Capabilities

_(None — no existing specs are modified)_

## Impact

- **Dependencies**: `pyproject.toml` integration deps gain `pytest-jubilant>=2,<3`; `tenacity` retained for retry logic in `remove_integration`
- **Files added**: `tests/integration/constants.py`, `tests/integration/utils.py`, `tests/integration/__init__.py`
- **Files modified**: `tests/integration/conftest.py`, `tests/integration/test_charm.py`, `pyproject.toml`
- **CI**: `tox -e integration` will run the new test suite; pytest-jubilant CLI options (`--no-juju-setup`, `--no-juju-teardown`, `--juju-model`) replace custom `--no-deploy`/`--keep-models`/`--model` options
