# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Library for the authentik_cluster relation.

This library is published by the authentik-server charm and consumed
by the authentik-worker charm to share AUTHENTIK_SECRET_KEY.
"""

import logging
from typing import Any, Optional

from ops import Object

# The unique Charmhub library identifier, never change it
LIBID = "0000000000000000"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 1

logger = logging.getLogger(__name__)


class AuthentikClusterProviderEvents(Object):
    """Events emitted by AuthentikClusterProvider."""

    def __init__(self, parent: Any, relation_name: str) -> None:
        super().__init__(parent, relation_name)
        self.relation_name = relation_name

    @property
    def ready(self) -> Any:
        """Event emitted when the relation is ready."""
        from ops import RelationReadyEvent
        return RelationReadyEvent(self._parent, self.relation_name)


class AuthentikClusterRequirerEvents(Object):
    """Events emitted by AuthentikClusterRequirer."""

    def __init__(self, parent: Any, relation_name: str) -> None:
        super().__init__(parent, relation_name)
        self.relation_name = relation_name

    @property
    def cluster_changed(self) -> Any:
        """Event emitted when cluster relation data changes."""
        from ops import RelationChangedEvent
        return RelationChangedEvent(self._parent, self.relation_name)

    @property
    def cluster_removed(self) -> Any:
        """Event emitted when cluster relation is broken."""
        from ops import RelationBrokenEvent
        return RelationBrokenEvent(self._parent, self.relation_name)


class AuthentikClusterProvider(Object):
    """Server-side of the authentik-cluster relation.

    Usage in server charm:
        self.cluster_provider = AuthentikClusterProvider(self)
        # In _ensure_cluster_relation():
        self.cluster_provider.set_secret_key(key_value)
    """

    on = AuthentikClusterProviderEvents

    def __init__(self, charm: Any, relation_name: str = "authentik-cluster") -> None:
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name
        self._secret: Optional[Any] = None

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
            self._secret = self._charm.app.add_secret(
                {"secret-key": secret_key}, label="authentik-secret-key"
            )
        else:
            self._secret.set_content({"secret-key": secret_key})

        for relation in self._charm.model.relations.get(self._relation_name, []):
            self._secret.grant(relation)
            relation.data[self._charm.app]["secret_key_secret_id"] = self._secret.id

    def is_ready(self) -> bool:
        """True if the secret key has been set and published."""
        if self._secret is None:
            return False
        return True


class AuthentikClusterRequirer(Object):
    """Worker-side of the authentik-cluster relation.

    Usage in worker charm:
        self.cluster = AuthentikClusterRequirer(self)
        # In _build_env():
        key = self.cluster.get_secret_key()
    """

    on = AuthentikClusterRequirerEvents

    def __init__(self, charm: Any, relation_name: str = "authentik-cluster") -> None:
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name

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

    def is_ready(self) -> bool:
        """True if the secret key can be retrieved."""
        return self.get_secret_key() is not None