## 1. Fix `charmcraft.yaml`

- [x] 1.1 Rename container `authentik-server` → `authentik` and resource `authentik-server-image` → `authentik-image`
- [x] 1.2 Update `upstream-source` to `ghcr.io/goauthentik/server:2026.2.2`
- [x] 1.3 Add `authentik-cluster` under `provides` (interface `authentik_cluster`, optional)
- [x] 1.4 Add `authentik-server-info` under `provides` (interface `authentik_server_info`, optional)
- [x] 1.5 Add `ingress` under `requires` (interface `ingress`, optional, limit 1)
- [x] 1.6 Add `authentik-peers` under `peers` (interface `authentik_peers`)
- [x] 1.7 Verify the 4 observability relations are present: `logging`, `metrics-endpoint`, `grafana-dashboard`, `tracing`
- [x] 1.8 Run `charmcraft pack` — confirm it succeeds

## 2. Update `src/constants.py`

- [x] 2.1 Verify/add `CONTAINER_NAME = "authentik"`
- [x] 2.2 Add `PEER_RELATION_NAME = "authentik-peers"` if not present
- [x] 2.3 Add `INGRESS_RELATION_NAME = "ingress"` if not present

## 3. Fix `_ensure_secrets()` in `src/charm.py`

- [x] 3.1 Add `from ops.exceptions import SecretNotFoundError` and `import secrets as _secrets`
- [x] 3.2 Add module-level label constants: `_SECRET_KEY_LABEL`, `_BOOTSTRAP_TOKEN_LABEL`, `_BOOTSTRAP_PASSWORD_LABEL`
- [x] 3.3 Add `_ensure_secret(peer, databag_key, label, content_factory)` private helper
- [x] 3.4 Rewrite `_ensure_secrets()` to call `_ensure_secret()` three times (one per secret)
- [x] 3.5 Remove the old unconditional `app.add_secret()` calls

## 4. Unit tests

- [x] 4.1 Add test: `_ensure_secrets()` on first call creates 3 secrets and writes IDs to peer databag
- [x] 4.2 Add test: `_ensure_secrets()` on second call does not raise `SecretAlreadyExistsError`
- [x] 4.3 Add test: non-leader unit skips secret creation
- [x] 4.4 Run `tox -e unit` — all tests pass

## 5. Lint and format

- [x] 5.1 Run `tox -e fmt`
- [x] 5.2 Run `tox -e lint` — no errors
