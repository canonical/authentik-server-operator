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
        self.server_info_provider.set_server_info(
            authentik_host="http://authentik-server:9000",
            bootstrap_token=token_value,
            bootstrap_password=password_value,
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

from ops.charm import CharmBase, RelationBrokenEvent, RelationChangedEvent, RelationCreatedEvent
from ops.framework import EventBase, EventSource, Object, ObjectEvents

# The unique Charmhub library identifier, never change it
LIBID = "0000000000000000"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 2

RELATION_NAME = "authentik-server-info"
INTERFACE_NAME = "authentik_server_info"

logger = logging.getLogger(__name__)


class AuthentikServerInfoReadyEvent(EventBase):
    """Event emitted when the provider populates the relation with info."""


class AuthentikServerInfoChangedEvent(EventBase):
    """Event emitted when server-info relation data changes."""


class AuthentikServerInfoRemovedEvent(EventBase):
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
        self._token_secret = None
        self._password_secret = None

        self.framework.observe(
            self._charm.on[relation_name].relation_created,
            self._on_relation_created,
        )

    def _on_relation_created(self, event: RelationCreatedEvent) -> None:
        self.on.ready.emit()

    def set_server_info(
        self,
        authentik_host: str,
        bootstrap_token: str,
        bootstrap_password: str,
    ) -> None:
        """Store connection info in Juju secrets and publish to all relations.

        - Creates two app-owned secrets (token, password) on first call
        - Grants both secrets to each related LDAP app
        - Writes host + secret IDs to provider app databag
        - Idempotent
        """
        if not self._charm.unit.is_leader():
            return

        if self._token_secret is None:
            self._token_secret = self._charm.app.add_secret(
                {"bootstrap-token": bootstrap_token}, label="authentik-bootstrap-token"
            )
        else:
            self._token_secret.set_content({"bootstrap-token": bootstrap_token})

        if self._password_secret is None:
            self._password_secret = self._charm.app.add_secret(
                {"bootstrap-password": bootstrap_password}, label="authentik-bootstrap-password"
            )
        else:
            self._password_secret.set_content({"bootstrap-password": bootstrap_password})

        for relation in self._charm.model.relations.get(self._relation_name, []):
            self._token_secret.grant(relation)
            self._password_secret.grant(relation)
            relation.data[self._charm.app].update({
                "authentik_host": authentik_host,
                "authentik_token_secret_id": self._token_secret.id,
                "bootstrap_password_secret_id": self._password_secret.id,
            })

    def is_ready(self) -> bool:
        """True if server info has been published."""
        if not self._charm.unit.is_leader():
            return False
        for relation in self._charm.model.relations.get(self._relation_name, []):
            if relation.data[self._charm.app].get("authentik_host"):
                return True
        return False


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
        self.on.info_changed.emit()

    def _on_relation_broken(self, event: RelationBrokenEvent) -> None:
        self.on.info_removed.emit()

    def get_authentik_host(self) -> Optional[str]:
        """Return the Authentik server URL."""
        relation = self._charm.model.get_relation(self._relation_name)
        if not relation or not relation.app:
            return None
        return relation.data[relation.app].get("authentik_host")

    def get_authentik_token(self) -> Optional[str]:
        """Retrieve bootstrap token from Juju secret."""
        relation = self._charm.model.get_relation(self._relation_name)
        if not relation or not relation.app:
            return None
        secret_id = relation.data[relation.app].get("authentik_token_secret_id")
        if not secret_id:
            return None
        secret = self._charm.model.get_secret(id=secret_id)
        return secret.get_content()["bootstrap-token"]

    def get_bootstrap_password(self) -> Optional[str]:
        """Retrieve bootstrap password from Juju secret."""
        relation = self._charm.model.get_relation(self._relation_name)
        if not relation or not relation.app:
            return None
        secret_id = relation.data[relation.app].get("bootstrap_password_secret_id")
        if not secret_id:
            return None
        secret = self._charm.model.get_secret(id=secret_id)
        return secret.get_content()["bootstrap-password"]

    def is_ready(self) -> bool:
        """True if all 3 fields (host, token, password) are available."""
        return (
            self.get_authentik_host() is not None
            and self.get_authentik_token() is not None
            and self.get_bootstrap_password() is not None
        )
