## 1. Rewrite `lib/charms/authentik_server/v0/authentik_cluster.py`

- [x] 1.1 Add `AuthentikClusterProviderReadyEvent(EventBase)` and `AuthentikClusterProviderEvents(ObjectEvents)` with `ready = EventSource(...)`
- [x] 1.2 Add `AuthentikClusterRequirerReadyEvent(EventBase)` and `AuthentikClusterRequirerEvents(ObjectEvents)` with `ready = EventSource(...)`
- [x] 1.3 Rewrite `AuthentikClusterProvider.__init__`: call `super().__init__`, store `_charm` and `_relation_name`, `framework.observe` `relation_created` and `relation_joined`
- [x] 1.4 Rewrite `set_secret_key()`: `model.get_secret(label=_CLUSTER_SECRET_LABEL)` with `SecretNotFoundError` fallback; grant secret and write ID to all relations; remove `self._secret` instance var
- [x] 1.5 Rewrite `AuthentikClusterRequirer.__init__`: observe `relation_changed`
- [x] 1.6 Implement `is_ready` property and `get_secret_key()` method
- [x] 1.7 Add `_CLUSTER_SECRET_LABEL = "authentik-cluster-secret-key"` module constant
- [x] 1.8 Bump `LIBPATCH`

## 2. Rewrite `lib/charms/authentik_server/v0/authentik_server_info.py`

- [x] 2.1 Add `AuthentikServerInfoProviderReadyEvent`, `AuthentikServerInfoProviderEvents`, `AuthentikServerInfoRequirerReadyEvent`, `AuthentikServerInfoRequirerEvents` following the same pattern
- [x] 2.2 Rewrite `AuthentikServerInfoProvider.__init__`: observe `relation_created` and `relation_joined`
- [x] 2.3 Implement `publish(host, bootstrap_token, bootstrap_password)` using `_get_or_create_secret()` helper; grant both secrets; write all three fields to databag
- [x] 2.4 Implement `_get_or_create_secret(label, content)` helper (label lookup with `SecretNotFoundError` fallback)
- [x] 2.5 Add `ServerInfoData(BaseModel)` with `host`, `bootstrap_token`, `bootstrap_password` fields
- [x] 2.6 Rewrite `AuthentikServerInfoRequirer.__init__`: observe `relation_changed`
- [x] 2.7 Implement `is_ready` property and `get_info() -> ServerInfoData | None`
- [x] 2.8 Add `_TOKEN_SECRET_LABEL` and `_PASSWORD_SECRET_LABEL` module constants
- [x] 2.9 Bump `LIBPATCH`

## 3. Unit tests for `authentik_cluster`

- [x] 3.1 Test: `set_secret_key()` on first call creates secret with label and writes ID to relation databag
- [x] 3.2 Test: `set_secret_key()` on second call updates secret content without `SecretAlreadyExistsError`
- [x] 3.3 Test: `on.ready` fires on `relation_created` and `relation_joined`
- [x] 3.4 Test: `is_ready` is `False` when relation absent
- [x] 3.5 Test: `get_secret_key()` returns correct value when relation and secret are present

## 4. Unit tests for `authentik_server_info`

- [x] 4.1 Test: `publish()` idempotent — no error on second call
- [x] 4.2 Test: both secrets are granted to the relation and IDs are in databag
- [x] 4.3 Test: `on.ready` fires when provider is ready
- [x] 4.4 Test: `get_info()` returns `None` when relation absent
- [x] 4.5 Test: `get_info()` returns populated `ServerInfoData` when all fields present

## 5. Lint, format, and final checks

- [x] 5.1 Run `tox -e fmt`
- [x] 5.2 Run `tox -e lint` — no errors
- [x] 5.3 Run `tox -e unit` — all tests pass

## 6. Manual follow-up (tracked, not implemented here)

- [x] 6.1 Register `authentik_cluster` lib on Charmhub and replace `LIBID = "0000000000000000"` with the real ID
- [x] 6.2 Register `authentik_server_info` lib on Charmhub and replace `LIBID = "0000000000000000"` with the real ID
