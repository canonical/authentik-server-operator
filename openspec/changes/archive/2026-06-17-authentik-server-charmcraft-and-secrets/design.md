## Context

The charm was scaffolded from a template and the `charmcraft.yaml` was never properly updated. The container name and OCI image are wrong (charm will not deploy), and several required relations are absent (charm will not integrate with other components). Additionally, `_ensure_secrets()` crashes on second run because it calls `app.add_secret()` unconditionally.

## Goals

- `charmcraft pack` produces a deployable charm
- `juju deploy` starts the container successfully
- `juju integrate` works for all documented relations
- `_ensure_secrets()` is idempotent across restarts

## Decisions

### D1: `charmcraft.yaml` corrections are the priority

These changes must land before any other work. The wrong container name means the Pebble layer is applied to a non-existent container; the wrong OCI image means Kubernetes will never pull successfully.

### D2: Secret labels follow `"authentik-<purpose>"` naming

Labels are module-level constants in `charm.py` to keep them close to `_ensure_secrets()`:
```python
_SECRET_KEY_LABEL = "authentik-secret-key"
_BOOTSTRAP_TOKEN_LABEL = "authentik-bootstrap-token"
_BOOTSTRAP_PASSWORD_LABEL = "authentik-bootstrap-password"
```

### D3: `_ensure_secret()` helper for DRY secret creation

A private `_ensure_secret(peer, databag_key, label, content_factory)` helper keeps `_ensure_secrets()` readable. The content factory is a `Callable[[], dict[str, str]]` so values are only generated when actually needed.

### D4: No structural changes to `_reconcile()` in this change

This change only fixes `charmcraft.yaml` and `_ensure_secrets()`. All other reconciliation logic is left untouched to keep the diff minimal and reviewable.
