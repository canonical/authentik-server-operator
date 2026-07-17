## Why

During deployments, administrator/bootstrap credentials in Juju secrets can fall out of sync with the Authentik PostgreSQL database, locking operators out of the web interface. We need a secure, native, and reliable method for Juju operators to fetch the initial bootstrap credentials or safely recover administrative access directly.

## What Changes

- Add a Juju action `get-admin-credentials` to safely fetch the initial bootstrap username, password, and token currently stored in Juju secrets.
- Add a Juju action `create-recovery-link` to dynamically generate a secure, single-use, time-bound admin recovery link using Authentik's native command-line utility.
- Expose clear warnings in `get-admin-credentials` command outputs and descriptions indicating that returned bootstrap passwords do not reflect subsequent runtime changes.

## Non-goals

- Automating the detection or synchronization of user password updates back to the Juju secret backend.
- Bypassing Authentik's built-in access control or hashing configurations.

## Capabilities

### New Capabilities

- `admin-management`: Provide actions to retrieve bootstrap credentials and safely generate single-use recovery URLs for instances.

### Modified Capabilities

None.

## Impact

- **Affected Modules**: [src/charm.py](file:///home/nikos.sklikas@canonical.com/projects/authentik-charms/authentik-server-operator-admin-cmd/src/charm.py), [src/services.py](file:///home/nikos.sklikas@canonical.com/projects/authentik-charms/authentik-server-operator-admin-cmd/src/services.py), [src/cli.py](file:///home/nikos.sklikas@canonical.com/projects/authentik-charms/authentik-server-operator-admin-cmd/src/cli.py), and [charmcraft.yaml](file:///home/nikos.sklikas@canonical.com/projects/authentik-charms/authentik-server-operator-admin-cmd/charmcraft.yaml).
- **Testing**: Requires additions to [tests/unit/test_cli.py](file:///home/nikos.sklikas@canonical.com/projects/authentik-charms/authentik-server-operator-admin-cmd/tests/unit/test_cli.py) and new integration tests in [tests/integration/test_charm.py](file:///home/nikos.sklikas@canonical.com/projects/authentik-charms/authentik-server-operator-admin-cmd/tests/integration/test_charm.py) run after the deployment scaling phase.
