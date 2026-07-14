# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Wrappers for charm relation data, implementing EnvVarConvertible."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import ops
from charms.certificate_transfer_interface.v1.certificate_transfer import (
    CertificateTransferRequires,
)
from charms.data_platform_libs.v0.data_interfaces import DatabaseRequires
from charms.smtp_integrator.v0.smtp import SmtpRequires, TransportSecurity
from charms.tempo_coordinator_k8s.v0.tracing import TracingEndpointRequirer
from charms.traefik_k8s.v0.traefik_route import TraefikRouteRequirer
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel

from constants import (
    CERTIFICATE_TRANSFER_INTEGRATION_NAME,
    HTTP_PORT,
    PEER_RELATION,
)
from env_vars import EnvVars

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    """The data source from the database integration."""

    host: str = ""
    port: str = ""
    user: str = ""
    password: str = ""
    name: str = ""

    def to_env_vars(self) -> EnvVars:
        """Return PostgreSQL connection environment variables."""
        return {
            "AUTHENTIK_POSTGRESQL__HOST": self.host,
            "AUTHENTIK_POSTGRESQL__PORT": self.port,
            "AUTHENTIK_POSTGRESQL__USER": self.user,
            "AUTHENTIK_POSTGRESQL__PASSWORD": self.password,
            "AUTHENTIK_POSTGRESQL__NAME": self.name,
        }

    @classmethod
    def load(cls, requirer: DatabaseRequires) -> "DatabaseConfig":
        """Load database config from the relation."""
        if not (relations := requirer.relations):
            return cls()
        integration_data = requirer.fetch_relation_data()[relations[0].id]
        if "endpoints" not in integration_data:
            return cls()
        host, port = integration_data["endpoints"].split(":")
        return cls(
            host=host,
            port=port,
            user=integration_data.get("username", ""),
            password=integration_data.get("password", ""),
            name=integration_data.get("database", ""),
        )


@dataclass(frozen=True, slots=True)
class TracingData:
    """The data source from the tracing integration."""

    is_ready: bool = False
    endpoint: str = ""

    def to_env_vars(self) -> EnvVars:
        """Return tracing environment variables."""
        if not self.is_ready:
            return {}
        return {"OTEL_EXPORTER_OTLP_ENDPOINT": self.endpoint}

    @classmethod
    def load(cls, requirer: TracingEndpointRequirer) -> "TracingData":
        """Load tracing data from the relation."""
        if not requirer.is_ready():
            return cls()
        endpoint = requirer.get_endpoint("otlp_http")
        return cls(is_ready=True, endpoint=endpoint or "")


@dataclass(frozen=True, slots=True)
class TLSCertificates:
    """The data source from the certificate transfer integration."""

    ca_bundle: str

    @classmethod
    def load(cls, requirer: CertificateTransferRequires) -> "TLSCertificates":
        """Fetch the CA certificates from all receive-ca-cert integrations.

        Args:
            requirer: The CertificateTransferRequires integration.

        Returns:
            The loaded TLSCertificates.
        """
        # deal with v1 relations
        ca_certs = requirer.get_all_certificates()

        # deal with v0 relations
        cert_transfer_integrations = requirer.charm.model.relations[
            CERTIFICATE_TRANSFER_INTEGRATION_NAME
        ]

        for integration in cert_transfer_integrations:
            ca = {
                integration.data[unit]["ca"]
                for unit in integration.units
                if "ca" in integration.data.get(unit, {})
            }
            ca_certs.update(ca)

        ca_bundle = "\n".join(sorted(ca_certs))

        return cls(ca_bundle=ca_bundle)


@dataclass(frozen=True, slots=True)
class SmtpData:
    """The data source from the SMTP integration."""

    host: str = ""
    port: str = ""
    username: str = ""
    password: str = ""
    use_tls: bool = False
    use_ssl: bool = False
    from_address: str = ""

    def to_env_vars(self) -> EnvVars:
        """Return SMTP environment variables."""
        if not self.host:
            return {}
        env_vars: dict[str, str | bool] = {
            "AUTHENTIK_EMAIL__HOST": self.host,
            "AUTHENTIK_EMAIL__PORT": self.port,
            "AUTHENTIK_EMAIL__USERNAME": self.username,
            "AUTHENTIK_EMAIL__PASSWORD": self.password,
            "AUTHENTIK_EMAIL__USE_TLS": "true" if self.use_tls else "false",
            "AUTHENTIK_EMAIL__USE_SSL": "true" if self.use_ssl else "false",
        }
        if self.from_address:
            env_vars["AUTHENTIK_EMAIL__FROM"] = self.from_address
        return env_vars

    @classmethod
    def load(cls, requirer: SmtpRequires) -> "SmtpData":
        """Load SMTP config from the relation."""
        try:
            relation_data = requirer.get_relation_data()
        except Exception as e:
            logger.error("Failed to load SMTP relation data: %s", e)
            return cls()
        if not relation_data:
            return cls()

        use_tls = False
        use_ssl = False
        transport_sec = relation_data.transport_security
        if transport_sec == TransportSecurity.STARTTLS or transport_sec == "starttls":
            use_tls = True
        elif transport_sec == TransportSecurity.TLS or transport_sec == "tls":
            use_ssl = True

        return cls(
            host=relation_data.host or "",
            port=str(relation_data.port) if relation_data.port is not None else "",
            username=relation_data.user or "",
            password=relation_data.password or "",
            use_tls=use_tls,
            use_ssl=use_ssl,
            from_address=relation_data.smtp_sender or "",
        )


class PeerData:
    """Access peer relation app-level data.

    Only app-level data is used; unit-level data is intentionally left empty.
    The leader unit is the sole writer; all units read.
    """

    def __init__(self, model: "ops.Model") -> None:
        self._model = model
        self._app = model.app

    def __getitem__(self, key: str) -> dict[str, Any]:
        """Get a dictionary value from the peer relation data."""
        if not (peers := self._model.get_relation(PEER_RELATION)):
            return {}

        value = peers.data[self._app].get(key)
        if not value:
            return {}
        try:
            return json.loads(value)
        except Exception as e:
            logger.warning("Failed to parse peer relation key %s: %s", key, e)
            return {}

    def __setitem__(self, key: str, value: Any) -> None:
        """Set a value in the peer relation data."""
        if not (peers := self._model.get_relation(PEER_RELATION)):
            return

        peers.data[self._app][key] = json.dumps(value)

    def pop(self, key: str) -> dict[str, Any]:
        """Remove and return a value from the peer relation data."""
        if not (peers := self._model.get_relation(PEER_RELATION)):
            return {}

        data = peers.data[self._app].pop(key, None)
        if not data:
            return {}
        try:
            return json.loads(data)
        except Exception as e:
            logger.warning("Failed to parse popped key %s: %s", key, e)
            return {}

    def get_string(self, key: str) -> str | None:
        """Get a string value from the peer relation data."""
        if not (peers := self._model.get_relation(PEER_RELATION)):
            return None
        return peers.data[self._app].get(key)

    def set_string(self, key: str, value: str) -> None:
        """Set a string value in the peer relation data."""
        if not (peers := self._model.get_relation(PEER_RELATION)):
            return
        peers.data[self._app][key] = value


class TraefikRouteIntegration(BaseModel):
    """The data source from the Traefik route integration."""

    external_host: str = ""
    scheme: str = ""

    @property
    def secure(self) -> bool:
        """Whether the scheme is HTTPS."""
        return self.scheme == "https"

    def to_env_vars(self) -> EnvVars:
        """Return Traefik Route environment variables."""
        if not self.external_host:
            return {}
        return {"AUTHENTIK_OPTS__BASE_URL": self.base_url}

    @property
    def base_url(self) -> str:
        """The base URL for this route."""
        if not self.external_host:
            return ""
        scheme = self.scheme or "http"
        return f"{scheme}://{self.external_host}"

    @classmethod
    def load(cls, requirer: Optional[TraefikRouteRequirer]) -> "TraefikRouteIntegration":
        """Load Traefik Route data from the relation."""
        if not requirer or not requirer.is_ready():
            return cls()
        return cls(
            external_host=requirer.external_host,
            scheme=requirer.scheme,
        )

    def render_config(self, app_name: str, model_name: str) -> dict:
        """Render Traefik route configuration dictionary from jinja template."""
        template_dir = Path(__file__).parent.parent / "templates"
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template("traefik-route.json.j2")

        identifier = f"{model_name}-{app_name}"

        rendered = template.render(
            identifier=identifier,
            external_host=self.external_host,
            app=app_name,
            model=model_name,
            port=HTTP_PORT,
        )

        return json.loads(rendered)
