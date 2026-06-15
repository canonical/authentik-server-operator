# authentik_cluster Library

## Interface Contract

Relation: `authentik-cluster` (interface `authentik_cluster`)
Direction: server provides, worker requires.

```
Provider (server app databag)       Requirer reads
────────────────────────────────────────────────────
secret_key_secret_id   →  model.get_secret(id=...)["secret-key"]
(secret granted to requirer app)
```

## Corrected Implementation

### Events

```python
from ops import EventBase, EventSource, ObjectEvents

class AuthentikClusterProviderReadyEvent(EventBase):
    """Fired when the provider has written data to the relation databag."""

class AuthentikClusterProviderEvents(ObjectEvents):
    ready = EventSource(AuthentikClusterProviderReadyEvent)

class AuthentikClusterRequirerReadyEvent(EventBase):
    """Fired when the requirer can read a valid secret key."""

class AuthentikClusterRequirerEvents(ObjectEvents):
    ready = EventSource(AuthentikClusterRequirerReadyEvent)
```

### Provider

```python
_CLUSTER_SECRET_LABEL = "authentik-cluster-secret-key"

class AuthentikClusterProvider(Object):
    on = AuthentikClusterProviderEvents()

    def __init__(self, charm: CharmBase, relation_name: str) -> None:
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name
        self.framework.observe(charm.on[relation_name].relation_created, self._on_created)
        self.framework.observe(charm.on[relation_name].relation_joined, self._on_joined)

    def _on_created(self, event: RelationCreatedEvent) -> None:
        self.on.ready.emit()

    def _on_joined(self, event: RelationJoinedEvent) -> None:
        self.on.ready.emit()

    def set_secret_key(self, secret_key: str) -> None:
        if not self._charm.unit.is_leader():
            return
        try:
            secret = self._charm.model.get_secret(label=_CLUSTER_SECRET_LABEL)
            secret.set_content({"secret-key": secret_key})
        except SecretNotFoundError:
            secret = self._charm.app.add_secret(
                {"secret-key": secret_key}, label=_CLUSTER_SECRET_LABEL
            )
        for relation in self._charm.model.relations.get(self._relation_name, []):
            secret.grant(relation)
            relation.data[self._charm.app]["secret_key_secret_id"] = secret.id
```

### Requirer

```python
class AuthentikClusterRequirer(Object):
    on = AuthentikClusterRequirerEvents()

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
        return bool(relation.data[relation.app].get("secret_key_secret_id"))

    def get_secret_key(self) -> str | None:
        relation = self._charm.model.get_relation(self._relation_name)
        if not relation:
            return None
        secret_id = relation.data[relation.app].get("secret_key_secret_id")
        if not secret_id:
            return None
        return self._charm.model.get_secret(id=secret_id).get_content().get("secret-key")
```

## Files Changed

| File | Change |
|------|--------|
| `lib/charms/authentik_server/v0/authentik_cluster.py` | Full rewrite |

## Acceptance Criteria

- `set_secret_key()` idempotent: first call creates; subsequent calls update without error
- `get_secret_key()` returns `None` when relation absent; returns value when set
- `on.ready` fires on `relation_created` and `relation_joined` (provider)
- `on.ready` fires on `relation_changed` when `secret_key_secret_id` is present (requirer)
- `LIBPATCH` incremented
