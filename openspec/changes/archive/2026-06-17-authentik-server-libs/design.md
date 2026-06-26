## Context

Both custom libs were written without a working knowledge of the `ops` event framework. The bugs are systematic: wrong base classes, missing `EventSource` declarations, missing `framework.observe` wiring, and instance-level secret state that is reset on every charm initialisation. The reference implementation is `lib/charms/tenant_service/v0/tenant_service_info.py` in the `tenant-service-operator` repo.

## Goals

- Both libs emit correct `on.ready` events
- Both libs survive restarts without `SecretAlreadyExistsError`
- Both libs are usable by downstream charms (worker, LDAP outpost)

## Decisions

### D1: Follow the `tenant_service_info.py` pattern exactly

The reference lib defines: `EventBase` subclass → `ObjectEvents` subclass with `EventSource` field → `Object` subclass with `on = Events()` (instance). This is the canonical ops pattern and must be followed precisely.

### D2: No instance state for secrets — always look up from the model

Replace `self._secret = None` with a stateless `_get_or_create_secret(label, content)` helper that calls `model.get_secret(label=label)` first, falling back to `app.add_secret(content, label=label)` on `SecretNotFoundError`. This is safe across restarts and multi-unit deployments.

### D3: Provider fires `on.ready` on both `relation_created` and `relation_joined`

`relation_created` fires when the relation is established (could be from either side). `relation_joined` fires when a unit joins (important for multi-unit scenarios where a new worker unit joins an existing relation). Both should trigger the provider to (re-)publish its data.

### D4: Requirer fires `on.ready` only when data is complete

The requirer's `_on_relation_changed` only emits `on.ready` when `is_ready` is `True` (all required databag fields are present). This prevents the charm from acting on incomplete data.

### D5: `ServerInfoData` is a Pydantic `BaseModel`

The requirer returns a typed `ServerInfoData(host, bootstrap_token, bootstrap_password)` rather than a raw dict. This matches the pattern from `tenant_service_info.py` (`TenantServiceProviderData`) and gives type safety to the LDAP outpost charm.

### D6: Module-level secret labels as private constants

```python
_CLUSTER_SECRET_LABEL = "authentik-cluster-secret-key"
_TOKEN_SECRET_LABEL = "authentik-server-info-bootstrap-token"
_PASSWORD_SECRET_LABEL = "authentik-server-info-bootstrap-password"
```

Different from the server charm's own secret labels to avoid collision (the server charm creates its own secrets with `"authentik-secret-key"` etc.; the libs manage separate secrets specifically for cross-charm sharing).

### D7: Bump `LIBPATCH` — do not change `LIBAPI` or `LIBID`

`LIBID` cannot be changed until registered on Charmhub (manual step). `LIBAPI` is unchanged because the public API shape is the same (same class names, same method signatures). Only `LIBPATCH` increments.
