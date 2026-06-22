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

    def test_to_env_vars_defaults(self, minimal_config: dict) -> None:
        config = CharmConfig(minimal_config)
        env = config.to_env_vars()

        assert env["AUTHENTIK_LOG_LEVEL"] == "info"
        assert env["HTTP_PROXY"] == ""
        assert env["HTTPS_PROXY"] == ""
        assert env["NO_PROXY"] == ""
        assert env["AUTHENTIK_WEB__WORKERS"] == "2"

    def test_get_missing_config_keys(self, minimal_config: dict) -> None:
        config = CharmConfig(minimal_config)
        assert config.get_missing_config_keys() == []
