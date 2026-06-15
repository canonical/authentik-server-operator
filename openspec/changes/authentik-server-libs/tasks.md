## 1. Rewrite `lib/charms/authentik_server/v0/authentik_cluster.py`

- [ ] 1.1 Add `AuthentikClusterProviderReadyEvent(EventBase)` and `AuthentikClusterProviderEvents(ObjectEvents)` with `ready = EventSource(...)`
- [ ] 1.2 Add `AuthentikClusterRequirerReadyEvent(EventBase)` and `AuthentikClusterRequirerEvents(ObjectEvents)` with `ready = EventSource(...)`
- [ ] 1.3 Rewrite `AuthentikClusterProvider.__init__`: call `super().__init__`, store `_charm` and `_relation_name`, `framework.observe` `relation_created` and `relation_joined`
- [ ] 1.4 Rewrite `set_secret_key()`: `model.get_secret(label=_CLUSTER_SECRET_LABEL)` with `SecretNotFoundError` fallback; grant secret and write ID to all relations; remove `self._secret` instance var
- [ ] 1.5 Rewrite `AuthentikClusterRequirer.__init__`: observe `relation_changed`
- [ ] 1.6 Implement `is_ready` property and `get_secret_key()` method
- [ ] 1.7 Add `_CLUSTER_SECRET_LABEL = "authentik-cluster-secret-key"` module constant
- [ ] 1.8 Bump `LIBPATCH`

## 2. Rewrite `lib/charms/authentik_server/v0/authentik_server_info.py`

- [ ] 2.1 Add `AuthentikServerInfoProviderReadyEvent`, `AuthentikServerInfoProviderEvents`, `AuthentikServerInfoRequirerReadyEvent`, `AuthentikServerInfoRequirerEvents` following the same pattern
- [ ] 2.2 Rewrite `AuthentikServerInfoProvider.__init__`: observe `relation_created` and `relation_joined`
- [ ] 2.3 Implement `publish(host, bootstrap_token, bootstrap_password)` using `_get_or_create_secret()` helper; grant both secrets; write all three fields to databag
- [ ] 2.4 Implement `_get_or_create_secret(label, content)` helper (label lookup with `SecretNotFoundError` fallback)
- [ ] 2.5 Add `ServerInfoData(BaseModel)` with `host`, `bootstrap_token`, `bootstrap_password` fields
- [ ] 2.6 Rewrite `AuthentikServerInfoRequirer.__init__`: observe `relation_changed`
- [ ] 2.7 Implement `is_ready` property and `get_info() -> ServerInfoData | None`
- [ ] 2.8 Add `_TOKEN_SECRET_LABEL` and `_PASSWORD_SECRET_LABEL` module constants
- [ ] 2.9 Bump `LIBPATCH`

## 3. Unit tests for `authentik_cluster`

- [ ] 3.1 Test: `set_secret_key()` on first call creates secret with label and writes ID to relation databag
- [ ] 3.2 Test: `set_secret_key()` on second call updates secret content without `SecretAlreadyExistsError`
- [ ] 3.3 Test: `on.ready` fires on `relation_created` and `relation_joined`
- [ ] 3.4 Test: `is_ready` is `False` when relation absent
- [ ] 3.5 Test: `get_secret_key()` returns correct value when relation and secret are present

## 4. Unit tests for `authentik_server_info`

- [ ] 4.1 Test: `publish()` idempotent — no error on second call
- [ ] 4.2 Test: both secrets are granted to the relation and IDs are in databag
- [ ] 4.3 Test: `on.ready` fires when provider is ready
- [ ] 4.4 Test: `get_info()` returns `None` when relation absent
- [ ] 4.5 Test: `get_info()` returns populated `ServerInfoData` when all fields present

## 5. Lint, format, and final checks

- [ ] 5.1 Run `tox -e fmt`
- [ ] 5.2 Run `tox -e lint` — no errors
- [ ] 5.3 Run `tox -e unit` — all tests pass

## 6. Manual follow-up (tracked, not implemented here)

- [ ] 6.1 Register `authentik_cluster` lib on Charmhub and replace `LIBID = "0000000000000000"` with the real ID
- [ ] 6.2 Register `authentik_server_info` lib on Charmhub and replace `LIBID = "0000000000000000"` with the real ID
