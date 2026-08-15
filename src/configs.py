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
            # Database pooling tunings
            "AUTHENTIK_POSTGRESQL__DISABLE_SERVER_SIDE_CURSORS": str(
                self._config.get("postgresql_disable_server_side_cursors", False)
            ).lower(),
            "AUTHENTIK_POSTGRESQL__CONN_HEALTH_CHECKS": str(
                self._config.get("postgresql_conn_health_checks", False)
            ).lower(),
            "AUTHENTIK_POSTGRESQL__CONN_MAX_AGE": str(
                self._config.get("postgresql_conn_max_age", 0)
            ),
            "AUTHENTIK_POSTGRESQL__USE_PGBOUNCER": self.use_pgbouncer_value,
        }

    @property
    def use_pgbouncer_value(self) -> str:
        """The pgbouncer declaration as authentik expects it.

        Shared with authentik-worker over the cluster relation, so the worker
        never needs its own copy of this option.
        """
        return str(self._config.get("postgresql_use_pgbouncer", False)).lower()

    def get_missing_config_keys(self) -> list:
        """Return a list of required config keys that are missing or empty."""
        return []

    def get_config_conflicts(self) -> list[str]:
        """Return human-readable descriptions of mutually incompatible config.

        These are combinations authentik accepts but that produce broken
        behaviour, so the charm blocks rather than starting a workload that
        misbehaves in ways the operator did not ask for.
        """
        conflicts = []

        # Under transaction pooling a client is not pinned to one backend
        # between transactions, so a server-side cursor opened on one backend is
        # gone by the time it is read from another. authentik only defaults this
        # off for use_pgbouncer when the setting is absent; the charm always
        # exports it, so an explicit false silently wins and breaks queries.
        if self._config.get("postgresql_use_pgbouncer", False) and not self._config.get(
            "postgresql_disable_server_side_cursors", False
        ):
            conflicts.append(
                "postgresql_use_pgbouncer=true requires "
                "postgresql_disable_server_side_cursors=true: server-side cursors "
                "do not survive transaction pooling"
            )

        return conflicts
