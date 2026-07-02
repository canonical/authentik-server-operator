#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm the Authentik server application."""

import logging
import re
import subprocess
from secrets import token_urlsafe

import ops
from charms.authentik_server.v0.authentik_cluster import AuthentikClusterProvider
from charms.authentik_server.v0.authentik_server_info import AuthentikServerInfoProvider
from charms.certificate_transfer_interface.v1.certificate_transfer import (
    CertificateTransferRequires,
)
from charms.data_platform_libs.v0.data_interfaces import DatabaseRequires
from charms.grafana_k8s.v0.grafana_dashboard import GrafanaDashboardProvider
from charms.hydra.v0.oauth import (
    CLIENT_SECRET_FIELD,
    OAUTH_PROVIDER_JSON_SCHEMA,
    OAuthProvider,
    _dump_data,
)
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

from authentik_api import AuthentikAPI
from configs import CharmConfig
from constants import (
    CERTIFICATE_TRANSFER_INTEGRATION_NAME,
    CLUSTER_RELATION,
    DATABASE_RELATION,
    GRAFANA_RELATION_NAME,
    HTTP_PORT,
    INGRESS_RELATION,
    LOCAL_CERTIFICATES_PATH,
    LOCAL_CHARM_CERTIFICATES_FILE,
    LOCAL_CHARM_CERTIFICATES_PATH,
    LOGGING_RELATION_NAME,
    OAUTH_RELATION_NAME,
    PEBBLE_READY_CHECK_NAME,
    PEER_RELATION,
    PROMETHEUS_RELATION_NAME,
    SERVER_INFO_RELATION,
    TRACING_RELATION_NAME,
    WORKLOAD_CONTAINER,
    WORKLOAD_SERVICE,
)
from exceptions import CharmError, PebbleError
from integrations import (
    DatabaseConfig,
    IngressData,
    TLSCertificates,
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
        self.oauth_provider = OAuthProvider(self, relation_name=OAUTH_RELATION_NAME)

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
        self.certificate_transfer_requirer = CertificateTransferRequires(
            self, CERTIFICATE_TRANSFER_INTEGRATION_NAME
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
        self._current_event = event
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
            self._ensure_server_info_relation,
            self._ensure_tls,
            self._ensure_oauth_relation,
        ]:
            try:
                can_plan = can_plan and f()
            except CharmError:
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

    def _ensure_secrets(self) -> bool:
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

    def _ensure_cluster_relation(self) -> bool:
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
            )
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

    def _ensure_tls(self) -> bool:
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

    def _ensure_oauth_relation(self) -> bool:
        """Ensure active oauth relations are registered in Authentik API and orphans deleted."""
        if not self.unit.is_leader():
            return True

        api = AuthentikAPI(self._secrets.bootstrap_token)
        if not api.is_service_available():
            logger.info("Authentik API service is not available yet")
            return True

        relations = self.model.relations[OAUTH_RELATION_NAME]

        current_event = getattr(self, "_current_event", None)
        is_broken_event = (
            isinstance(current_event, ops.RelationBrokenEvent)
            and current_event.relation.name == OAUTH_RELATION_NAME
        )
        broken_relation_id = current_event.relation.id if is_broken_event else None

        active_relations = []
        for relation in relations:
            if relation.id == broken_relation_id:
                logger.info("Relation %s is broken, skipping registration", relation.id)
                continue
            active_relations.append(relation)

        if active_relations:
            # Retrieve authorization flow dynamically
            authorization_flow = api.get_authorization_flow_uuid()
            if not authorization_flow:
                logger.error("Failed to retrieve explicit consent authorization flow UUID")
                return False

            for relation in active_relations:
                self._sync_oauth_relation(relation, api, authorization_flow)

        # Garbage collect / delete orphans (Authentik providers/applications whose Juju relations are gone)
        active_relation_ids = {r.id for r in active_relations}
        self._garbage_collect_oauth_relations(api, active_relation_ids)

        return True

    def _sync_oauth_relation(
        self,
        relation: ops.Relation,
        api: AuthentikAPI,
        authorization_flow: str,
    ) -> None:
        """Sync a single Juju oauth relation with the Authentik REST API.

        Args:
            relation: The Juju relation object.
            api: The AuthentikAPI client instance.
            authorization_flow: The consent flow UUID.
        """
        if not relation.app:
            logger.info("Remote application is not ready for relation %s", relation.id)
            return

        # Extract dynamic scopes from relation data, falling back to "openid email profile"
        scope_str = relation.data[relation.app].get("scope") or "openid email profile"
        scopes = sorted({s.strip().lower() for s in scope_str.split() if s.strip()})

        # Determine OIDC client slug and populate standard provider endpoints immediately
        clean_app_name = self._clean_slug(relation.app.name)
        slug = f"{clean_app_name}-{relation.id}"

        host = self._authentik_host.rstrip("/")
        provider_info = {
            "issuer_url": f"{host}/application/o/{slug}/",
            "authorization_endpoint": f"{host}/application/o/authorize/",
            "token_endpoint": f"{host}/application/o/token/",
            "introspection_endpoint": f"{host}/application/o/introspect/",
            "userinfo_endpoint": f"{host}/application/o/userinfo/",
            "jwks_endpoint": f"{host}/application/o/{slug}/jwks/",
            "scope": " ".join(scopes),
        }
        relation.data[self.app].update(_dump_data(provider_info, OAUTH_PROVIDER_JSON_SCHEMA))

        requirer_data = relation.data[relation.app]
        redirect_uri = requirer_data.get("redirect_uri")
        if not redirect_uri:
            logger.info("Relation %s has no redirect_uri yet, waiting...", relation.id)
            return

        client_id, client_secret = self._get_or_generate_credentials(relation)

        # Retrieve matching property mappings dynamically for the requested scopes
        property_mappings = api.get_property_mappings(scopes)

        # Sync Provider and Application on Authentik via API and get slug
        actual_slug = self._sync_authentik_objects(
            relation=relation,
            api=api,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            authorization_flow=authorization_flow,
            property_mappings=property_mappings,
        )
        if not actual_slug:
            return

    def _get_or_generate_credentials(self, relation: ops.Relation) -> tuple[str, str]:
        """Load or generate OIDC client credentials for a relation.

        Args:
            relation: The Juju relation object.

        Returns:
            A tuple of (client_id, client_secret).
        """
        client_id = relation.data[self.app].get("client_id")
        client_secret = None
        if client_id:
            client_secret_id = relation.data[self.app].get("client_secret_id")
            if client_secret_id:
                try:
                    secret_obj = self.oauth_provider.get_client_secret(client_secret_id)
                    client_secret = secret_obj.get_content()[CLIENT_SECRET_FIELD]
                except Exception as e:
                    logger.warning("Failed to read existing secret %s: %s", client_secret_id, e)

        if not client_id or not client_secret:
            # Generate new secure credentials
            client_id = token_urlsafe(16)
            client_secret = token_urlsafe(32)
            self.oauth_provider.set_client_credentials_in_relation_data(
                relation.id, client_id, client_secret
            )
            logger.info("Generated new client credentials for relation %s", relation.id)

        return client_id, client_secret

    def _sync_authentik_objects(
        self,
        relation: ops.Relation,
        api: AuthentikAPI,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        authorization_flow: str,
        property_mappings: list[str],
    ) -> str | None:
        """Create or update provider and application in Authentik.

        Args:
            relation: The Juju relation.
            api: The AuthentikAPI client.
            client_id: The OIDC client ID.
            client_secret: The OIDC client secret.
            redirect_uri: The redirect URI.
            authorization_flow: Flow UUID.
            property_mappings: Property mappings list.

        Returns:
            The application slug if successful, otherwise None.
        """
        clean_app_name = self._clean_slug(relation.app.name)
        slug = f"{clean_app_name}-{relation.id}"
        name = f"{relation.app.name} (Relation {relation.id})"

        app_data = api.get_application(slug)
        if not app_data:
            provider_pk = api.create_oauth_provider(
                name=name,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uris=redirect_uri,
                authorization_flow=authorization_flow,
                property_mappings=property_mappings,
            )
            if provider_pk is None:
                logger.error("Failed to create OAuth provider %s", name)
                return None

            if not api.create_application(name=name, slug=slug, provider_pk=provider_pk):
                logger.error("Failed to create application %s with provider %s", name, provider_pk)
                return None

            logger.info("Successfully created application %s and OAuth provider", name)
        else:
            provider_pk = app_data.get("provider")
            if provider_pk:
                api.update_oauth_provider(
                    provider_pk=provider_pk,
                    name=name,
                    client_id=client_id,
                    client_secret=client_secret,
                    redirect_uris=redirect_uri,
                    authorization_flow=authorization_flow,
                    property_mappings=property_mappings,
                )
            api.update_application(slug=slug, name=name, provider_pk=provider_pk)
            logger.info("Successfully updated application %s and OAuth provider", name)

        return slug

    def _garbage_collect_oauth_relations(
        self, api: AuthentikAPI, active_relation_ids: set[int]
    ) -> None:
        """Garbage-collect orphan Authentik applications and providers.

        Args:
            api: The AuthentikAPI client instance.
            active_relation_ids: Set of active relation IDs to keep.
        """
        all_apps = api.list_applications()
        for app in all_apps:
            app_slug = app.get("slug", "")
            # We only delete apps created by this charm. They match our slug format: {clean_app_name}-{relation_id}
            # We can parse the relation ID from the end of the slug and check if it's our relation.
            match = re.match(r"^(.*)-(\d+)$", app_slug)
            if match:
                slug_relation_id = int(match.group(2))
                if slug_relation_id not in active_relation_ids:
                    logger.info(
                        "Deleting orphan Authentik application and provider for relation %s",
                        slug_relation_id,
                    )
                    provider_pk = app.get("provider")
                    if provider_pk:
                        api.delete_oauth_provider(provider_pk)
                    api.delete_application(app_slug)

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
