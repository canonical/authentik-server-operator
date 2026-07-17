# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Default environment variables and EnvVarConvertible protocol."""

from typing import Mapping, Protocol, TypeAlias, Union

EnvVars: TypeAlias = Mapping[str, Union[str, bool]]

DEFAULT_SERVER_ENV: dict[str, str | bool] = {
    "AUTHENTIK_ERROR_REPORTING__ENABLED": "false",
    "AUTHENTIK_LOG_LEVEL": "info",
    # The ak lifecycle script calls `python` which only exists in the venv.
    # The rock's pebble service definition sets this PATH but Juju replaces that
    # layer entirely, so the charm must redeclare it here.
    "PATH": "/lifecycle:/ak-root/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    # Prevent Python from writing .pyc files
    "PYTHONDONTWRITEBYTECODE": "1",
    # Ensure stdout/stderr are unbuffered to stream logs in real-time
    "PYTHONUNBUFFERED": "1",
    # PYTHONPATH pointing to / where authentik is located
    "PYTHONPATH": "/",
    # Virtualenv path indicators
    "VIRTUAL_ENV": "/ak-root/.venv",
    "VENV_PATH": "/ak-root/.venv",
    # Signal to Authentik that it is running in a container
    "AK_RUNNING_IN_CONTAINER": "true",
    # Enable FIPS mode in Go if supported
    "GOFIPS": "1",
    # PostgreSQL — populated by DatabaseConfig
    "AUTHENTIK_POSTGRESQL__HOST": "",
    "AUTHENTIK_POSTGRESQL__PORT": "",
    "AUTHENTIK_POSTGRESQL__USER": "",
    "AUTHENTIK_POSTGRESQL__PASSWORD": "",
    "AUTHENTIK_POSTGRESQL__NAME": "",
    "AUTHENTIK_POSTGRESQL__DISABLE_SERVER_SIDE_CURSORS": "false",
    "AUTHENTIK_POSTGRESQL__CONN_HEALTH_CHECKS": "false",
    "AUTHENTIK_POSTGRESQL__CONN_MAX_AGE": "0",
    # Server secrets — populated by Secrets
    "AUTHENTIK_SECRET_KEY": "",
    "AUTHENTIK_BOOTSTRAP_TOKEN": "",
    "AUTHENTIK_BOOTSTRAP_PASSWORD": "",
    # Update check — always disabled in charm-managed deployments
    "AUTHENTIK_DISABLE_UPDATE_CHECK": "true",
    # Proxy
    "HTTP_PROXY": "",
    "HTTPS_PROXY": "",
    "NO_PROXY": "",
    # Web workers — populated by CharmConfig
    "AUTHENTIK_WEB__WORKERS": "2",
    # Web path — populated at runtime from ingress URL
    "AUTHENTIK_WEB__PATH": "/",
    # Base URL — populated at runtime from traefik-route URL
    "AUTHENTIK_OPTS__BASE_URL": "",
}


class EnvVarConvertible(Protocol):
    """Interface for objects that contribute environment variables to the Pebble layer."""

    def to_env_vars(self) -> EnvVars:
        """Return a mapping of environment variable names to values."""
        ...
