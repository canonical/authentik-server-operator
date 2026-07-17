## 1. Action Declarations

- [x] 1.1 Declare the `get-admin-credentials` and `create-recovery-link` actions with clear descriptions, parameters, and stale password warnings in [charmcraft.yaml](file:///home/nikos.sklikas@canonical.com/projects/authentik-charms/authentik-server-operator-admin-cmd/charmcraft.yaml).

## 2. Low-Level Workload Executions

- [x] 2.1 Implement the `create_recovery_key` command-line execution and regex path extraction in `CommandLine` in [src/cli.py](file:///home/nikos.sklikas@canonical.com/projects/authentik-charms/authentik-server-operator-admin-cmd/src/cli.py).
- [x] 2.2 Expose the `create_recovery_link` service wrapper inside `WorkloadService` in [src/services.py](file:///home/nikos.sklikas@canonical.com/projects/authentik-charms/authentik-server-operator-admin-cmd/src/services.py).

## 3. Charm Event Handling

- [x] 3.1 Register the action observers and implement `_on_get_admin_credentials` with a visible stale password warning dictionary key in [src/charm.py](file:///home/nikos.sklikas@canonical.com/projects/authentik-charms/authentik-server-operator-admin-cmd/src/charm.py).
- [x] 3.2 Implement `_on_create_recovery_link` in [src/charm.py](file:///home/nikos.sklikas@canonical.com/projects/authentik-charms/authentik-server-operator-admin-cmd/src/charm.py) utilizing `urllib.parse.urljoin` to join the host and parsed token path safely.

## 4. Testing

- [x] 4.1 Write comprehensive unit tests for `CommandLine.create_recovery_key` in [tests/unit/test_cli.py](file:///home/nikos.sklikas@canonical.com/projects/authentik-charms/authentik-server-operator-admin-cmd/tests/unit/test_cli.py).
- [x] 4.2 Write unit tests for both actions verifying success and failure states in [tests/unit/test_charm.py](file:///home/nikos.sklikas@canonical.com/projects/authentik-charms/authentik-server-operator-admin-cmd/tests/unit/test_charm.py).
- [x] 4.3 Implement new integration tests in [tests/integration/test_charm.py](file:///home/nikos.sklikas@canonical.com/projects/authentik-charms/authentik-server-operator-admin-cmd/tests/integration/test_charm.py) that execute after the application is scaled up to verify the actions dynamically on live units.

## 5. Verification & Style

- [x] 5.1 Format and lint the codebase using `tox -e fmt` and `tox -e lint` before finalizing.
