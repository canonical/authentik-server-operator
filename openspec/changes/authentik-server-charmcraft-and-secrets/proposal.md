## Why

The `authentik-server-operator` was created in a hackathon with two structural problems that prevent it from deploying at all:

1. **`charmcraft.yaml` is wrong**: the container is named `authentik-server` instead of `authentik`, the OCI image points to `ghcr.io/canonical/authentik-server` (a non-existent image) instead of `ghcr.io/goauthentik/server:2026.2.2`, and the custom relations (`authentik-cluster`, `authentik-server-info`, `ingress`, `authentik-peers`) are missing entirely.

2. **`_ensure_secrets()` crashes on restart**: it calls `app.add_secret()` unconditionally without checking if the secret already exists and without labels, causing `SecretAlreadyExistsError` on every reconcile after the first.

These two issues must be fixed before any other work can be done on the charm.

## What Changes

- Fix `charmcraft.yaml`: rename container to `authentik`, correct OCI image to `ghcr.io/goauthentik/server:2026.2.2`, add all missing relations
- Add missing `constants.py` entries (`PEER_RELATION_NAME`, `INGRESS_RELATION_NAME`)
- Rewrite `_ensure_secrets()` in `charm.py` to look up secrets by label before creating (idempotent across restarts)

## Capabilities

### Modified Capabilities

- `charmcraft-config`: Correct container name, OCI image, and relation declarations
- `secret-management`: Secret creation uses labels and is idempotent across restarts

## Non-goals

- Lib rewrites (separate change: `authentik-server-libs`)
- Observability wiring (separate change: `authentik-server-observability`)
- TLS/certificate handling
- Grafana dashboard content

## Impact

- `charmcraft.yaml` — structural corrections; `charmcraft pack` will now produce a deployable charm
- `src/charm.py` — `_ensure_secrets()` rewrite; restarts no longer crash
- `src/constants.py` — two new constants
