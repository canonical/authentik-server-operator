# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Shared fixtures and state factory for Authentik Server unit tests."""

import json
from typing import Any
from unittest.mock import MagicMock, PropertyMock

import pytest
from ops import testing
from pytest_mock import MockerFixture

from charm import AuthentikServerCharm
from constants import WORKLOAD_CONTAINER


# ---------------------------------------------------------------------------
# create_state() — module-level factory (NOT a fixture)
# ---------------------------------------------------------------------------
def create_state(
    leader: bool = True,
    secrets: list | None = None,
    relations: list | None = None,
    containers: list | None = None,
    config: dict | None = None,
    can_connect: bool = True,
    workload_version: str = "2025.6.1",
) -> testing.State:
    """Build a complete State with sensible defaults for authentik-server tests."""
    if secrets is None:
        secrets = []
    if relations is None:
        relations = []
    if containers is None:
        containers = [
            testing.Container(
                WORKLOAD_CONTAINER,
                can_connect=can_connect,
                execs={
                    testing.Exec(
                        command_prefix=[
                            "/ak-root/.venv/bin/python",
                            "-c",
                            "from authentik import VERSION; print(VERSION)",
                        ],
                        return_code=0,
                        stdout=workload_version,
                    ),
                },
            )
        ]
    if config is None:
        config = {}

    return testing.State(
        leader=leader,
        secrets=secrets,
        containers=containers,
        relations=relations,
        config=config,
        model=testing.Model(name="test-model"),
    )


# ---------------------------------------------------------------------------
# Resource-patch mocks (autouse)
# ---------------------------------------------------------------------------
@pytest.fixture()
def mocked_resource_patch(mocker: MockerFixture) -> MagicMock:
    mocked = mocker.patch(
        "charms.observability_libs.v0.kubernetes_compute_resources_patch.ResourcePatcher",
        autospec=True,
    )
    mocked.return_value.is_failed.return_value = (False, "")
    mocked.return_value.is_in_progress.return_value = False
    return mocked


@pytest.fixture(autouse=True)
def mocked_k8s_resource_patch(mocker: MockerFixture, mocked_resource_patch: MagicMock) -> None:
    mocker.patch.multiple(
        "charm.KubernetesComputeResourcesPatch",
        _namespace="testing",
        _patch=lambda *a, **kw: True,
        is_ready=lambda *a, **kw: True,
    )


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------
@pytest.fixture
def context() -> testing.Context:
    return testing.Context(AuthentikServerCharm)


# ---------------------------------------------------------------------------
# Container fixture (for tests that need a direct reference)
# ---------------------------------------------------------------------------
@pytest.fixture
def container() -> testing.Container:
    return testing.Container(
        WORKLOAD_CONTAINER,
        can_connect=True,
        execs={
            testing.Exec(
                command_prefix=[
                    "/ak-root/.venv/bin/python",
                    "-c",
                    "from authentik import VERSION; print(VERSION)",
                ],
                return_code=0,
                stdout="2025.6.1",
            ),
        },
    )


# ---------------------------------------------------------------------------
# Relation fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def db_relation() -> testing.Relation:
    return testing.Relation(
        endpoint="pg-database",
        interface="postgresql_client",
        remote_app_name="postgresql-k8s",
        remote_app_data={
            "database": "authentik",
            "endpoints": "test-host:5432",
            "username": "test-user",
            "password": "test-pass",
        },
    )


@pytest.fixture
def peer_relation() -> testing.PeerRelation:
    return testing.PeerRelation(
        endpoint="authentik-peers",
        interface="authentik_peers",
    )


@pytest.fixture
def ingress_relation() -> testing.Relation:
    return testing.Relation(
        endpoint="ingress",
        interface="ingress",
        remote_app_name="traefik",
        remote_app_data={
            "ingress": json.dumps({"url": "http://authentik.example.com"}),
        },
    )


@pytest.fixture
def cluster_relation() -> testing.Relation:
    return testing.Relation(
        endpoint="authentik-cluster",
        interface="authentik_cluster",
        remote_app_name="authentik-worker",
    )


@pytest.fixture
def server_info_relation() -> testing.Relation:
    return testing.Relation(
        endpoint="authentik-server-info",
        interface="authentik_server_info",
        remote_app_name="authentik-ldap-outpost",
    )


# ---------------------------------------------------------------------------
# Secret fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def secret_key_secret() -> testing.Secret:
    return testing.Secret(
        tracked_content={"secret-key": "test-secret-key"},
        label="authentik-server-secret-key",
    )


@pytest.fixture
def bootstrap_token_secret() -> testing.Secret:
    return testing.Secret(
        tracked_content={"bootstrap-token": "test-bootstrap-token"},
        label="authentik-server-bootstrap-token",
    )


@pytest.fixture
def bootstrap_password_secret() -> testing.Secret:
    return testing.Secret(
        tracked_content={"bootstrap-password": "test-bootstrap-password"},
        label="authentik-server-bootstrap-password",
    )


# ---------------------------------------------------------------------------
# Observability relation fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def tracing_relation() -> testing.Relation:
    return testing.Relation(
        endpoint="tracing",
        interface="tracing",
        remote_app_name="tempo-coordinator-k8s",
        remote_app_data={
            "receivers": '[{"protocol": {"name": "otlp_http", "type": "http"}, "url": "http://tempo:4318"}]',
        },
    )


@pytest.fixture
def logging_relation() -> testing.Relation:
    return testing.Relation(
        endpoint="logging",
        interface="loki_push_api",
        remote_app_name="loki-k8s",
    )


@pytest.fixture
def metrics_endpoint_relation() -> testing.Relation:
    return testing.Relation(
        endpoint="metrics-endpoint",
        interface="prometheus_scrape",
        remote_app_name="prometheus-k8s",
    )


@pytest.fixture
def grafana_dashboard_relation() -> testing.Relation:
    return testing.Relation(
        endpoint="grafana-dashboard",
        interface="grafana_dashboard",
        remote_app_name="grafana-k8s",
    )


# ---------------------------------------------------------------------------
# Charm service mocks
# ---------------------------------------------------------------------------
@pytest.fixture
def mocked_workload_service_version(mocker: MockerFixture) -> MagicMock:
    return mocker.patch(
        "charm.WorkloadService.version", new_callable=PropertyMock, return_value="2025.6.1"
    )


@pytest.fixture
def mocked_open_port(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("charm.WorkloadService.open_port")


@pytest.fixture
def mocked_holistic_handler(mocker: MockerFixture) -> MagicMock:
    mock_fn = MagicMock()

    def _on_holistic_handler(self: Any, event: Any) -> None:
        mock_fn(event)

    mocker.patch("charm.AuthentikServerCharm._on_holistic_handler", _on_holistic_handler)
    return mock_fn


# ---------------------------------------------------------------------------
# Condition mock fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def mocked_container_connectivity(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("charm.container_connectivity", return_value=True)


@pytest.fixture
def mocked_get_missing_config_keys(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("charm.CharmConfig.get_missing_config_keys", return_value=[])


@pytest.fixture
def mocked_database_integration_exists(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("charm.database_integration_exists", return_value=True)


@pytest.fixture
def mocked_database_resource_is_created(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("charm.database_resource_is_created", return_value=True)


@pytest.fixture
def mocked_secrets_is_ready(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("charm.Secrets.is_ready", return_value=True)


@pytest.fixture
def mocked_workload_is_running(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("charm.WorkloadService.is_running", return_value=True)


@pytest.fixture
def mocked_workload_is_failing(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("charm.WorkloadService.is_failing", return_value=False)


@pytest.fixture
def all_satisfied_conditions(
    mocked_container_connectivity: MagicMock,
    mocked_get_missing_config_keys: MagicMock,
    mocked_database_integration_exists: MagicMock,
    mocked_database_resource_is_created: MagicMock,
    mocked_secrets_is_ready: MagicMock,
    mocked_workload_is_running: MagicMock,
    mocked_workload_is_failing: MagicMock,
) -> None:
    pass
