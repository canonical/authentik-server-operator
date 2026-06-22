# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Library for the authentik_cluster relation.

This library is published by the authentik-server charm and consumed
by the authentik-worker charm to share AUTHENTIK_SECRET_KEY.

## Getting Started

To use the library from the provider side:

In the `charmcraft.yaml` of the charm, add:
```yaml
provides:
  authentik-cluster:
    interface: authentik_cluster
    optional: true
```

Then, to initialise the library:
```python
from charms.authentik_server.v0.authentik_cluster import AuthentikClusterProvider

class AuthentikServerCharm(CharmBase):
    def __init__(self, *args):
        self.cluster_provider = AuthentikClusterProvider(self)
        self.framework.observe(
            self.cluster_provider.on.ready,
            self._on_cluster_ready,
        )

    def _on_cluster_ready(self, event):
        self.cluster_provider.set_secret_key(secret_key_value)
```

To use from the requirer side:

In the `charmcraft.yaml` of the charm, add:
```yaml
requires:
  authentik-cluster:
    interface: authentik_cluster
    optional: true
```

Then, to initialise the library:
```python
from charms.authentik_server.v0.authentik_cluster import AuthentikClusterRequirer

class AuthentikWorkerCharm(CharmBase):
    def __init__(self, *args):
        self.cluster = AuthentikClusterRequirer(self)
        self.framework.observe(
            self.cluster.on.cluster_changed,
            self._on_cluster_changed,
        )
```
"""

import logging
from typing import Optional

from ops import SecretNotFoundError
from ops.charm import CharmBase, RelationChangedEvent, RelationCreatedEvent
from ops.framework import EventBase, EventSource, Object, ObjectEvents

# The unique Charmhub library identifier, never change it
LIBID = "0000000000000000"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 3

RELATION_NAME = "authentik-cluster"
INTERFACE_NAME = "authentik_cluster"

logger = logging.getLogger(__name__)


class AuthentikClusterReadyEvent(EventBase):
    """Event emitted when the cluster relation is ready."""


class AuthentikClusterChangedEvent(EventBase):
    """Event emitted when cluster relation data changes."""


class AuthentikClusterRemovedEvent(EventBase):
    """Event emitted when the cluster relation is removed."""


class AuthentikClusterProviderEvents(ObjectEvents):
    """Events emitted by AuthentikClusterProvider."""

    ready = EventSource(AuthentikClusterReadyEvent)


class AuthentikClusterRequirerEvents(ObjectEvents):
    """Events emitted by AuthentikClusterRequirer."""

    cluster_changed = EventSource(AuthentikClusterChangedEvent)
    cluster_removed = EventSource(AuthentikClusterRemovedEvent)


class AuthentikClusterProvider(Object):
    """Server-side of the authentik-cluster relation.

    Usage in server charm:
        self.cluster_provider = AuthentikClusterProvider(self)
        self.framework.observe(self.cluster_provider.on.ready, self._on_cluster_ready)
    """

    on = AuthentikClusterProviderEvents()

    def __init__(self, charm: CharmBase, relation_name: str = RELATION_NAME) -> None:
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name
        self._secret = None

        self.framework.observe(
            self._charm.on[relation_name].relation_created,
            self._on_relation_created,
        )

    def _on_relation_created(self, event: RelationCreatedEvent) -> None:
        self.on.ready.emit()

    def set_secret_key(self, secret_key: str) -> None:
        """Store the secret key and publish to all related apps.

        - Creates an app-owned Juju secret on first call
        - Grants the secret to each related worker app
        - Writes secret_key_secret_id to provider app databag
        - Idempotent: safe to call multiple times
        """
        if not self._charm.unit.is_leader():
            return

        if self._secret is None:
            try:
                self._secret = self._charm.model.get_secret(label="authentik-secret-key")
            except SecretNotFoundError:
                self._secret = self._charm.app.add_secret(
                    {"secret-key": secret_key}, label="authentik-secret-key"
                )

        self._secret.set_content({"secret-key": secret_key})

        for relation in self._charm.model.relations.get(self._relation_name, []):
            self._secret.grant(relation)
            relation.data[self._charm.app]["secret_key_secret_id"] = self._secret.id

    def set_server_version(self, version: str) -> None:
        """Publish the server's workload version to all related workers.

        Workers read this and block if their own version doesn't match,
        preventing schema mismatches after upgrades.

        Args:
            version: The authentik workload version string (e.g. "2026.5.3").
        """
        if not self._charm.unit.is_leader():
            return
        for relation in self._charm.model.relations.get(self._relation_name, []):
            relation.data[self._charm.app]["server_version"] = version

    def is_ready(self) -> bool:
        """True if the secret key has been set and published."""
        return self._secret is not None


class AuthentikClusterRequirer(Object):
    """Worker-side of the authentik-cluster relation.

    Usage in worker charm:
        self.cluster = AuthentikClusterRequirer(self)
        self.framework.observe(self.cluster.on.cluster_changed, self._on_cluster_changed)
    """

    on = AuthentikClusterRequirerEvents()

    def __init__(self, charm: CharmBase, relation_name: str = RELATION_NAME) -> None:
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name

        self.framework.observe(
            self._charm.on[relation_name].relation_changed,
            self._on_relation_changed,
        )
        self.framework.observe(
            self._charm.on[relation_name].relation_broken,
            self._on_relation_broken,
        )

    def _on_relation_changed(self, event: RelationChangedEvent) -> None:
        if not event.relation.app:
            return
        if not event.relation.data.get(event.relation.app):
            return
        self.on.cluster_changed.emit()

    def _on_relation_broken(self, event: RelationCreatedEvent) -> None:
        self.on.cluster_removed.emit()

    def get_secret_key(self) -> Optional[str]:
        """Retrieve AUTHENTIK_SECRET_KEY from the Juju secret.

        Reads secret_key_secret_id from provider app databag,
        fetches the granted secret, returns value.
        Returns None if relation missing or secret not yet available.
        """
        relation = self._charm.model.get_relation(self._relation_name)
        if not relation or not relation.app:
            return None
        secret_id = relation.data[relation.app].get("secret_key_secret_id")
        if not secret_id:
            return None
        secret = self._charm.model.get_secret(id=secret_id)
        return secret.get_content()["secret-key"]

    def get_server_version(self) -> Optional[str]:
        """Return the server's published workload version, or None if not yet set."""
        relation = self._charm.model.get_relation(self._relation_name)
        if not relation or not relation.app:
            return None
        return relation.data[relation.app].get("server_version")

    def is_ready(self) -> bool:
        """True if the secret key can be retrieved."""
        return self.get_secret_key() is not None