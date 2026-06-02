#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm the Authentik server application."""

import logging
import secrets

import ops
from charms.authentik_server.v0.authentik_cluster import AuthentikClusterProvider
from charms.authentik_server.v0.authentik_server_info import AuthentikServerInfoProvider
from charms.data_platform_libs.v0.data_interfaces import DatabaseRequires
from charms.traefik_k8s.v2.ingress import IngressPerAppRequirer
from configs import CharmConfig
from constants import (
    BOOTSTRAP_PASSWORD_PEER_KEY,
    BOOTSTRAP_TOKEN_PEER_KEY,
    CLUSTER_RELATION,
    DATABASE_RELATION,
    HTTP_PORT,
    HTTPS_PORT,
    INGRESS_RELATION,
    PEER_RELATION,
    SECRET_KEY_PEER_KEY,
    SERVER_INFO_RELATION,
    WORKLOAD_CONTAINER,
)
from integrations import (
    ClusterIntegration,
    DatabaseIntegration,
    SecretsIntegration,
    ServerInfoIntegration,
)
from services import PebbleService

logger = logging.getLogger(__name__)


class AuthentikServerCharm(ops.CharmBase):
    """Authentik Server Operator."""

    def __init__(self, framework: ops.Framework) -> None:
        super().__init__(framework)

        self._container = self.unit.get_container(WORKLOAD_CONTAINER)
        self._pebble = PebbleService(self.unit)
        self._config = CharmConfig(self.config)

        self.database = DatabaseRequires(
            self, relation_name=DATABASE_RELATION, database_name="authentik"
        )
        self.cluster_provider = AuthentikClusterProvider(self, relation_name=CLUSTER_RELATION)
        self.server_info_provider = AuthentikServerInfoProvider(
            self, relation_name=SERVER_INFO_RELATION
        )
        self.ingress = IngressPerAppRequirer(self, relation_name=INGRESS_RELATION, port=HTTP_PORT)

        self._db_integration = DatabaseIntegration(self.database)
        self._secrets_integration = SecretsIntegration(self)
        self._cluster_integration = ClusterIntegration(self.cluster_provider)
        self._server_info_integration = ServerInfoIntegration(self.server_info_provider)

        self.framework.observe(self.on.install, self._on_event)
        self.framework.observe(self.on.config_changed, self._on_event)
        self.framework.observe(self.on.authentik_pebble_ready, self._on_event)
        self.framework.observe(self.database.on.database_created, self._on_event)
        self.framework.observe(self.database.on.endpoints_changed, self._on_event)
        self.framework.observe(self.cluster_provider.on.ready, self._on_event)
        self.framework.observe(self.server_info_provider.on.ready, self._on_event)
        self.framework.observe(self.ingress.on.ready, self._on_event)
        self.framework.observe(self.ingress.on.revoked, self._on_event)

        self.framework.observe(self.on.collect_unit_status, self._on_collect_status)

    def _on_event(self, event: ops.EventBase) -> None:
        self._reconcile()

    def _reconcile(self) -> None:
        """Idempotent reconciliation. Called on every event."""
        if not self._container.can_connect():
            return

        self._ensure_secrets()
        self._ensure_relations()
        self._ensure_pebble_layer()

    def _ensure_secrets(self) -> None:
        """Generate all secrets (leader only). Store IDs in peer databag."""
        if not self.unit.is_leader():
            return

        peer = self.model.get_relation(PEER_RELATION)
        if peer is None:
            return

        if not peer.data[self.app].get(SECRET_KEY_PEER_KEY):
            key = secrets.token_urlsafe(50)
            secret = self.app.add_secret(
                {"secret-key": key},
            )
            peer.data[self.app][SECRET_KEY_PEER_KEY] = secret.id
            logger.info("generated AUTHENTIK_SECRET_KEY")

        if not peer.data[self.app].get(BOOTSTRAP_TOKEN_PEER_KEY):
            token = secrets.token_urlsafe(50)
            secret = self.app.add_secret(
                {"bootstrap-token": token},
            )
            peer.data[self.app][BOOTSTRAP_TOKEN_PEER_KEY] = secret.id
            logger.info("generated AUTHENTIK_BOOTSTRAP_TOKEN")

        if not peer.data[self.app].get(BOOTSTRAP_PASSWORD_PEER_KEY):
            password = secrets.token_urlsafe(32)
            secret = self.app.add_secret(
                {"bootstrap-password": password},
            )
            peer.data[self.app][BOOTSTRAP_PASSWORD_PEER_KEY] = secret.id
            logger.info("generated AUTHENTIK_BOOTSTRAP_PASSWORD")

    def _ensure_relations(self) -> None:
        """Share secrets with related apps."""
        if not self.unit.is_leader():
            return

        secret_key = self._secrets_integration._get_secret_value(SECRET_KEY_PEER_KEY, "secret-key")
        if secret_key:
            self.cluster_provider.set_secret_key(secret_key)

        bootstrap_token = self._secrets_integration._get_secret_value(
            BOOTSTRAP_TOKEN_PEER_KEY, "bootstrap-token"
        )
        bootstrap_password = self._secrets_integration._get_secret_value(
            BOOTSTRAP_PASSWORD_PEER_KEY, "bootstrap-password"
        )
        if bootstrap_token and bootstrap_password:
            self.server_info_provider.set_server_info(
                authentik_host=f"http://{self.app.name}:{HTTP_PORT}",
                bootstrap_token=bootstrap_token,
                bootstrap_password=bootstrap_password,
            )

    def _ensure_pebble_layer(self) -> None:
        """Render and apply the Pebble layer if all prerequisites are available."""
        if not self._db_integration.is_ready():
            return
        if not self._secrets_integration.is_ready():
            return

        layer = self._pebble.render_pebble_layer(
            self._db_integration,
            self._secrets_integration,
            self._config,
        )
        self._pebble.plan(layer)
        self._container.open_port("tcp", HTTP_PORT)
        self._container.open_port("tcp", HTTPS_PORT)

    def _on_collect_status(self, event: ops.CollectStatusEvent) -> None:
        """Report unit status."""
        if not self._container.can_connect():
            event.add_status(ops.WaitingStatus("waiting for pebble"))
            return

        if not self._db_integration.is_ready():
            event.add_status(ops.BlockedStatus("missing pg-database relation"))
            return

        if not self._secrets_integration.is_ready():
            event.add_status(ops.WaitingStatus("waiting for secrets"))
            return

        event.add_status(ops.ActiveStatus())


if __name__ == "__main__":  # pragma: nocover
    ops.main(AuthentikServerCharm)
