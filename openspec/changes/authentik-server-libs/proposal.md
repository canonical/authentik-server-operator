## Why

The two custom charm interface libraries owned by the server charm have broken event infrastructure and a secret persistence bug:

**`lib/charms/authentik_server/v0/authentik_cluster.py`** (shared with worker):
- Event container class inherits from `Object` instead of `ObjectEvents`
- No `EventSource` declarations — `self.on.ready` cannot be emitted
- `on = AuthentikClusterProviderEvents` is a class reference, not an instance
- No `framework.observe` calls in `__init__` — underlying relation events are never wired
- `self._secret = None` is reset on every charm initialisation → `SecretAlreadyExistsError` on second run

**`lib/charms/authentik_server/v0/authentik_server_info.py`** (shared with LDAP outpost):
- Same event infrastructure bugs as above
- Two secrets (`bootstrap_token`, `bootstrap_password`) both have the same persistence bug

These bugs make both downstream charms (`authentik-worker-operator`, `authentik-ldap-outpost-operator`) crash on restart. Fixing these libs is a prerequisite for making the worker and LDAP charms production-ready.

## What Changes

- Rewrite `authentik_cluster.py`: correct `ObjectEvents` + `EventSource` pattern, `framework.observe` wiring in `__init__`, label-based secret lookup (no instance state)
- Rewrite `authentik_server_info.py`: same fixes, two-secret pattern (bootstrap token + bootstrap password), `ServerInfoData` Pydantic model
- Bump `LIBPATCH` on both libs

## Capabilities

### Modified Capabilities

- `authentik-cluster-lib`: Correct ops event pattern; secret creation idempotent across restarts
- `authentik-server-info-lib`: Same; Pydantic `ServerInfoData` model for type-safe requirer data access

## Non-goals

- Copying fixed libs into worker or LDAP outpost repos (those are separate changes in their respective repos)
- Charmhub lib publishing (manual step, tracked as a task in this change)
- Any `charm.py` changes beyond what's needed to wire the fixed libs

## Impact

- `lib/charms/authentik_server/v0/authentik_cluster.py` — full rewrite
- `lib/charms/authentik_server/v0/authentik_server_info.py` — full rewrite
- `tests/unit/` — new tests for both libs
