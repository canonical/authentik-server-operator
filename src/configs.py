# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm configuration wrapper."""

from ops import ConfigData

from env_vars import EnvVars


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
            "HTTP_PROXY": self._config.get("http_proxy") or "",
            "HTTPS_PROXY": self._config.get("https_proxy") or "",
            "NO_PROXY": self._config.get("no_proxy") or "",
            "AUTHENTIK_WEB__WORKERS": str(self._config.get("web_workers", 2)),
        }

    def get_missing_config_keys(self) -> list:
        """Return a list of required config keys that are missing or empty."""
        return []
