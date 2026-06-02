# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm configuration wrapper."""

from env_vars import EnvVars
from ops import ConfigData


class CharmConfig:
    """Wraps charm config and exposes it as env vars.

    Args:
        config: The ops ConfigData object from the charm.
    """

    def __init__(self, config: ConfigData) -> None:
        self._config = config

    def to_env_vars(self) -> EnvVars:
        """Return charm-config-derived environment variables."""
        return {
            "AUTHENTIK_LOG_LEVEL": self._config.get("log_level", "info"),
        }
