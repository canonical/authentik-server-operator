#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm the Authentik server application."""

import logging
from secrets import token_urlsafe

import ops
from charms.authentik_server.v0.authentik_cluster import AuthentikClusterProvider
from charms.authentik_server.v0.authentik_server_info import AuthentikServerInfoProvider
from charms.data_platform_libs.v0.data_interfaces import DatabaseRequires
from charms.grafana_k8s.v0.grafana_dashboard import GrafanaDashboardProvider
from charms.loki_k8s.v1.loki_push_api import LogForwarder
from charms.observability_libs.v0.kubernetes_compute_resources_patch import (
    K8sResourcePatchFailedEvent,
    KubernetesComputeResourcesPatch,
    ResourceRequirements,
    adjust_resource_requirements,
)
from charms.prometheus_k8s.v0.prometheus_scrape import MetricsEndpointProvider
from charms.tempo_coordinator_k8s.v0.tracing import TracingEndpointRequirer
from charms.traefik_k8s.v2.ingress import IngressPerAppRequirer

from configs import CharmConfig
from constants import (
    BOOTSTRAP_PASSWORD_KEY,
    BOOTSTRAP_TOKEN_KEY,
    CLUSTER_RELATION,
    DATABASE_RELATION,
    GRAFANA_RELATION_NAME,
    HTTP_PORT,
    INGRESS_RELATION,
    LOGGING_RELATION_NAME,
    PEBBLE_READY_CHECK_NAME,
    PEER_RELATION,
    PROMETHEUS_RELATION_NAME,
    SECRET_KEY_KEY,
    SERVER_INFO_RELATION,
    TRACING_RELATION_NAME,
    WORKLOAD_CONTAINER,
    WORKLOAD_SERVICE,
)
from exceptions import CharmError, PebbleError
from integrations import (
    DatabaseConfig,
    IngressData,
    TracingData,
)
from secret import Secrets
from services import PebbleService, WorkloadService
from utils import (
    NOOP_CONDITIONS,
    container_connectivity,
    database_integration_exists,
    database_resource_is_created,
)

logger = logging.getLogger(__name__)


class AuthentikServerCharm(ops.CharmBase):
    """Authentik Server Operator."""

    def __init__(self, framework: ops.Framework) -> None:
        super().__init__(framework)

        self._container = self.unit.get_container(WORKLOAD_CONTAINER)
        self._pebble = PebbleService(self.unit)
        self._workload_service = WorkloadService(self.unit)
        self._config = CharmConfig(self.config)

        self.database = DatabaseRequires(
            self, relation_name=DATABASE_RELATION, database_name="authentik"
        )
        self.cluster_provider = AuthentikClusterProvider(self, relation_name=CLUSTER_RELATION)
        self.server_info_provider = AuthentikServerInfoProvider(
            self, relation_name=SERVER_INFO_RELATION
        )
        self.ingress = IngressPerAppRequirer(self, relation_name=INGRESS_RELATION, port=HTTP_PORT)

        # Observability
        self._log_forwarder = LogForwarder(self, relation_name=LOGGING_RELATION_NAME)
        self.metrics_endpoint = MetricsEndpointProvider(
            self,
            relation_name=PROMETHEUS_RELATION_NAME,
            jobs=[
                {
                    "job_name": "authentik_server_metrics",
                    "metrics_path": "/-/metrics/",
                    "static_configs": [{"targets": [f"*:{HTTP_PORT}"]}],
                }
            ],
        )
        self._grafana_dashboards = GrafanaDashboardProvider(
            self,
            relation_name=GRAFANA_RELATION_NAME,
        )
        self.tracing = TracingEndpointRequirer(
            self,
            relation_name=TRACING_RELATION_NAME,
            protocols=["otlp_http"],
        )

        self._secrets = Secrets(self.model, self.model.get_relation(PEER_RELATION))

        self.resources_patch = KubernetesComputeResourcesPatch(
            self,
            WORKLOAD_CONTAINER,
            resource_reqs_func=self._resource_reqs_from_config,
        )

        # Generic event observers
        self.framework.observe(self.on.config_changed, self._on_holistic_handler)
        self.framework.observe(self.database.on.database_created, self._on_holistic_handler)
        self.framework.observe(self.database.on.endpoints_changed, self._on_holistic_handler)
        self.framework.observe(self.cluster_provider.on.ready, self._on_holistic_handler)
        self.framework.observe(self.server_info_provider.on.ready, self._on_holistic_handler)
        self.framework.observe(self.ingress.on.ready, self._on_holistic_handler)
        self.framework.observe(self.ingress.on.revoked, self._on_holistic_handler)
        self.framework.observe(self.tracing.on.endpoint_changed, self._on_holistic_handler)
        self.framework.observe(self.tracing.on.endpoint_removed, self._on_holistic_handler)

        # Pebble events — dedicated handlers
        self.framework.observe(self.on.authentik_pebble_ready, self._on_pebble_ready)
        self.framework.observe(self.on.authentik_pebble_check_failed, self._on_pebble_check_failed)
        self.framework.observe(
            self.on.authentik_pebble_check_recovered, self._on_pebble_check_recovered
        )

        # Lifecycle
        self.framework.observe(self.on.leader_elected, self._on_holistic_handler)
        self.framework.observe(self.on.leader_settings_changed, self._on_holistic_handler)
        self.framework.observe(self.on.secret_changed, self._on_holistic_handler)
        self.framework.observe(self.on.secret_expired, self._on_holistic_handler)
        self.framework.observe(self.on.update_status, self._on_holistic_handler)

        # Peer relation
        self.framework.observe(self.on[PEER_RELATION].relation_created, self._on_holistic_handler)
        self.framework.observe(self.on[PEER_RELATION].relation_changed, self._on_holistic_handler)

        # Database broken
        self.framework.observe(
            self.on[DATABASE_RELATION].relation_broken, self._on_database_relation_broken
        )

        # Resource patching
        self.framework.observe(
            self.resources_patch.on.patch_failed, self._on_resource_patch_failed
        )

        self.framework.observe(self.on.collect_unit_status, self._on_collect_status)

    @property
    def _pebble_layer(self) -> ops.pebble.Layer:
        """Build the pebble layer from all env var sources."""
        return self._pebble.render_pebble_layer(
            DatabaseConfig.load(self.database),
            self._secrets,
            self._config,
            TracingData.load(self.tracing),
            IngressData.load(self.ingress),
        )

    def _on_holistic_handler(self, event: ops.EventBase) -> None:
        """Entry point for the centralized reconciliation handler."""
        self.unit.status = ops.MaintenanceStatus("Configuring resources")
        self._holistic_handler(event)

    def _holistic_handler(self, event: ops.EventBase) -> None:
        """Centralized reconciliation handler."""
        if not all(condition(self) for condition in NOOP_CONDITIONS):
            return

        can_plan = True
        for f in [
            self._ensure_secrets,
            self._ensure_cluster_relation,
            self._ensure_server_info_relation,
        ]:
            try:
                can_plan = can_plan and f()
            except CharmError:
                logger.exception("Error in %s", f.__name__)
                can_plan = False

        if not can_plan:
            return

        try:
            self._pebble.plan(self._pebble_layer)
        except PebbleError:
            logger.error(
                "Failed to plan pebble layer, please check the %s container logs",
                WORKLOAD_CONTAINER,
            )

    def _ensure_secrets(self) -> bool:
        """Generate all secrets (leader only)."""
        if self._secrets.is_ready():
            return True
        if not self.unit.is_leader():
            return False
        self._secrets[SECRET_KEY_LABEL] = {SECRET_KEY_KEY: token_urlsafe(50)}
        self._secrets[BOOTSTRAP_TOKEN_LABEL] = {BOOTSTRAP_TOKEN_KEY: token_urlsafe(50)}
        self._secrets[BOOTSTRAP_PASSWORD_LABEL] = {BOOTSTRAP_PASSWORD_KEY: token_urlsafe(32)}
        return True

    def _ensure_cluster_relation(self) -> bool:
        """Ensure the cluster relation has up-to-date secret key and version data."""
        if (
            self.unit.is_leader()
            and self._secrets.is_ready()
            and self.model.relations[CLUSTER_RELATION]
        ):
            self.cluster_provider.set_secret_key(self._secrets.secret_key)
            self.cluster_provider.set_server_version(self._workload_service.version)
        return True

    def _ensure_server_info_relation(self) -> bool:
        """Ensure the server-info relation has up-to-date data."""
        if (
            self.unit.is_leader()
            and self._secrets.is_ready()
            and self.model.relations[SERVER_INFO_RELATION]
        ):
            self.server_info_provider.update_relations_app_data(
                authentik_host=self._authentik_host,
                bootstrap_token=self._secrets.bootstrap_token,
                bootstrap_password=self._secrets.bootstrap_password,
            )
        return True

    @property
    def _authentik_host(self) -> str:
        """Externally reachable Authentik host URL.

        Uses the ingress URL when ingress is configured, otherwise falls back
        to the cluster-local service address.
        """
        if url := IngressData.load(self.ingress).url:
            return url
        return f"http://{self.app.name}.{self.model.name}.svc.cluster.local:{HTTP_PORT}"

    def _on_pebble_ready(self, event: ops.PebbleReadyEvent) -> None:
        """Handle the pebble-ready event."""
        self._workload_service.open_port()
        self._on_holistic_handler(event)
        self._workload_service.set_version()

    def _on_pebble_check_failed(self, event: ops.PebbleCheckFailedEvent) -> None:
        """Handle the pebble-check-failed event."""
        if event.info.name == PEBBLE_READY_CHECK_NAME:
            logger.warning("The authentik service is not running")

    def _on_pebble_check_recovered(self, event: ops.PebbleCheckRecoveredEvent) -> None:
        """Handle the pebble-check-recovered event."""
        if event.info.name == PEBBLE_READY_CHECK_NAME:
            logger.info("The authentik service is online again")

    def _on_database_relation_broken(self, event: ops.RelationBrokenEvent) -> None:
        """Handle the database relation-broken event."""
        if self._container.can_connect():
            try:
                self._container.stop(WORKLOAD_SERVICE)
            except ops.pebble.Error:
                logger.warning("Failed to stop workload after database relation broken")

    def _on_resource_patch_failed(self, event: K8sResourcePatchFailedEvent) -> None:
        """Handle the resource-patch-failed event."""
        logger.error("Resource patching failed: %s", event.message)
        self._on_holistic_handler(event)

    def _on_collect_status(self, event: ops.CollectStatusEvent) -> None:
        """Report unit status."""
        can_connect = container_connectivity(self)

        if not can_connect:
            event.add_status(ops.WaitingStatus("waiting for pebble"))

        if configs := self._config.get_missing_config_keys():
            event.add_status(ops.BlockedStatus(f"missing required configuration: {configs}"))

        if not database_integration_exists(self):
            event.add_status(ops.BlockedStatus("missing pg-database relation"))

        if database_integration_exists(self) and not database_resource_is_created(self):
            event.add_status(ops.WaitingStatus("waiting for database creation"))

        if not self._secrets.is_ready():
            event.add_status(ops.WaitingStatus("waiting for secrets"))

        if not self.model.relations[CLUSTER_RELATION]:
            event.add_status(ops.BlockedStatus("missing authentik-worker relation"))

        if can_connect and self._workload_service.is_failing():
            event.add_status(
                ops.BlockedStatus(
                    f"failed to start the service, please check the "
                    f"{WORKLOAD_CONTAINER} container logs"
                )
            )

        if can_connect and not self._workload_service.is_running():
            event.add_status(ops.WaitingStatus("waiting for the service to start"))

        event.add_status(self.resources_patch.get_status())
        event.add_status(ops.ActiveStatus())

    def _resource_reqs_from_config(self) -> ResourceRequirements:
        """Build resource requirements from charm config."""
        limits = {"cpu": self.model.config.get("cpu"), "memory": self.model.config.get("memory")}
        requests = {"cpu": "500m", "memory": "1Gi"}
        return adjust_resource_requirements(limits, requests, adhere_to_requests=True)


if __name__ == "__main__":  # pragma: nocover
    ops.main(AuthentikServerCharm)
