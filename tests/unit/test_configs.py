# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for CharmConfig."""

import pytest

from configs import CharmConfig


class TestCharmConfig:
    @pytest.fixture
    def full_config(self) -> dict:
        return {
            "log_level": "debug",
            "http_proxy": "http://proxy:6666",
            "https_proxy": "http://proxy:6666",
            "no_proxy": "localhost",
            "web_workers": 4,
            "postgresql_disable_server_side_cursors": True,
            "postgresql_conn_health_checks": True,
            "postgresql_conn_max_age": 120,
        }

    @pytest.fixture
    def minimal_config(self) -> dict:
        return {
            "log_level": "info",
        }

    def test_to_env_vars(self, full_config: dict) -> None:
        config = CharmConfig(full_config)
        env = config.to_env_vars()

        assert env["AUTHENTIK_LOG_LEVEL"] == "debug"
        assert env["HTTP_PROXY"] == "http://proxy:6666"
        assert env["HTTPS_PROXY"] == "http://proxy:6666"
        assert env["NO_PROXY"] == "localhost"
        assert env["AUTHENTIK_WEB__WORKERS"] == "4"
        assert env["AUTHENTIK_POSTGRESQL__DISABLE_SERVER_SIDE_CURSORS"] == "true"
        assert env["AUTHENTIK_POSTGRESQL__CONN_HEALTH_CHECKS"] == "true"
        assert env["AUTHENTIK_POSTGRESQL__CONN_MAX_AGE"] == "120"

    def test_to_env_vars_defaults(self, minimal_config: dict) -> None:
        config = CharmConfig(minimal_config)
        env = config.to_env_vars()

        assert env["AUTHENTIK_LOG_LEVEL"] == "info"
        assert env["HTTP_PROXY"] == ""
        assert env["HTTPS_PROXY"] == ""
        assert env["NO_PROXY"] == ""
        assert env["AUTHENTIK_WEB__WORKERS"] == "2"
        assert env["AUTHENTIK_POSTGRESQL__DISABLE_SERVER_SIDE_CURSORS"] == "false"
        assert env["AUTHENTIK_POSTGRESQL__CONN_HEALTH_CHECKS"] == "false"
        assert env["AUTHENTIK_POSTGRESQL__CONN_MAX_AGE"] == "0"

    def test_get_missing_config_keys(self, minimal_config: dict) -> None:
        config = CharmConfig(minimal_config)
        assert config.get_missing_config_keys() == []

    def test_use_pgbouncer_value_follows_config(self, minimal_config: dict) -> None:
        assert CharmConfig(minimal_config).use_pgbouncer_value == "false"
        cfg = {**minimal_config, "postgresql_use_pgbouncer": True}
        assert CharmConfig(cfg).use_pgbouncer_value == "true"

    def test_no_conflict_when_pgbouncer_disabled(self, minimal_config: dict) -> None:
        assert CharmConfig(minimal_config).get_config_conflicts() == []

    def test_conflict_when_pgbouncer_without_disabled_cursors(self, minimal_config: dict) -> None:
        cfg = {
            **minimal_config,
            "postgresql_use_pgbouncer": True,
            "postgresql_disable_server_side_cursors": False,
        }
        conflicts = CharmConfig(cfg).get_config_conflicts()

        assert len(conflicts) == 1
        assert "postgresql_use_pgbouncer=true" in conflicts[0]

    def test_no_conflict_when_pgbouncer_with_disabled_cursors(self, minimal_config: dict) -> None:
        cfg = {
            **minimal_config,
            "postgresql_use_pgbouncer": True,
            "postgresql_disable_server_side_cursors": True,
        }
        assert CharmConfig(cfg).get_config_conflicts() == []
