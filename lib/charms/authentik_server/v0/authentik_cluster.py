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
    optional: false
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
        self.cluster_provider.update_relations_app_data(secret_key=secret_key_value)
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

from ops import ModelError, Secret, SecretNotFoundError
from ops.charm import (
    CharmBase,
    RelationBrokenEvent,
    RelationChangedEvent,
    RelationCreatedEvent,
    RelationEvent,
)
from ops.framework import EventSource, Object, ObjectEvents
from pydantic import BaseModel, Field, ValidationError

LIBID = "810ec184ec9e4c61aa18b3eef8e5e241"
LIBAPI = 0
LIBPATCH = 2

PYDEPS = ["pydantic"]

RELATION_NAME = "authentik-cluster"
INTERFACE_NAME = "authentik_cluster"

logger = logging.getLogger(__name__)


class ProviderData(BaseModel):
    """Data published by the authentik-server into the cluster relation databag."""

    secret_key_secret_id: str
    db_host: str
    db_port: str
    db_user: str
    db_name: str
    server_version: str = ""

    secret_key: Optional[str] = Field(default=None, exclude=True)
    db_password: Optional[str] = Field(default=None, exclude=True)

class AuthentikClusterReadyEvent(RelationEvent):
    """Event emitted when the cluster relation is ready."""


class AuthentikClusterChangedEvent(RelationEvent):
    """Event emitted when cluster relation data changes."""


class AuthentikClusterRemovedEvent(RelationEvent):
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

        self.framework.observe(
            self._charm.on[relation_name].relation_created,
            self._on_relation_created,
        )
        self.framework.observe(
            self._charm.on[relation_name].relation_broken,
            self._on_relation_broken,
        )

    def _on_relation_created(self, event: RelationCreatedEvent) -> None:
        self.on.ready.emit(event.relation)

    def _on_relation_broken(self, event: RelationBrokenEvent) -> None:
        if not self._charm.unit.is_leader():
            return

        relations = self._charm.model.relations.get(self._relation_name, [])
        remaining_relations = [rel for rel in relations if rel.id != event.relation.id]
        if remaining_relations:
            try:
                secret = self._charm.model.get_secret(label="authentik-secret-key")
                secret.revoke(event.relation)
            except SecretNotFoundError:
                pass
        else:
            self._delete_secret()

    def _create_or_update_secret(self, secret_key: str, db_password: Optional[str] = None) -> Secret:
        """Create or update the app-owned Juju secret for the cluster secret key."""
        content = {"secret-key": secret_key}
        if db_password:
            content["db-password"] = db_password
        try:
            secret = self._charm.model.get_secret(label="authentik-secret-key")
            current_content = secret.get_content()
            if any(current_content.get(k) != v for k, v in content.items()):
                secret.set_content(content)
        except SecretNotFoundError:
            secret = self._charm.app.add_secret(content, label="authentik-secret-key")
        return secret

    def _delete_secret(self) -> None:
        """Remove all revisions of the cluster secret key secret, if it exists."""
        if not self._charm.unit.is_leader():
            return
        try:
            secret = self._charm.model.get_secret(label="authentik-secret-key")
        except SecretNotFoundError:
            return
        secret.remove_all_revisions()

    def update_relations_app_data(
        self,
        secret_key: str,
        db_host: str,
        db_port: str,
        db_user: str,
        db_password: str,
        db_name: str,
        server_version: str = "",
    ) -> None:
        """Store the secret key and publish provider data to all related workers.

        - Creates an app-owned Juju secret for the secret key on first call
        - Grants the secret to each related worker app
        - Writes ProviderData to each databag
        - Idempotent: safe to call multiple times

        Args:
            secret_key: The AUTHENTIK_SECRET_KEY value to share.
            db_host: The database host.
            db_port: The database port.
            db_user: The database user.
            db_password: The database password.
            db_name: The database name.
            server_version: The authentik workload version string (e.g. "2026.5.3").
        """
        if not self._charm.unit.is_leader():
            return

        secret = self._create_or_update_secret(secret_key, db_password)
        data = ProviderData(
            secret_key_secret_id=secret.id or secret.get_info().id,
            server_version=server_version,
            db_host=db_host,
            db_port=db_port,
            db_user=db_user,
            db_name=db_name,
        )
        for relation in self._charm.model.relations.get(self._relation_name, []):
            secret.grant(relation)
            relation.data[self._charm.app].update(data.model_dump(mode="json", exclude_none=True))

    def is_ready(self) -> bool:
        """True if the secret key has been created and published to all relations."""
        relations = self._charm.model.relations.get(self._relation_name, [])
        if not relations:
            return False
        for relation in relations:
            if not relation.data[self._charm.app].get("secret_key_secret_id"):
                return False
        return True


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
        self.on.cluster_changed.emit(event.relation)

    def _on_relation_broken(self, event: RelationBrokenEvent) -> None:
        self.on.cluster_removed.emit(event.relation)

    def get_provider_data(self) -> Optional[ProviderData]:
        """Return parsed ProviderData with resolved secrets, or None if unavailable or invalid."""
        relation = self._charm.model.get_relation(self._relation_name)
        if not relation or not relation.app:
            return None
        raw = dict(relation.data[relation.app])
        if not (secret_id := raw.get("secret_key_secret_id")):
            return None

        secret = self._get_secret(secret_id)
        if not secret:
            return None

        try:
            content = secret.get_content(refresh=True)
        except (SecretNotFoundError, ModelError) as e:
            logger.warning("Failed to retrieve content for cluster secret: %s", e)
            return None

        raw["db_password"] = content.get("db-password")
        raw["secret_key"] = content.get("secret-key")

        try:
            data = ProviderData(**raw)
        except ValidationError:
            logger.warning("Invalid data in authentik-cluster relation databag or secret")
            return None

        return data

    def _get_secret(self, secret_id: str) -> Optional[Secret]:
        """Fetch a secret by ID, returning None on any error."""
        try:
            return self._charm.model.get_secret(id=secret_id)
        except (SecretNotFoundError, ModelError):
            return None

    def get_secret_key(self) -> Optional[str]:
        """Retrieve AUTHENTIK_SECRET_KEY from the resolved provider data.

        Returns None if the relation is missing or the secret is not yet available.
        """
        data = self.get_provider_data()
        return data.secret_key if data else None

    def get_server_version(self) -> Optional[str]:
        """Return the server's published workload version, or None if not yet set."""
        data = self.get_provider_data()
        return data.server_version if data and data.server_version else None

    def get_database_config(self) -> Optional[dict[str, str]]:
        """Retrieve database configuration from the resolved provider data.

        Returns None if database configuration is missing.
        """
        data = self.get_provider_data()
        if not data or not all([data.db_host, data.db_port, data.db_user, data.db_password, data.db_name]):
            return None
        return {
            "db-host": data.db_host,
            "db-port": data.db_port,
            "db-user": data.db_user,
            "db-password": data.db_password,
            "db-name": data.db_name,
        }

    def is_ready(self) -> bool:
        """True if the relation exists and contains valid provider data."""
        return self.get_provider_data() is not None