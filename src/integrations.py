# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Wrappers for charm relation data, implementing EnvVarConvertible."""

import logging
from dataclasses import dataclass

from charms.data_platform_libs.v0.data_interfaces import DatabaseRequires
from charms.tempo_coordinator_k8s.v0.tracing import TracingEndpointRequirer

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


@dataclass(frozen=True)
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
