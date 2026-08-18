#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm the Authentik server application."""

import logging
import re
import subprocess
from functools import cached_property
from secrets import token_urlsafe
from urllib.parse import urljoin

import ops
from charms.authentik_server.v0.authentik_cluster import AuthentikClusterProvider
from charms.authentik_server.v0.authentik_server_info import AuthentikServerInfoProvider
from charms.certificate_transfer_interface.v1.certificate_transfer import (
    CertificateTransferRequires,
)
from charms.data_platform_libs.v0.data_interfaces import DatabaseRequires
from charms.grafana_k8s.v0.grafana_dashboard import GrafanaDashboardProvider
from charms.hydra.v0.oauth import CLIENT_SECRET_FIELD, OAuthProvider
from charms.loki_k8s.v1.loki_push_api import LogForwarder
from charms.observability_libs.v0.kubernetes_compute_resources_patch import (
    K8sResourcePatchFailedEvent,
    KubernetesComputeResourcesPatch,
    ResourceRequirements,
    adjust_resource_requirements,
)
from charms.prometheus_k8s.v0.prometheus_scrape import MetricsEndpointProvider
from charms.smtp_integrator.v0.smtp import SmtpRequires
from charms.tempo_coordinator_k8s.v0.tracing import TracingEndpointRequirer
from charms.traefik_k8s.v0.traefik_route import TraefikRouteRequirer

from authentik_api import AuthentikAPI
from configs import CharmConfig
from constants import (
    CERTIFICATE_TRANSFER_INTEGRATION_NAME,
    CLUSTER_RELATION,
    DATABASE_RELATION,
    GRAFANA_RELATION_NAME,
    HTTP_PORT,
    LOCAL_CERTIFICATES_PATH,
    LOCAL_CHARM_CERTIFICATES_FILE,
    LOCAL_CHARM_CERTIFICATES_PATH,
    LOGGING_RELATION_NAME,
    METRICS_PORT,
    OAUTH_RELATION_NAME,
    PEBBLE_READY_CHECK_NAME,
    PEER_RELATION,
    PROMETHEUS_RELATION_NAME,
    SERVER_INFO_RELATION,
    SMTP_RELATION,
    TRACING_RELATION_NAME,
    TRAEFIK_ROUTE_RELATION,
    WORKLOAD_CONTAINER,
    WORKLOAD_SERVICE,
)
from exceptions import (
    AuthentikAPIError,
    AuthentikTransientError,
    CharmError,
    DatabaseConnectionError,
    MigrationFailedError,
    MigrationPendingError,
    PebbleError,
    ServiceBackoffError,
    WorkloadNotRunningError,
)
from integrations import (
    DatabaseConfig,
    SmtpData,
    TLSCertificates,
    TracingData,
    TraefikRouteIntegration,
)
from oauth import OauthReconciler
from secret import Secrets
from services import PebbleService, WorkloadService
from utils import (
    NOOP_CONDITIONS,
    container_connectivity,
    database_integration_exists,
    database_resource_is_created,
    traefik_route_integration_exists,
    traefik_route_is_ready,
    traefik_route_is_secure,
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
        self.traefik_route = TraefikRouteRequirer(
            self,
            self.model.get_relation(TRAEFIK_ROUTE_RELATION),
            relation_name=TRAEFIK_ROUTE_RELATION,
        )
        self.smtp = SmtpRequires(self, relation_name=SMTP_RELATION)
        self.oauth_provider = OAuthProvider(self, relation_name=OAUTH_RELATION_NAME)

        # Observability
        self._log_forwarder = LogForwarder(self, relation_name=LOGGING_RELATION_NAME)
        self.metrics_endpoint = MetricsEndpointProvider(
            self,
            relation_name=PROMETHEUS_RELATION_NAME,
            jobs=[
                {
                    "job_name": "authentik_server_metrics",
                    "static_configs": [{"targets": [f"*:{METRICS_PORT}"]}],
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
        self.certificate_transfer_requirer = CertificateTransferRequires(
            self, CERTIFICATE_TRANSFER_INTEGRATION_NAME
        )

        self._secrets = Secrets(self.model)

        self.resources_patch = KubernetesComputeResourcesPatch(
            self,
            WORKLOAD_CONTAINER,
            resource_reqs_func=self._resource_reqs_from_config,
        )

        # Generic event observers
        self.framework.observe(self.on.config_changed, self._on_holistic_handler)
        self.framework.observe(self.database.on.database_created, self._on_holistic_handler)
        self.framework.observe(self.database.on.endpoints_changed, self._on_holistic_handler)
        self.framework.observe(
            self.database.on.read_only_endpoints_changed, self._on_holistic_handler
        )
        self.framework.observe(self.cluster_provider.on.ready, self._on_holistic_handler)
        self.framework.observe(self.server_info_provider.on.ready, self._on_holistic_handler)
        self.framework.observe(self.traefik_route.on.ready, self._on_holistic_handler)
        self.framework.observe(self.smtp.on.smtp_data_available, self._on_holistic_handler)
        self.framework.observe(self.tracing.on.endpoint_changed, self._on_holistic_handler)
        self.framework.observe(self.tracing.on.endpoint_removed, self._on_holistic_handler)

        # Certificate transfer events
        self.framework.observe(
            self.certificate_transfer_requirer.on.certificate_set_updated,
            self._on_holistic_handler,
        )
        self.framework.observe(
            self.certificate_transfer_requirer.on.certificates_removed,
            self._on_holistic_handler,
        )

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

        # OAuth Relation
        self.framework.observe(
            self.on[OAUTH_RELATION_NAME].relation_created, self._on_holistic_handler
        )
        self.framework.observe(
            self.on[OAUTH_RELATION_NAME].relation_changed, self._on_holistic_handler
        )
        self.framework.observe(
            self.on[OAUTH_RELATION_NAME].relation_broken, self._on_holistic_handler
        )

        # Database broken
        self.framework.observe(
            self.on[DATABASE_RELATION].relation_broken, self._on_database_relation_broken
        )

        # Resource patching
        self.framework.observe(
            self.resources_patch.on.patch_failed, self._on_resource_patch_failed
        )

        self.framework.observe(self.on.collect_unit_status, self._on_collect_status)
        self.framework.observe(
            self.on.get_bootstrap_admin_credentials_action,
            self._on_get_bootstrap_admin_credentials,
        )
        self.framework.observe(self.on.create_recovery_link_action, self._on_create_recovery_link)

    @property
    def _authentik_host(self) -> str:
        """Externally reachable Authentik host URL.

        Prioritizes the Traefik route URL when configured, falling back to the
        cluster-local service address.
        """
        if url := TraefikRouteIntegration.load(self.traefik_route).base_url:
            return url
        return self._internal_url

    @property
    def _internal_url(self) -> str:
        """Internally reachable Authentik host URL.

        Uses the cluster-local service address.
        """
        return f"http://{self.app.name}.{self.model.name}.svc.cluster.local:{HTTP_PORT}"

    @property
    def _pebble_layer(self) -> ops.pebble.Layer:
        """Build the pebble layer from all env var sources."""
        return self._pebble.render_pebble_layer(
            DatabaseConfig.load(self.database),
            self._secrets,
            self._config,
            TracingData.load(self.tracing),
            SmtpData.load(self.smtp),
            TraefikRouteIntegration.load(self.traefik_route),
        )

    def _on_holistic_handler(self, event: ops.EventBase) -> None:
        """Entry point for the centralized reconciliation handler."""
        self.unit.status = ops.MaintenanceStatus("Configuring resources")
        self._holistic_handler(event)

    def _holistic_handler(self, event: ops.EventBase) -> None:
        """Centralized reconciliation handler."""
        if not all(condition(self) for condition in NOOP_CONDITIONS):
            return

        self._tls_cert_changed = False
        can_plan = True
        for f in [
            self._ensure_secrets,
            self._ensure_cluster_relation,
            self._ensure_traefik_route,
            self._ensure_server_info_relation,
            self._ensure_tls,
            self._ensure_oauth_relation,
        ]:
            try:
                can_plan = can_plan and f(event)
            except AuthentikTransientError:
                # Transient Authentik failures propagate so Juju retries the hook.
                raise
            except (CharmError, AuthentikAPIError):
                logger.exception("Error in %s", f.__name__)
                can_plan = False

        if not can_plan:
            return

        try:
            self._pebble.plan(self._pebble_layer, force_restart=self._tls_cert_changed)
        except PebbleError:
            logger.error(
                "Failed to plan pebble layer, please check the %s container logs",
                WORKLOAD_CONTAINER,
            )

    def _ensure_secrets(self, event: ops.EventBase | None = None) -> bool:
        """Generate the consolidated secret (leader only)."""
        if self._secrets.is_ready():
            return True
        if not self.unit.is_leader():
            return False
        self._secrets.create(
            secret_key=token_urlsafe(50),
            bootstrap_token=token_urlsafe(50),
            bootstrap_password=token_urlsafe(32),
        )
        return True

    def _ensure_cluster_relation(self, event: ops.EventBase | None = None) -> bool:
        """Ensure the cluster relation has up-to-date secret key and version data."""
        if not self.model.relations[CLUSTER_RELATION]:
            return False
        if self.unit.is_leader() and self._secrets.is_ready():
            db_info = DatabaseConfig.load(self.database)
            if not all([db_info.host, db_info.port, db_info.user, db_info.password, db_info.name]):
                logger.info("Database configuration is not fully ready yet")
                return False
            self.cluster_provider.update_relations_app_data(
                secret_key=self._secrets.secret_key,
                server_version=self._workload_service.version,
                db_host=db_info.host,
                db_port=db_info.port,
                db_user=db_info.user,
                db_password=db_info.password,
                db_name=db_info.name,
                db_read_replicas=",".join(db_info.read_only_endpoints),
                db_use_pgbouncer=self._config.use_pgbouncer_value,
            )
        return True

    def _ensure_traefik_route(self, event: ops.EventBase | None = None) -> bool:
        """Ensure Traefik route configuration is submitted to Traefik."""
        if not self.model.relations[TRAEFIK_ROUTE_RELATION]:
            return False

        if not self.unit.is_leader():
            return True

        if not self.traefik_route.is_ready():
            return False

        integration = TraefikRouteIntegration.load(self.traefik_route)
        config = integration.render_config(self.app.name, self.model.name)
        if not config:
            logger.error("Failed to render Traefik route configuration")
            return False

        try:
            self.traefik_route.submit_to_traefik(config=config)
        except Exception as e:
            logger.error("Failed to submit config to Traefik: %s", e)
            return False

        if not integration.external_host or not integration.secure:
            return False

        return True

    @cached_property
    def _authentik_api(self) -> AuthentikAPI:
        """A single Authentik API client per hook (shared HTTP session and caches)."""
        return AuthentikAPI(self._secrets.bootstrap_token)

    def _ensure_server_info_relation(self, event: ops.EventBase | None = None) -> bool:
        """Publish the Authentik host and API token to the server-info relation.

        The API token is currently the bootstrap admin token, shared under the
        canonical ``api-token`` key. Provisioning a dedicated least-privilege
        automation token is deferred to a later change.

        Publication is gated on the workload API being reachable so consumers are
        only triggered (via the resulting databag change) once Authentik can
        actually serve requests, avoiding a premature provisioning attempt during
        first boot.
        """
        if not (
            self.unit.is_leader()
            and self._secrets.is_ready()
            and self.model.relations[SERVER_INFO_RELATION]
        ):
            return True

        if not self._workload_service.is_running():
            logger.info("Authentik workload is not ready for server-info publication")
            return True

        api = self._authentik_api
        if not api.is_service_available:
            logger.info("Authentik API is not available yet for server-info publication")
            return True

        self.server_info_provider.update_relations_app_data(
            authentik_host=self._internal_url,
            api_token=self._secrets.bootstrap_token,
        )
        return True

    def _ensure_tls(self, event: ops.EventBase | None = None) -> bool:
        """Ensure TLS certificates are updated on both the charm and workload.

        Returns:
            True if TLS certificates were successfully ensured, False otherwise.
        """
        LOCAL_CHARM_CERTIFICATES_FILE.parent.mkdir(parents=True, exist_ok=True)

        certificates = TLSCertificates.load(self.certificate_transfer_requirer).ca_bundle
        existing = (
            LOCAL_CHARM_CERTIFICATES_FILE.read_text()
            if LOCAL_CHARM_CERTIFICATES_FILE.exists()
            else ""
        )

        if certificates == existing:
            return True

        if certificates:
            LOCAL_CHARM_CERTIFICATES_FILE.write_text(certificates)
        else:
            LOCAL_CHARM_CERTIFICATES_FILE.unlink(missing_ok=True)

        try:
            subprocess.run(
                [
                    "update-ca-certificates",
                    "--fresh",
                    "--etccertsdir",
                    str(LOCAL_CERTIFICATES_PATH),
                    "--localcertsdir",
                    str(LOCAL_CHARM_CERTIFICATES_PATH),
                ],
                check=True,
            )
        except subprocess.CalledProcessError:
            logger.exception("Failed to update CA certificates")
            # Remove the cert file so the next reconciliation retries the subprocess.
            LOCAL_CHARM_CERTIFICATES_FILE.unlink(missing_ok=True)
            return False

        self._tls_cert_changed = self._workload_service.update_ca_certs()
        return True

    def _clean_slug(self, name: str) -> str:
        """Sanitize an application/provider name to be a valid Authentik slug.

        Slugs must only contain lowercase alphanumeric, hyphens, and underscores.
        """
        slug = name.lower()
        slug = re.sub(r"[^a-z0-9_-]", "-", slug)
        slug = re.sub(r"-+", "-", slug)
        return slug.strip("-")

    def _ensure_oauth_relation(self, event: ops.EventBase | None = None) -> bool:
        """Ensure active oauth relations are registered in Authentik API and orphans deleted."""
        if not self.unit.is_leader():
            return True

        if not self._workload_service.is_running():
            logger.info("Authentik workload is not ready for OAuth reconciliation")
            return True

        api = self._authentik_api
        if not api.is_service_available:
            logger.info("Authentik API is not available yet for OAuth reconciliation")
            return True

        relations = self.model.relations[OAUTH_RELATION_NAME]

        is_broken_event = (
            isinstance(event, ops.RelationBrokenEvent)
            and event.relation.name == OAUTH_RELATION_NAME
        )
        broken_relation_id = event.relation.id if is_broken_event and event else None

        active_relation_ids = {
            relation.id for relation in relations if relation.id != broken_relation_id
        }

        reconciler = OauthReconciler(self, api)
        reconciler.reconcile(active_relation_ids)
        return True

    def _get_or_generate_credentials(self, relation: ops.Relation) -> tuple[str, str, bool]:
        """Get existing OIDC credentials or generate new ones in memory.

        Args:
            relation: The Juju relation object.

        Returns:
            A tuple of (client_id, client_secret, is_new).
        """
        client_id = relation.data[self.app].get("client_id")
        client_secret = None
        if client_id:
            client_secret_id = relation.data[self.app].get("client_secret_id")
            if client_secret_id:
                try:
                    secret_obj = self.model.get_secret(id=client_secret_id)
                    client_secret = secret_obj.get_content(refresh=True).get(CLIENT_SECRET_FIELD)
                except ops.SecretNotFoundError:
                    logger.warning(
                        "Client secret %s no longer exists; regenerating", client_secret_id
                    )
                except ops.ModelError as e:
                    raise AuthentikTransientError(
                        f"Failed to read client secret {client_secret_id!r}: {e}"
                    ) from e

        is_new = False
        if not client_id or not client_secret:
            # Generate new secure credentials in memory (do not write to databag yet)
            client_id = token_urlsafe(16)
            client_secret = token_urlsafe(32)
            is_new = True

        return client_id, client_secret, is_new

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
            # Re-run reconciliation so the server-info relation (whose publication
            # is gated on API readiness) is populated as soon as the API recovers,
            # instead of waiting for the next update-status tick.
            self._on_holistic_handler(event)

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

        for conflict in self._config.get_config_conflicts():
            event.add_status(ops.BlockedStatus(conflict))

        self._collect_integrations_status(event)

        if not self._secrets.is_ready():
            event.add_status(ops.WaitingStatus("waiting for secrets"))

        if not self.model.relations[CLUSTER_RELATION]:
            event.add_status(ops.BlockedStatus("missing authentik-worker relation"))

        if can_connect:
            self._collect_health_status(event)

        event.add_status(self.resources_patch.get_status())
        event.add_status(ops.ActiveStatus())

    def _collect_integrations_status(self, event: ops.CollectStatusEvent) -> None:
        """Collect status for integrations (database and traefik-route)."""
        if not database_integration_exists(self):
            event.add_status(ops.BlockedStatus("missing pg-database relation"))

        if database_integration_exists(self) and not database_resource_is_created(self):
            event.add_status(ops.WaitingStatus("waiting for database creation"))

        if not traefik_route_integration_exists(self):
            event.add_status(ops.BlockedStatus("missing traefik-route relation"))

        if traefik_route_integration_exists(self) and not traefik_route_is_ready(self):
            event.add_status(ops.WaitingStatus("waiting for ingress to be ready"))

        if traefik_route_is_ready(self) and not traefik_route_is_secure(self):
            event.add_status(ops.BlockedStatus("Requires a secure (HTTPS) public ingress."))

    def _collect_health_status(self, event: ops.CollectStatusEvent) -> None:
        """Collect status from workload health check."""
        try:
            self._workload_service.check_health()
        except ServiceBackoffError:
            event.add_status(
                ops.BlockedStatus(
                    f"failed to start the service, please check the "
                    f"{WORKLOAD_CONTAINER} container logs"
                )
            )
        except DatabaseConnectionError:
            event.add_status(
                ops.BlockedStatus("database connection failed, please check credentials")
            )
        except MigrationPendingError:
            event.add_status(ops.WaitingStatus("running database migrations"))
        except MigrationFailedError as e:
            event.add_status(ops.BlockedStatus(str(e)))
        except WorkloadNotRunningError:
            event.add_status(ops.WaitingStatus("waiting for the service to start"))

    def _on_get_bootstrap_admin_credentials(self, event: ops.ActionEvent) -> None:
        """Handle the get-bootstrap-admin-credentials action."""
        if not self._secrets.is_ready():
            event.fail("Admin credentials are not ready yet.")
            return

        event.set_results({
            "username": "akadmin",
            "password": self._secrets.bootstrap_password,
            "bootstrap-token": self._secrets.bootstrap_token,
            "warning": (
                "These are initial bootstrap credentials generated at deployment time. "
                "If the administrator password was subsequently changed via the web UI or "
                "recovery flows, the password returned here will be stale."
            ),
        })

    def _on_create_recovery_link(self, event: ops.ActionEvent) -> None:
        """Handle the create-recovery-link action."""
        if not self._container.can_connect():
            event.fail("Cannot connect to the workload container.")
            return

        username = event.params.get("username", "akadmin")
        duration = event.params.get("duration", 10)

        try:
            path = self._workload_service.create_recovery_link(username, duration)
            url = urljoin(self._authentik_host, path)
            event.set_results({
                "status": "success",
                "url": url,
                "path": path,
            })
        except Exception as e:
            logger.exception("Failed to create recovery link")
            event.fail(f"Failed to create recovery link: {e}")

    def _resource_reqs_from_config(self) -> ResourceRequirements:
        """Build resource requirements from charm config."""
        limits = {"cpu": self.model.config.get("cpu"), "memory": self.model.config.get("memory")}
        requests = {"cpu": "500m", "memory": "1Gi"}
        return adjust_resource_requirements(limits, requests, adhere_to_requests=True)


if __name__ == "__main__":  # pragma: nocover
    ops.main(AuthentikServerCharm)
