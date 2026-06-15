# charmcraft.yaml Configuration Fix

## Container

Change `containers` section:

```yaml
# Before
containers:
  authentik-server:
    resource: authentik-server-image

# After
containers:
  authentik:
    resource: authentik-image
```

The Pebble layer in `services.py` already uses `CONTAINER_NAME = "authentik"`. The YAML must match.

## OCI Image Resource

```yaml
# Before
resources:
  authentik-server-image:
    type: oci-image
    description: Authentik server image
    upstream-source: ghcr.io/canonical/authentik-server:v0.2.0

# After
resources:
  authentik-image:
    type: oci-image
    description: Authentik server OCI image
    upstream-source: ghcr.io/goauthentik/server:2026.2.2
```

## Relations

Add under `provides`:
```yaml
authentik-cluster:
  interface: authentik_cluster
  optional: true

authentik-server-info:
  interface: authentik_server_info
  optional: true
```

Add under `requires`:
```yaml
ingress:
  interface: ingress
  optional: true
  limit: 1
```

Add under `peers`:
```yaml
authentik-peers:
  interface: authentik_peers
```

The four observability relations (`logging`, `metrics-endpoint`, `grafana-dashboard`, `tracing`) should already be present from the hackathon YAML; verify they are correct.

## Constants

Verify/add in `src/constants.py`:
```python
CONTAINER_NAME = "authentik"          # already correct
PEER_RELATION_NAME = "authentik-peers"
INGRESS_RELATION_NAME = "ingress"     # if not present
```

## Acceptance Criteria

- `charmcraft pack` succeeds
- `juju deploy ./authentik-server_*.charm --resource authentik-image=ghcr.io/goauthentik/server:2026.2.2` starts without container errors
- `juju integrate authentik-server:authentik-cluster authentik-worker:authentik-cluster` does not error on missing relation
