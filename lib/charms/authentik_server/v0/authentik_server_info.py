# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Interface library for sharing authentik-server info.

This library provides a Python API for both providing and requesting
authentik-server deployment info, such as the HTTP service URL and
bootstrap credentials.

## Getting Started

To use the library from the provider side:

In the `charmcraft.yaml` of the charm, add:
```yaml
provides:
  authentik-server-info:
    interface: authentik_server_info
    optional: true
```

Then, to initialise the library:
```python
from charms.authentik_server.v0.authentik_server_info import AuthentikServerInfoProvider

class AuthentikServerCharm(CharmBase):
    def __init__(self, *args):
        self.server_info_provider = AuthentikServerInfoProvider(self)
        self.framework.observe(
            self.server_info_provider.on.ready,
            self._on_server_info_ready,
        )

    def _on_server_info_ready(self, event):
        self.server_info_provider.update_relations_app_data(
            authentik_host="http://authentik-server:9000",
            api_token=api_token_value,
        )
```

To use from the requirer side:

In the `charmcraft.yaml` of the charm, add:
```yaml
requires:
  authentik-server-info:
    interface: authentik_server_info
    optional: true
```

Then, to initialise the library:
```python
from charms.authentik_server.v0.authentik_server_info import AuthentikServerInfoRequirer

class AuthentikLdapOutpostCharm(CharmBase):
    def __init__(self, *args):
        self.server_info = AuthentikServerInfoRequirer(self)
        self.framework.observe(
            self.server_info.on.info_changed,
            self._on_server_info_changed,
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
from pydantic import BaseModel, ValidationError

LIBID = "786e915b50384bbdaf17fa871eb6202f"
LIBAPI = 0
LIBPATCH = 5

PYDEPS = ["pydantic"]

RELATION_NAME = "authentik-server-info"
INTERFACE_NAME = "authentik_server_info"

logger = logging.getLogger(__name__)


class ProviderData(BaseModel):
    """Data published by the authentik-server into the server-info relation databag."""

    authentik_host: str
    authentik_token_secret_id: str

class AuthentikServerInfoReadyEvent(RelationEvent):
    """Event emitted when the provider populates the relation with info."""


class AuthentikServerInfoChangedEvent(RelationEvent):
    """Event emitted when server-info relation data changes."""


class AuthentikServerInfoRemovedEvent(RelationEvent):
    """Event emitted when the server-info relation is removed."""


class AuthentikServerInfoProviderEvents(ObjectEvents):
    """Events for AuthentikServerInfoProvider."""

    ready = EventSource(AuthentikServerInfoReadyEvent)


class AuthentikServerInfoRequirerEvents(ObjectEvents):
    """Events for AuthentikServerInfoRequirer."""

    info_changed = EventSource(AuthentikServerInfoChangedEvent)
    info_removed = EventSource(AuthentikServerInfoRemovedEvent)


class AuthentikServerInfoProvider(Object):
    """Server-side of the authentik-server-info relation.

    Usage in server charm:
        self.server_info_provider = AuthentikServerInfoProvider(self)
        self.framework.observe(self.server_info_provider.on.ready, self._on_server_info_ready)
    """

    on = AuthentikServerInfoProviderEvents()

    def __init__(self, charm: CharmBase, relation_name: str = RELATION_NAME):
        super().__init__(charm, relation_name)
        self._relation_name = relation_name
        self._charm = charm

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
                secret = self._charm.model.get_secret(label="authentik-api-token")
                secret.revoke(event.relation)
            except SecretNotFoundError:
                pass
        else:
            self._delete_secrets()


    def _delete_secrets(self) -> None:
        """Remove all revisions of the API-token secret, if it exists."""
        if not self._charm.unit.is_leader():
            return
        try:
            secret = self._charm.model.get_secret(label="authentik-api-token")
        except SecretNotFoundError:
            return
        secret.remove_all_revisions()

    def _create_or_update_token_secret(self, label: str, api_token: str) -> Secret:
        """Create or update the app-owned API-token secret."""
        content = {"api-token": api_token}
        try:
            secret = self._charm.model.get_secret(label=label)
            if secret.get_content() != content:
                secret.set_content(content)
        except SecretNotFoundError:
            secret = self._charm.app.add_secret(content, label=label)
        return secret

    def update_relations_app_data(
        self,
        authentik_host: str,
        api_token: str,
    ) -> None:
        """Store the API token in a Juju secret and publish ProviderData to all relations.

        - Creates an app-owned API-token secret on first call
        - Grants it to each related LDAP app
        - Writes ProviderData (host + token secret ID) to each relation databag
        - Idempotent: safe to call multiple times

        Args:
            authentik_host: The Authentik server URL (e.g. "http://authentik-server:9000").
            api_token: The dedicated LDAP automation API token value.
        """
        if not self._charm.unit.is_leader():
            return

        token_secret = self._create_or_update_token_secret("authentik-api-token", api_token)
        data = ProviderData(
            authentik_host=authentik_host,
            authentik_token_secret_id=token_secret.id or token_secret.get_info().id,
        )
        for relation in self._charm.model.relations.get(self._relation_name, []):
            token_secret.grant(relation)
            relation.data[self._charm.app].update(data.model_dump())

    def is_ready(self) -> bool:
        """True if server info has been published to all relations."""
        relations = self._charm.model.relations.get(self._relation_name, [])
        if not relations:
            return False
        for relation in relations:
            data = relation.data[self._charm.app]
            if not (
                data.get("authentik_host")
                and data.get("authentik_token_secret_id")
            ):
                return False
        return True


class AuthentikServerInfoRequirer(Object):
    """LDAP-outpost-side of the authentik-server-info relation.

    Usage in LDAP charm:
        self.server_info = AuthentikServerInfoRequirer(self)
        self.framework.observe(self.server_info.on.info_changed, self._on_info_changed)
    """

    on = AuthentikServerInfoRequirerEvents()

    def __init__(self, charm: CharmBase, relation_name: str = RELATION_NAME):
        super().__init__(charm, relation_name)
        self._relation_name = relation_name
        self._charm = charm

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
        self.on.info_changed.emit(event.relation)

    def _on_relation_broken(self, event: RelationBrokenEvent) -> None:
        self.on.info_removed.emit(event.relation)

    def get_provider_data(self) -> Optional[ProviderData]:
        """Return parsed ProviderData, or None if unavailable or invalid."""
        relation = self._charm.model.get_relation(self._relation_name)
        if not relation or not relation.app:
            return None
        raw = dict(relation.data[relation.app])
        if not (
            raw.get("authentik_host")
            and raw.get("authentik_token_secret_id")
        ):
            return None
        try:
            return ProviderData(**raw)
        except ValidationError:
            logger.warning("Invalid data in authentik-server-info relation databag")
            return None

    def is_ready(self) -> bool:
        """True if the relation exists and contains valid provider data."""
        return self.get_provider_data() is not None

    def get_authentik_host(self) -> Optional[str]:
        """Return the Authentik server URL, or None if unavailable."""
        data = self.get_provider_data()
        return data.authentik_host if data else None

    def _get_secret(self, secret_id: str) -> Optional[Secret]:
        """Fetch a secret by ID, returning None on any error."""
        try:
            return self._charm.model.get_secret(id=secret_id)
        except (SecretNotFoundError, ModelError):
            return None

    def get_authentik_token(self) -> Optional[str]:
        """Retrieve the API token from the granted Juju secret."""
        data = self.get_provider_data()
        if not data:
            return None
        secret = self._get_secret(data.authentik_token_secret_id)
        if not secret:
            return None
        return secret.get_content().get("api-token")
