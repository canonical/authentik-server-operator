## Why

The charm published the Authentik bootstrap admin token to LDAP consumers through a dual-secret `authentik-server-info` contract (`bootstrap-token` plus an unused `bootstrap-password`). Consumers only ever needed a single API token, so the extra secret and the legacy alias added credential surface for no benefit. This change collapses the contract to a single canonical `api-token` key.

Minting a dedicated, least-privilege automation identity (so the bootstrap token is never shared with consumers) is a larger effort and is **deferred** (tracked separately); until it lands, the server publishes its bootstrap admin token under the `api-token` key.

## What Changes

- Collapse the `authentik-server-info` contract to a single canonical `api-token` secret key (LIBPATCH 4). `ProviderData` carries `authentik_host` and `authentik_token_secret_id` only; no `bootstrap-token` alias and no `bootstrap-password` field or secret are published.
- Publish one app-owned token secret per relation, granted only to that relation and revoked on relation departure.
- The requirer resolves the token from the canonical `api-token` key and tolerates a legacy `bootstrap-token` key, so consumers work against a not-yet-upgraded provider during a rolling upgrade.

## Capabilities

### Modified Capabilities

- `authentik-server-info-lib`: single canonical `api-token` server-info contract with per-relation secret grants and no bootstrap-password field or `bootstrap-token` alias.

## Non-goals

- Minting a dedicated least-privilege server/LDAP automation identity and wiring the charm to use it (deferred; tracked separately). The server currently publishes its bootstrap admin token under the `api-token` key.
- Rotating the bootstrap credential or changing intentional internal HTTP transport.

## Impact

- `lib/charms/authentik_server/v0/authentik_server_info.py`: api-token contract, LIBPATCH 4.
- `src/integrations.py`, `src/charm.py`: publish `authentik_host` + `api_token` per relation.
