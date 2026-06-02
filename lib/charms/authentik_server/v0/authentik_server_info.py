# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
from typing import TYPE_CHECKING

import ops
from ops import Object

# The unique Charmhub library identifier, never change it
LIBID = "0000000000000000"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 1

if TYPE_CHECKING:
    from ops import CharmBase

logger = logging.getLogger(__name__)


class AuthentikServerInfoProviderEvents(Object):
    """Events for AuthentikServerInfoProvider."""

    def __init__(self):
        super().__init__()
        self._ready = ops.EventSource(ops.EventBase)
        self.on = self._ready


class AuthentikServerInfoProvider(Object):
    """Server-side of the authentik-server-info relation.

    Usage in server charm:
        self.server_info_provider = AuthentikServerInfoProvider(self)
        # In _ensure_server_info_relation():
        self.server_info_provider.set_server_info(
            authentik_host="http://authentik-server:9000",
            bootstrap_token=token_value,
            bootstrap_password=password_value,
        )
    """

    on = AuthentikServerInfoProviderEvents()

    def __init__(self, charm: "CharmBase", relation_name: str = "authentik-server-info"):
        super().__init__(charm, relation_name)
        self._relation_name = relation_name
        self._charm = charm
        self._token_secret = None
        self._password_secret = None

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

        self.on.emit()

    def is_ready(self) -> bool:
        """True if server info has been published."""
        if not self._charm.unit.is_leader():
            return False
        for relation in self._charm.model.relations.get(self._relation_name, []):
            if relation.data[self._charm.app].get("authentik_host"):
                return True
        return False


class AuthentikServerInfoRequirerEvents(Object):
    """Events for AuthentikServerInfoRequirer."""

    def __init__(self):
        super().__init__()
        self._info_changed = ops.EventSource(ops.EventBase)
        self._info_removed = ops.EventSource(ops.EventBase)
        self.on = type("Events", (), {
            "info_changed": self._info_changed,
            "info_removed": self._info_removed,
        })()


class AuthentikServerInfoRequirer(Object):
    """LDAP-outpost-side of the authentik-server-info relation.

    Usage in LDAP charm:
        self.server_info = AuthentikServerInfoRequirer(self)
        # In _build_env():
        host = self.server_info.get_authentik_host()
        token = self.server_info.get_authentik_token()
    """

    def __init__(self, charm: "CharmBase", relation_name: str = "authentik-server-info"):
        super().__init__(charm, relation_name)
        self._relation_name = relation_name
        self._charm = charm

    def get_authentik_host(self) -> str | None:
        """Return the Authentik server URL."""
        relation = self._charm.model.get_relation(self._relation_name)
        if not relation or not relation.app:
            return None
        return relation.data[relation.app].get("authentik_host")

    def get_authentik_token(self) -> str | None:
        """Retrieve bootstrap token from Juju secret."""
        relation = self._charm.model.get_relation(self._relation_name)
        if not relation or not relation.app:
            return None
        secret_id = relation.data[relation.app].get("authentik_token_secret_id")
        if not secret_id:
            return None
        secret = self._charm.model.get_secret(id=secret_id)
        return secret.get_content()["bootstrap-token"]

    def get_bootstrap_password(self) -> str | None:
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
