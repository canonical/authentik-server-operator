## 1. Server-info api-token contract

- [x] 1.1 Collapse `lib/charms/authentik_server/v0/authentik_server_info.py` to the single canonical `api-token` contract and bump `LIBPATCH`
- [x] 1.2 Publish `authentik_host` + `api_token` per relation from `src/integrations.py` and `src/charm.py`, with per-relation grant and revocation
- [x] 1.3 Requirer resolves `api-token` with a legacy `bootstrap-token` fallback for rolling upgrades
- [x] 1.4 Add library and charm tests for api-token content, per-relation grants, cleanup, and no bootstrap-password disclosure

## 2. Verification

- [x] 2.1 Run focused library and charm tests
- [x] 2.2 Parent-owned repository-wide verification
