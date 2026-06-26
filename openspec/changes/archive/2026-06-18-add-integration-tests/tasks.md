## 1. Dependencies & Configuration

- [x] 1.1 Add `pytest-jubilant>=2,<3` to the `integration` optional-dependencies in `pyproject.toml`, keeping existing `jubilant`, `pytest`, `requests`, and `tenacity` entries
- [x] 1.2 Verify `tox.ini` integration env already passes `CHARM_PATH` and uses `pytest` correctly (no changes expected)

## 2. Integration Test Support Files

- [x] 2.1 Create `tests/integration/__init__.py` (empty file)
- [x] 2.2 Create `tests/integration/constants.py` with `APP_NAME`, `APP_IMAGE` (from charmcraft.yaml metadata), `DB_APP = "postgresql-k8s"`, `DB_CHANNEL = "14/stable"`, `WORKER_APP = "authentik-worker"`, and `WORKER_CHANNEL = "latest/edge"` — adapted from tenant-service `constants.py`
- [x] 2.3 Create `tests/integration/utils.py` with status predicates (`all_active`, `all_blocked`, `is_blocked`, `unit_number`, `and_`, `any_error`), `get_unit_data`, `get_unit_address`, `get_integration_data`, and `remove_integration` context manager — adapted from tenant-service `utils.py`, removing `juju_model_factory`

## 3. Conftest & Test Files

- [x] 3.1 Rewrite `tests/integration/conftest.py` — remove `pytest_addoption`, `pytest_configure`, `pytest_collection_modifyitems`, and the manual `juju` fixture; keep `charm` fixture (session-scoped, CHARM_PATH or charmcraft pack), add `http_client` fixture (requests.Session), `integrate_dependencies` helper (pg-database + authentik-cluster), and `public_address` fixture using `get_unit_address`
- [x] 3.2 Rewrite `tests/integration/test_charm.py` with full lifecycle: `test_build_and_deploy` (`@pytest.mark.juju_setup`, deploys PostgreSQL + authentik-worker + charm), `test_app_health` (HTTP GET to `/-/health/live/`), `test_scale_up` (2 units), `test_remove_integration` (parametrized for `pg-database` and `authentik-cluster`), `test_scale_down` (1 unit), `test_remove_application` (`@pytest.mark.juju_teardown`)

## 4. Validation

- [x] 4.1 Run `tox -e fmt` to ensure formatting passes
- [x] 4.2 Run `tox -e lint` to ensure linting passes
