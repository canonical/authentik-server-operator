# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Default environment variables and EnvVarConvertible protocol."""

from typing import Mapping, Protocol, TypeAlias, Union

EnvVars: TypeAlias = Mapping[str, Union[str, bool]]

DEFAULT_SERVER_ENV: dict[str, str | bool] = {
    "AUTHENTIK_ERROR_REPORTING__ENABLED": "false",
    "AUTHENTIK_LOG_LEVEL": "info",
    # PostgreSQL — populated by DatabaseIntegration
    "AUTHENTIK_POSTGRESQL__HOST": "",
    "AUTHENTIK_POSTGRESQL__PORT": "",
    "AUTHENTIK_POSTGRESQL__USER": "",
    "AUTHENTIK_POSTGRESQL__PASSWORD": "",
    "AUTHENTIK_POSTGRESQL__NAME": "",
    # Server secrets — populated by SecretsIntegration
    "AUTHENTIK_SECRET_KEY": "",
    "AUTHENTIK_BOOTSTRAP_TOKEN": "",
    "AUTHENTIK_BOOTSTRAP_PASSWORD": "",
}


class EnvVarConvertible(Protocol):
    """Interface for objects that contribute environment variables to the Pebble layer."""

    def to_env_vars(self) -> EnvVars:
        """Return a mapping of environment variable names to values."""
        ...
