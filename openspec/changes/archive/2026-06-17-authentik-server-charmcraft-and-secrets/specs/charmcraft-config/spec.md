# charmcraft.yaml Configuration

## MODIFIED Requirements

### Requirement: Container name must match Pebble service name

`charmcraft.yaml` MUST declare the container as `authentik` with resource `authentik-image`.
The Pebble layer uses `CONTAINER_NAME = "authentik"`; `charmcraft.yaml` must match.

```yaml
containers:
  authentik:
    resource: authentik-image
```

#### Scenario: Charm packs and deploys without container errors

Given a `charmcraft.yaml` with `containers.authentik` pointing to `authentik-image`,
when `charmcraft pack` is run and the charm is deployed with
`--resource authentik-image=ghcr.io/goauthentik/server:2026.2.2`,
then the workload container starts without "container not found" errors.

### Requirement: OCI image resource must point to upstream Authentik image

The `resources` section MUST declare `authentik-image` sourced from the official
upstream image `ghcr.io/goauthentik/server:2026.2.2`.

```yaml
resources:
  authentik-image:
    type: oci-image
    description: Authentik server OCI image
    upstream-source: ghcr.io/goauthentik/server:2026.2.2
```

#### Scenario: Default resource resolves to upstream image

Given `charmcraft.yaml` declares `upstream-source: ghcr.io/goauthentik/server:2026.2.2`,
when a user deploys without specifying `--resource authentik-image`,
then Juju pulls the upstream image automatically.

## ADDED Requirements

### Requirement: Charm must declare authentik-cluster and authentik-server-info provided relations

`charmcraft.yaml` MUST include the following entries under `provides`:

```yaml
provides:
  authentik-cluster:
    interface: authentik_cluster
    optional: true
  authentik-server-info:
    interface: authentik_server_info
    optional: true
```

#### Scenario: Relation is available for integration

Given the charm is deployed, when
`juju integrate authentik-server:authentik-cluster authentik-worker:authentik-cluster`
is run, then no "relation not found" error occurs.

### Requirement: Charm must declare ingress required relation

`charmcraft.yaml` MUST include an `ingress` entry under `requires` with `limit: 1`.

```yaml
requires:
  ingress:
    interface: ingress
    optional: true
    limit: 1
```

#### Scenario: Ingress integration accepted

Given the charm is deployed, when
`juju integrate authentik-server:ingress traefik-k8s:ingress` is run,
then the integration completes without errors.

### Requirement: Charm must declare authentik-peers peer relation

`charmcraft.yaml` MUST include an `authentik-peers` peer relation so that the leader
unit can share secrets across units.

```yaml
peers:
  authentik-peers:
    interface: authentik_peers
```

#### Scenario: Peer relation present on multi-unit deployment

Given a multi-unit deployment, when a second unit joins, then the `authentik-peers`
peer relation is established and both units can access shared secret IDs.

### Requirement: PEER_RELATION_NAME constant must be defined in src/constants.py

`src/constants.py` MUST export `PEER_RELATION_NAME = "authentik-peers"` so that
`charm.py` can reference the peer relation by name without string literals.

#### Scenario: Charm references peer relation via constant

Given `PEER_RELATION_NAME` is defined in `constants.py`, when `charm.py` calls
`self.model.get_relation(PEER_RELATION_NAME)`, then the peer relation object is
returned correctly.
