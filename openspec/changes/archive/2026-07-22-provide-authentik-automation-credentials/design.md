## Context

The `authentik-server-info` provider previously published two Juju secrets (`bootstrap-token` and an unused `bootstrap-password`) plus three databag fields. The only consumer (the LDAP outpost) needs just an API token and the host. This change collapses the contract to a single canonical `api-token` key.

## Goals / Non-Goals

**Goals:**

- Publish exactly one API token per relation under the canonical `api-token` key, with per-relation grant and revocation.
- Let the requirer tolerate a legacy `bootstrap-token` secret key during a rolling upgrade.

**Non-Goals:**

- Minting or wiring a dedicated least-privilege automation identity (deferred). The bootstrap admin token is currently published as `api-token`.
- Rotating the bootstrap credential or changing intentional internal HTTP transport.

## Decisions

### Single canonical api-token contract

The provider creates one app-owned Juju secret per relation, labeled `authentik-api-token`, containing only the `api-token` key, grants it only to that relation, and revokes it on departure. `ProviderData` carries `authentik_host` and `authentik_token_secret_id`. No `bootstrap-token` alias and no bootstrap-password secret or databag field are published. `LIBPATCH` is incremented; `LIBAPI` is unchanged. The charm is pre-release, so this is a clean cutover.

### Mixed-version requirer tolerance

The requirer prefers the `api-token` secret key and falls back to the legacy `bootstrap-token` key, so a consumer works against a not-yet-upgraded provider during a rolling upgrade.

## Risks / Trade-offs

- **Bootstrap exposure:** Until the dedicated-token work lands, the bootstrap admin token is shared with consumers as `api-token`. Consumers are same-model, same-operator charms; the follow-up removes this exposure.
- **Clean cutover:** Pre-release; provider and consumer upgrade together.
