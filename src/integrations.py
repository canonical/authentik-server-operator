# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Wrappers for charm relation data, implementing EnvVarConvertible."""

import logging
from typing import TYPE_CHECKING

import ops

if TYPE_CHECKING:
    pass

from charms.authentik_server.v0.authentik_cluster import AuthentikClusterProvider
from charms.authentik_server.v0.authentik_server_info import AuthentikServerInfoProvider
from charms.data_platform_libs.v0.data_interfaces import DatabaseRequires
from constants import (
    BOOTSTRAP_PASSWORD_PEER_KEY,
    BOOTSTRAP_TOKEN_PEER_KEY,
    PEER_RELATION,
    SECRET_KEY_PEER_KEY,
)
from env_vars import EnvVars

logger = logging.getLogger(__name__)


class DatabaseIntegration:
    """Reads PostgreSQL relation data and exposes it as env vars.

    Args:
        database: The DatabaseRequires library object.
    """

    def __init__(self, database: DatabaseRequires) -> None:
        self._database = database

    def is_ready(self) -> bool:
        """Return True if the database relation is present and has endpoint data."""
        return bool(self._get_connection())

    def _get_connection(self) -> dict[str, str] | None:
        """Return a connection dict or None if the relation is not ready."""
        for data in self._database.fetch_relation_data().values():
            if "endpoints" in data:
                host, port = data["endpoints"].split(":")
                return {
                    "host": host,
                    "port": port,
                    "user": data["username"],
                    "password": data["password"],
                    "name": data["database"],
                }
        return None

    def to_env_vars(self) -> EnvVars:
        """Return PostgreSQL connection environment variables."""
        conn = self._get_connection()
        if not conn:
            return {}
        return {
            "AUTHENTIK_POSTGRESQL__HOST": conn["host"],
            "AUTHENTIK_POSTGRESQL__PORT": conn["port"],
            "AUTHENTIK_POSTGRESQL__USER": conn["user"],
            "AUTHENTIK_POSTGRESQL__PASSWORD": conn["password"],
            "AUTHENTIK_POSTGRESQL__NAME": conn["name"],
        }


class SecretsIntegration:
    """Reads secrets from peer databag and exposes them as env vars.

    Args:
        charm: The charm instance.
    """

    def __init__(self, charm: ops.CharmBase) -> None:
        self._charm = charm

    def is_ready(self) -> bool:
        """Return True if all secrets are available."""
        peer = self._charm.model.get_relation(PEER_RELATION)
        if not peer:
            return False
        return bool(
            peer.data[self._charm.app].get(SECRET_KEY_PEER_KEY)
            and peer.data[self._charm.app].get(BOOTSTRAP_TOKEN_PEER_KEY)
            and peer.data[self._charm.app].get(BOOTSTRAP_PASSWORD_PEER_KEY)
        )

    def _get_secret_value(self, peer_key: str, content_key: str) -> str | None:
        """Retrieve a secret value by its peer databag key."""
        peer = self._charm.model.get_relation(PEER_RELATION)
        if not peer:
            return None
        secret_id = peer.data[self._charm.app].get(peer_key)
        if not secret_id:
            return None
        secret = self._charm.model.get_secret(id=secret_id)
        return secret.get_content()[content_key]

    def to_env_vars(self) -> EnvVars:
        """Return secrets environment variables."""
        secret_key = self._get_secret_value(SECRET_KEY_PEER_KEY, "secret-key")
        bootstrap_token = self._get_secret_value(BOOTSTRAP_TOKEN_PEER_KEY, "bootstrap-token")
        bootstrap_password = self._get_secret_value(
            BOOTSTRAP_PASSWORD_PEER_KEY, "bootstrap-password"
        )
        if not secret_key or not bootstrap_token or not bootstrap_password:
            return {}
        return {
            "AUTHENTIK_SECRET_KEY": secret_key,
            "AUTHENTIK_BOOTSTRAP_TOKEN": bootstrap_token,
            "AUTHENTIK_BOOTSTRAP_PASSWORD": bootstrap_password,
        }


class ClusterIntegration:
    """Provides AUTHENTIK_SECRET_KEY to workers via cluster relation.

    Args:
        cluster_provider: The AuthentikClusterProvider library object.
    """

    def __init__(self, cluster_provider: AuthentikClusterProvider) -> None:
        self._cluster_provider = cluster_provider

    def is_ready(self) -> bool:
        """Return True if the cluster relation is ready."""
        return self._cluster_provider.is_ready()


class ServerInfoIntegration:
    """Provides server info to LDAP outpost via server-info relation.

    Args:
        server_info_provider: The AuthentikServerInfoProvider library object.
    """

    def __init__(self, server_info_provider: AuthentikServerInfoProvider) -> None:
        self._server_info_provider = server_info_provider

    def is_ready(self) -> bool:
        """Return True if the server info relation is ready."""
        return self._server_info_provider.is_ready()
