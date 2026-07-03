# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for integration wrapper classes (DatabaseConfig, TracingData)."""

from unittest.mock import MagicMock, create_autospec

import pytest
from charms.data_platform_libs.v0.data_interfaces import DatabaseRequires
from charms.smtp_integrator.v0.smtp import SmtpRequires
from charms.tempo_coordinator_k8s.v0.tracing import TracingEndpointRequirer

from integrations import DatabaseConfig, SmtpData, TracingData


class TestDatabaseConfig:
    @pytest.fixture
    def mocked_requirer(self) -> MagicMock:
        mocked = create_autospec(DatabaseRequires)
        relation = MagicMock(id=1)
        mocked.relations = [relation]
        mocked.fetch_relation_data.return_value = {
            1: {
                "endpoints": "host:5432",
                "username": "user",
                "password": "password",
                "database": "authentik",
            }
        }
        return mocked

    def test_load(self, mocked_requirer: MagicMock) -> None:
        config = DatabaseConfig.load(mocked_requirer)
        assert config.host == "host"
        assert config.port == "5432"
        assert config.user == "user"
        assert config.password == "password"
        assert config.name == "authentik"

    def test_load_empty(self) -> None:
        mocked = create_autospec(DatabaseRequires)
        mocked.relations = []
        config = DatabaseConfig.load(mocked)
        assert config == DatabaseConfig()

    def test_load_no_endpoints(self) -> None:
        mocked = create_autospec(DatabaseRequires)
        relation = MagicMock(id=1)
        mocked.relations = [relation]
        mocked.fetch_relation_data.return_value = {1: {"username": "user"}}
        config = DatabaseConfig.load(mocked)
        assert config == DatabaseConfig()

    def test_to_env_vars(self, mocked_requirer: MagicMock) -> None:
        config = DatabaseConfig.load(mocked_requirer)
        assert config.to_env_vars() == {
            "AUTHENTIK_POSTGRESQL__HOST": "host",
            "AUTHENTIK_POSTGRESQL__PORT": "5432",
            "AUTHENTIK_POSTGRESQL__USER": "user",
            "AUTHENTIK_POSTGRESQL__PASSWORD": "password",
            "AUTHENTIK_POSTGRESQL__NAME": "authentik",
        }

    def test_to_env_vars_empty(self) -> None:
        config = DatabaseConfig()
        assert config.to_env_vars() == {
            "AUTHENTIK_POSTGRESQL__HOST": "",
            "AUTHENTIK_POSTGRESQL__PORT": "",
            "AUTHENTIK_POSTGRESQL__USER": "",
            "AUTHENTIK_POSTGRESQL__PASSWORD": "",
            "AUTHENTIK_POSTGRESQL__NAME": "",
        }


class TestTracingData:
    @pytest.fixture
    def mocked_requirer(self) -> MagicMock:
        mocked = create_autospec(TracingEndpointRequirer)
        mocked.is_ready.return_value = True
        mocked.get_endpoint.return_value = "http://tempo:4318"
        return mocked

    def test_load(self, mocked_requirer: MagicMock) -> None:
        data = TracingData.load(mocked_requirer)
        assert data.is_ready is True
        assert data.endpoint == "http://tempo:4318"

    def test_load_not_ready(self) -> None:
        mocked = create_autospec(TracingEndpointRequirer)
        mocked.is_ready.return_value = False
        data = TracingData.load(mocked)
        assert data == TracingData()

    def test_to_env_vars_ready(self) -> None:
        data = TracingData(is_ready=True, endpoint="http://tempo:4318")
        assert data.to_env_vars() == {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://tempo:4318"}

    def test_to_env_vars_not_ready(self) -> None:
        data = TracingData(is_ready=False, endpoint="")
        assert data.to_env_vars() == {}

    def test_to_env_vars_ready_no_endpoint(self) -> None:
        data = TracingData(is_ready=True, endpoint="")
        assert data.to_env_vars() == {"OTEL_EXPORTER_OTLP_ENDPOINT": ""}


class TestSmtpData:
    @pytest.fixture
    def mocked_requirer(self) -> MagicMock:
        mocked = create_autospec(SmtpRequires)
        return mocked

    def test_load_empty(self, mocked_requirer: MagicMock) -> None:
        mocked_requirer.get_relation_data.return_value = None
        data = SmtpData.load(mocked_requirer)
        assert data == SmtpData()
        assert data.to_env_vars() == {}

    def test_load_exception(self, mocked_requirer: MagicMock) -> None:
        mocked_requirer.get_relation_data.side_effect = Exception("Some error")
        data = SmtpData.load(mocked_requirer)
        assert data == SmtpData()
        assert data.to_env_vars() == {}

    def test_load_and_to_env_vars_tls(self, mocked_requirer: MagicMock) -> None:
        from charms.smtp_integrator.v0.smtp import AuthType, SmtpRelationData, TransportSecurity

        relation_data = SmtpRelationData(
            host="smtp.example.com",
            port=587,
            user="user",
            password="password",
            auth_type=AuthType.PLAIN,
            transport_security=TransportSecurity.STARTTLS,
            smtp_sender="sender@example.com",
        )
        mocked_requirer.get_relation_data.return_value = relation_data
        data = SmtpData.load(mocked_requirer)
        assert data.host == "smtp.example.com"
        assert data.port == "587"
        assert data.username == "user"
        assert data.password == "password"
        assert data.use_tls is True
        assert data.use_ssl is False
        assert data.from_address == "sender@example.com"

        assert data.to_env_vars() == {
            "AUTHENTIK_EMAIL__HOST": "smtp.example.com",
            "AUTHENTIK_EMAIL__PORT": "587",
            "AUTHENTIK_EMAIL__USERNAME": "user",
            "AUTHENTIK_EMAIL__PASSWORD": "password",
            "AUTHENTIK_EMAIL__USE_TLS": "true",
            "AUTHENTIK_EMAIL__USE_SSL": "false",
            "AUTHENTIK_EMAIL__FROM": "sender@example.com",
        }

    def test_load_and_to_env_vars_ssl(self, mocked_requirer: MagicMock) -> None:
        from charms.smtp_integrator.v0.smtp import AuthType, SmtpRelationData, TransportSecurity

        relation_data = SmtpRelationData(
            host="smtp.example.com",
            port=465,
            user="user",
            password="password",
            auth_type=AuthType.PLAIN,
            transport_security=TransportSecurity.TLS,
        )
        mocked_requirer.get_relation_data.return_value = relation_data
        data = SmtpData.load(mocked_requirer)
        assert data.host == "smtp.example.com"
        assert data.port == "465"
        assert data.username == "user"
        assert data.password == "password"
        assert data.use_tls is False
        assert data.use_ssl is True
        assert data.from_address == ""

        assert data.to_env_vars() == {
            "AUTHENTIK_EMAIL__HOST": "smtp.example.com",
            "AUTHENTIK_EMAIL__PORT": "465",
            "AUTHENTIK_EMAIL__USERNAME": "user",
            "AUTHENTIK_EMAIL__PASSWORD": "password",
            "AUTHENTIK_EMAIL__USE_TLS": "false",
            "AUTHENTIK_EMAIL__USE_SSL": "true",
        }
