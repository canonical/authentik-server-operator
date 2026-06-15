## 1. Fix `charmcraft.yaml`

- [ ] 1.1 Rename container `authentik-server` → `authentik` and resource `authentik-server-image` → `authentik-image`
- [ ] 1.2 Update `upstream-source` to `ghcr.io/goauthentik/server:2026.2.2`
- [ ] 1.3 Add `authentik-cluster` under `provides` (interface `authentik_cluster`, optional)
- [ ] 1.4 Add `authentik-server-info` under `provides` (interface `authentik_server_info`, optional)
- [ ] 1.5 Add `ingress` under `requires` (interface `ingress`, optional, limit 1)
- [ ] 1.6 Add `authentik-peers` under `peers` (interface `authentik_peers`)
- [ ] 1.7 Verify the 4 observability relations are present: `logging`, `metrics-endpoint`, `grafana-dashboard`, `tracing`
- [ ] 1.8 Run `charmcraft pack` — confirm it succeeds

## 2. Update `src/constants.py`

- [ ] 2.1 Verify/add `CONTAINER_NAME = "authentik"`
- [ ] 2.2 Add `PEER_RELATION_NAME = "authentik-peers"` if not present
- [ ] 2.3 Add `INGRESS_RELATION_NAME = "ingress"` if not present

## 3. Fix `_ensure_secrets()` in `src/charm.py`

- [ ] 3.1 Add `from ops.exceptions import SecretNotFoundError` and `import secrets as _secrets`
- [ ] 3.2 Add module-level label constants: `_SECRET_KEY_LABEL`, `_BOOTSTRAP_TOKEN_LABEL`, `_BOOTSTRAP_PASSWORD_LABEL`
- [ ] 3.3 Add `_ensure_secret(peer, databag_key, label, content_factory)` private helper
- [ ] 3.4 Rewrite `_ensure_secrets()` to call `_ensure_secret()` three times (one per secret)
- [ ] 3.5 Remove the old unconditional `app.add_secret()` calls

## 4. Unit tests

- [ ] 4.1 Add test: `_ensure_secrets()` on first call creates 3 secrets and writes IDs to peer databag
- [ ] 4.2 Add test: `_ensure_secrets()` on second call does not raise `SecretAlreadyExistsError`
- [ ] 4.3 Add test: non-leader unit skips secret creation
- [ ] 4.4 Run `tox -e unit` — all tests pass

## 5. Lint and format

- [ ] 5.1 Run `tox -e fmt`
- [ ] 5.2 Run `tox -e lint` — no errors
