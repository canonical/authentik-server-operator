# authentik_server_info Library

## Interface Contract

Relation: `authentik-server-info` (interface `authentik_server_info`)
Direction: server provides, LDAP outpost requires.

```
Provider (server app databag)            Requirer reads
──────────────────────────────────────────────────────────────
host                          →  Authentik API base URL
bootstrap_token_secret_id     →  model.get_secret(id=...)["bootstrap-token"]
bootstrap_password_secret_id  →  model.get_secret(id=...)["bootstrap-password"]
(both secrets granted to requirer app)
```

## Corrected Implementation

### Events

```python
class AuthentikServerInfoProviderReadyEvent(EventBase):
    """Fired when the provider has written host and credential IDs to the databag."""

class AuthentikServerInfoProviderEvents(ObjectEvents):
    ready = EventSource(AuthentikServerInfoProviderReadyEvent)

class AuthentikServerInfoRequirerReadyEvent(EventBase):
    """Fired when the requirer can read host and credentials."""

class AuthentikServerInfoRequirerEvents(ObjectEvents):
    ready = EventSource(AuthentikServerInfoRequirerReadyEvent)
```

### Provider

```python
_TOKEN_SECRET_LABEL = "authentik-server-info-bootstrap-token"
_PASSWORD_SECRET_LABEL = "authentik-server-info-bootstrap-password"

class AuthentikServerInfoProvider(Object):
    on = AuthentikServerInfoProviderEvents()

    def __init__(self, charm: CharmBase, relation_name: str) -> None:
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name
        self.framework.observe(charm.on[relation_name].relation_created, self._on_created)
        self.framework.observe(charm.on[relation_name].relation_joined, self._on_joined)

    def _on_created(self, event): self.on.ready.emit()
    def _on_joined(self, event): self.on.ready.emit()

    def publish(self, host: str, bootstrap_token: str, bootstrap_password: str) -> None:
        if not self._charm.unit.is_leader():
            return
        token_secret = self._get_or_create_secret(
            _TOKEN_SECRET_LABEL, {"bootstrap-token": bootstrap_token}
        )
        password_secret = self._get_or_create_secret(
            _PASSWORD_SECRET_LABEL, {"bootstrap-password": bootstrap_password}
        )
        for relation in self._charm.model.relations.get(self._relation_name, []):
            token_secret.grant(relation)
            password_secret.grant(relation)
            relation.data[self._charm.app].update({
                "host": host,
                "bootstrap_token_secret_id": token_secret.id,
                "bootstrap_password_secret_id": password_secret.id,
            })

    def _get_or_create_secret(self, label: str, content: dict[str, str]):
        try:
            secret = self._charm.model.get_secret(label=label)
            secret.set_content(content)
        except SecretNotFoundError:
            secret = self._charm.app.add_secret(content, label=label)
        return secret
```

### Requirer

```python
class ServerInfoData(BaseModel):
    host: str
    bootstrap_token: str
    bootstrap_password: str

class AuthentikServerInfoRequirer(Object):
    on = AuthentikServerInfoRequirerEvents()

    def __init__(self, charm: CharmBase, relation_name: str) -> None:
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name
        self.framework.observe(charm.on[relation_name].relation_changed, self._on_changed)

    def _on_changed(self, event: RelationChangedEvent) -> None:
        if self.is_ready:
            self.on.ready.emit()

    @property
    def is_ready(self) -> bool:
        relation = self._charm.model.get_relation(self._relation_name)
        if not relation:
            return False
        data = relation.data[relation.app]
        return bool(data.get("host") and data.get("bootstrap_token_secret_id") and data.get("bootstrap_password_secret_id"))

    def get_info(self) -> ServerInfoData | None:
        relation = self._charm.model.get_relation(self._relation_name)
        if not relation:
            return None
        data = relation.data[relation.app]
        host = data.get("host")
        token_id = data.get("bootstrap_token_secret_id")
        password_id = data.get("bootstrap_password_secret_id")
        if not (host and token_id and password_id):
            return None
        token = self._charm.model.get_secret(id=token_id).get_content()["bootstrap-token"]
        password = self._charm.model.get_secret(id=password_id).get_content()["bootstrap-password"]
        return ServerInfoData(host=host, bootstrap_token=token, bootstrap_password=password)
```

## Files Changed

| File | Change |
|------|--------|
| `lib/charms/authentik_server/v0/authentik_server_info.py` | Full rewrite |

## Acceptance Criteria

- `publish()` idempotent: no `SecretAlreadyExistsError` on second call
- Both secrets granted to relation; databag contains all three fields
- `get_info()` returns `None` without relation; returns `ServerInfoData` when complete
- `on.ready` fires correctly for both provider and requirer
- `LIBPATCH` incremented
