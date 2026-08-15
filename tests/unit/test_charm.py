# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the Authentik Server charm."""

from unittest.mock import MagicMock, patch

import pytest
from ops import ModelError, SecretNotFoundError, StatusBase, pebble, testing
from ops.testing import ActionFailed
from pytest_mock import MockerFixture
from scenario.errors import UncaughtCharmError
from unit.conftest import create_state

from constants import (
    HEALTH_CHECK_URL,
    OAUTH_RELATION_NAME,
    PEBBLE_READY_CHECK_NAME,
    WORKLOAD_CONTAINER,
    WORKLOAD_SERVICE,
)
from exceptions import (
    AuthentikRequestValidationError,
    AuthentikTransientError,
    SecretError,
    ServiceBackoffError,
    WorkloadNotRunningError,
)

_BASE_PLAN_WITH_CHECK: dict = {
    "checks": {
        PEBBLE_READY_CHECK_NAME: {
            "override": "replace",
            "level": "alive",
            "http": {"url": HEALTH_CHECK_URL},
        }
    }
}


class TestPebbleReadyEvent:
    def test_when_event_emitted(
        self,
        context: testing.Context,
        container: testing.Container,
        cluster_relation: testing.Relation,
        mocked_open_port: MagicMock,
        mocked_holistic_handler: MagicMock,
        mocked_workload_service_version: MagicMock,
        all_satisfied_conditions: None,
    ) -> None:
        state = create_state(relations=[cluster_relation])

        state_out = context.run(context.on.pebble_ready(container), state)

        assert state_out.unit_status == testing.ActiveStatus()
        mocked_open_port.assert_called_once()
        mocked_holistic_handler.assert_called_once()
        assert state_out.workload_version == mocked_workload_service_version.return_value


class TestConfigChangedEvent:
    def test_when_event_emitted(
        self,
        context: testing.Context,
        cluster_relation: testing.Relation,
        mocked_holistic_handler: MagicMock,
        all_satisfied_conditions: None,
    ) -> None:
        state = create_state(relations=[cluster_relation])

        state_out = context.run(context.on.config_changed(), state)

        assert state_out.unit_status == testing.ActiveStatus()
        mocked_holistic_handler.assert_called_once()


class TestHolisticHandler:
    def test_when_container_not_connected(
        self,
        context: testing.Context,
        cluster_relation: testing.Relation,
        all_satisfied_conditions: None,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch("charm.container_connectivity", return_value=False)
        state = create_state(relations=[cluster_relation], can_connect=False)

        state_out = context.run(context.on.config_changed(), state)

        assert state_out.unit_status == testing.WaitingStatus("waiting for pebble")

    def test_when_all_conditions_satisfied(
        self,
        context: testing.Context,
        db_relation: testing.Relation,
        peer_relation: testing.PeerRelation,
        cluster_relation: testing.Relation,
        authentik_secrets: testing.Secret,
        all_satisfied_conditions: None,
    ) -> None:
        state = create_state(
            relations=[db_relation, peer_relation, cluster_relation],
            secrets=[authentik_secrets],
        )

        state_out = context.run(context.on.config_changed(), state)

        assert state_out.unit_status == testing.ActiveStatus()

    def test_non_leader_skips_secret_creation(
        self,
        context: testing.Context,
        db_relation: testing.Relation,
        peer_relation: testing.PeerRelation,
        cluster_relation: testing.Relation,
        authentik_secrets: testing.Secret,
        all_satisfied_conditions: None,
        mocker: MockerFixture,
    ) -> None:
        mocked_create = mocker.patch("charm.Secrets.create")
        state = create_state(
            leader=False,
            relations=[db_relation, peer_relation, cluster_relation],
            secrets=[authentik_secrets],
        )

        context.run(context.on.config_changed(), state)

        mocked_create.assert_not_called()

    def test_charm_error_from_ensure_secrets(
        self,
        context: testing.Context,
        db_relation: testing.Relation,
        peer_relation: testing.PeerRelation,
        cluster_relation: testing.Relation,
        all_satisfied_conditions: None,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch("charm.Secrets.is_ready", return_value=False)
        mocker.patch("charm.Secrets.create", side_effect=SecretError("fail"))
        state = create_state(
            relations=[db_relation, peer_relation, cluster_relation],
        )

        # Should not raise — CharmError is caught and can_plan set to False
        context.run(context.on.config_changed(), state)

    def test_authentik_api_error_is_caught(
        self,
        context: testing.Context,
        db_relation: testing.Relation,
        peer_relation: testing.PeerRelation,
        cluster_relation: testing.Relation,
        authentik_secrets: testing.Secret,
        all_satisfied_conditions: None,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch(
            "charm.AuthentikServerCharm._ensure_oauth_relation",
            side_effect=AuthentikRequestValidationError("bad scope"),
        )
        state = create_state(
            relations=[db_relation, peer_relation, cluster_relation],
            secrets=[authentik_secrets],
        )

        # Should not raise — typed Authentik API errors are caught like CharmError.
        context.run(context.on.config_changed(), state)

    def test_oauth_api_is_not_constructed_before_workload_is_ready(
        self,
        context: testing.Context,
        db_relation: testing.Relation,
        peer_relation: testing.PeerRelation,
        cluster_relation: testing.Relation,
        authentik_secrets: testing.Secret,
        traefik_route_relation: testing.Relation,
        all_satisfied_conditions: None,
        mocked_workload_is_running: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        oauth_relation = testing.Relation("oauth", remote_app_name="client")
        mocked_workload_is_running.return_value = False
        api_class = mocker.patch("charm.AuthentikAPI")
        state = create_state(
            relations=[
                db_relation,
                peer_relation,
                cluster_relation,
                oauth_relation,
                traefik_route_relation,
            ],
            secrets=[authentik_secrets],
        )

        context.run(context.on.config_changed(), state)

        api_class.assert_not_called()

    def test_exhausted_oauth_api_failure_propagates_from_hook(
        self,
        context: testing.Context,
        db_relation: testing.Relation,
        peer_relation: testing.PeerRelation,
        cluster_relation: testing.Relation,
        authentik_secrets: testing.Secret,
        traefik_route_relation: testing.Relation,
        all_satisfied_conditions: None,
        mocker: MockerFixture,
    ) -> None:
        oauth_relation = testing.Relation("oauth", remote_app_name="client")
        api = mocker.patch("charm.AuthentikAPI", autospec=True).return_value
        api.is_service_available = True
        api.get_authorization_flow_uuid.side_effect = AuthentikTransientError(
            "retry budget exhausted"
        )
        state = create_state(
            relations=[
                db_relation,
                peer_relation,
                cluster_relation,
                oauth_relation,
                traefik_route_relation,
            ],
            secrets=[authentik_secrets],
        )

        with pytest.raises(UncaughtCharmError, match="retry budget exhausted"):
            context.run(context.on.config_changed(), state)

    def test_server_info_not_published_before_api_ready(
        self,
        context: testing.Context,
        db_relation: testing.Relation,
        peer_relation: testing.PeerRelation,
        cluster_relation: testing.Relation,
        server_info_relation: testing.Relation,
        authentik_secrets: testing.Secret,
        traefik_route_relation: testing.Relation,
        all_satisfied_conditions: None,
        mocker: MockerFixture,
    ) -> None:
        """Server-info stays unpublished while the workload API is unavailable."""
        mocker.patch("charm.AuthentikServerCharm._ensure_oauth_relation", return_value=True)
        api = mocker.patch("charm.AuthentikAPI", autospec=True).return_value
        api.is_service_available = False
        publish = mocker.patch("charm.AuthentikServerInfoProvider.update_relations_app_data")
        state = create_state(
            relations=[
                db_relation,
                peer_relation,
                cluster_relation,
                server_info_relation,
                traefik_route_relation,
            ],
            secrets=[authentik_secrets],
        )

        context.run(context.on.config_changed(), state)

        publish.assert_not_called()

    def test_server_info_published_once_api_ready(
        self,
        context: testing.Context,
        db_relation: testing.Relation,
        peer_relation: testing.PeerRelation,
        cluster_relation: testing.Relation,
        server_info_relation: testing.Relation,
        authentik_secrets: testing.Secret,
        traefik_route_relation: testing.Relation,
        all_satisfied_conditions: None,
        mocker: MockerFixture,
    ) -> None:
        """Server-info is published once the workload API becomes reachable."""
        mocker.patch("charm.AuthentikServerCharm._ensure_oauth_relation", return_value=True)
        api = mocker.patch("charm.AuthentikAPI", autospec=True).return_value
        api.is_service_available = True
        publish = mocker.patch("charm.AuthentikServerInfoProvider.update_relations_app_data")
        state = create_state(
            relations=[
                db_relation,
                peer_relation,
                cluster_relation,
                server_info_relation,
                traefik_route_relation,
            ],
            secrets=[authentik_secrets],
        )

        context.run(context.on.config_changed(), state)

        publish.assert_called_once()


class TestCollectStatusEvent:
    def test_when_all_conditions_satisfied(
        self,
        context: testing.Context,
        cluster_relation: testing.Relation,
        all_satisfied_conditions: None,
    ) -> None:
        state = create_state(relations=[cluster_relation])

        state_out = context.run(context.on.collect_unit_status(), state)

        assert state_out.unit_status == testing.ActiveStatus()

    @pytest.mark.parametrize(
        "condition, condition_value, status, message",
        [
            (
                "container_connectivity",
                False,
                testing.WaitingStatus,
                "waiting for pebble",
            ),
            (
                "database_integration_exists",
                False,
                testing.BlockedStatus,
                "missing pg-database relation",
            ),
            (
                "database_resource_is_created",
                False,
                testing.WaitingStatus,
                "waiting for database creation",
            ),
            (
                "Secrets.is_ready",
                False,
                testing.WaitingStatus,
                "waiting for secrets",
            ),
            (
                "WorkloadService.check_health",
                ServiceBackoffError("Service is in backoff/error"),
                testing.BlockedStatus,
                f"failed to start the service, please check the "
                f"{WORKLOAD_CONTAINER} container logs",
            ),
            (
                "WorkloadService.check_health",
                WorkloadNotRunningError("Service is not running"),
                testing.WaitingStatus,
                "waiting for the service to start",
            ),
        ],
        ids=[
            "container_not_connected",
            "database_integration_missing",
            "database_resource_not_created",
            "secrets_not_ready",
            "workload_service_failing",
            "workload_service_not_running",
        ],
    )
    def test_when_a_condition_failed(
        self,
        context: testing.Context,
        cluster_relation: testing.Relation,
        all_satisfied_conditions: None,
        condition: str,
        condition_value: bool,
        status: type[StatusBase],
        message: str,
    ) -> None:
        state = create_state(relations=[cluster_relation])

        kwargs = {}
        if isinstance(condition_value, Exception):
            kwargs["side_effect"] = condition_value
        else:
            kwargs["return_value"] = condition_value

        with patch(f"charm.{condition}", **kwargs):
            state_out = context.run(context.on.collect_unit_status(), state)

        assert isinstance(state_out.unit_status, status)
        assert state_out.unit_status.message == message

    def test_missing_authentik_worker_relation(
        self,
        context: testing.Context,
        all_satisfied_conditions: None,
    ) -> None:
        """Test that missing authentik-cluster relation reports BlockedStatus."""
        state = create_state()

        state_out = context.run(context.on.collect_unit_status(), state)

        assert isinstance(state_out.unit_status, testing.BlockedStatus)
        assert state_out.unit_status.message == "missing authentik-worker relation"

    def test_with_cluster_relation_active(
        self,
        context: testing.Context,
        cluster_relation: testing.Relation,
        all_satisfied_conditions: None,
    ) -> None:
        """Test that with cluster relation present, status is Active."""
        state = create_state(relations=[cluster_relation])

        state_out = context.run(context.on.collect_unit_status(), state)

        assert state_out.unit_status == testing.ActiveStatus()


class TestDatabaseEvents:
    def test_on_relation_changed(
        self,
        context: testing.Context,
        mocked_holistic_handler: MagicMock,
        db_relation: testing.Relation,
    ) -> None:
        state = create_state(relations=[db_relation])

        context.run(context.on.relation_changed(db_relation), state)

        mocked_holistic_handler.assert_called_once()

    def test_on_read_only_endpoints_changed(
        self,
        context: testing.Context,
        mocked_holistic_handler: MagicMock,
        db_relation: testing.Relation,
    ) -> None:
        """Replica churn must trigger the holistic handler."""
        replica_relation = testing.Relation(
            endpoint="pg-database",
            interface="postgresql_client",
            remote_app_name="postgresql-k8s",
            remote_app_data={
                **db_relation.remote_app_data,
                "read-only-endpoints": "replica-a:5432",
            },
        )
        state = create_state(relations=[replica_relation])

        context.run(context.on.relation_changed(replica_relation), state)

        mocked_holistic_handler.assert_called_once()

    def test_read_replicas_published_to_cluster_relation(
        self,
        context: testing.Context,
        peer_relation: testing.PeerRelation,
        cluster_relation: testing.Relation,
        authentik_secrets: testing.Secret,
        traefik_route_relation: testing.Relation,
        all_satisfied_conditions: None,
    ) -> None:
        """The primary is filtered out and the remaining replicas are published."""
        replica_relation = testing.Relation(
            endpoint="pg-database",
            interface="postgresql_client",
            remote_app_name="postgresql-k8s",
            remote_app_data={
                "database": "authentik",
                "endpoints": "test-host:5432",
                "read-only-endpoints": "test-host:5432,replica-a:5432,replica-b:5432",
                "username": "test-user",
                "password": "test-pass",
            },
        )
        state = create_state(
            relations=[
                replica_relation,
                peer_relation,
                cluster_relation,
                traefik_route_relation,
            ],
            secrets=[authentik_secrets],
        )

        state_out = context.run(context.on.config_changed(), state)

        rel_out = state_out.get_relation(cluster_relation.id)
        assert rel_out.local_app_data["db_read_replicas"] == "replica-a:5432,replica-b:5432"

    def test_on_database_relation_broken(
        self,
        context: testing.Context,
        db_relation: testing.Relation,
        mocker: MockerFixture,
    ) -> None:
        mock_stop = mocker.patch("ops.model.Container.stop")
        state = create_state(relations=[db_relation])

        context.run(context.on.relation_broken(db_relation), state)

        mock_stop.assert_called_once_with(WORKLOAD_SERVICE)

    def test_on_database_relation_broken_container_not_connected(
        self,
        context: testing.Context,
        db_relation: testing.Relation,
    ) -> None:
        state = create_state(relations=[db_relation], can_connect=False)

        # Should not raise
        context.run(context.on.relation_broken(db_relation), state)


class TestSmtpEvents:
    def test_on_smtp_relation_changed(
        self,
        context: testing.Context,
        mocked_holistic_handler: MagicMock,
        smtp_relation: testing.Relation,
    ) -> None:
        state = create_state(relations=[smtp_relation])

        context.run(context.on.relation_changed(smtp_relation), state)

        mocked_holistic_handler.assert_called_once()

    def test_smtp_variables_applied_to_pebble_layer(
        self,
        context: testing.Context,
        db_relation: testing.Relation,
        peer_relation: testing.PeerRelation,
        cluster_relation: testing.Relation,
        authentik_secrets: testing.Secret,
        smtp_relation: testing.Relation,
        traefik_route_relation: testing.Relation,
        all_satisfied_conditions: None,
    ) -> None:
        state = create_state(
            relations=[
                db_relation,
                peer_relation,
                cluster_relation,
                smtp_relation,
                traefik_route_relation,
            ],
            secrets=[authentik_secrets],
        )

        state_out = context.run(context.on.config_changed(), state)

        container = state_out.get_container(WORKLOAD_CONTAINER)
        plan = container.plan.to_dict()
        services = plan.get("services", {})
        assert WORKLOAD_SERVICE in services
        service = services[WORKLOAD_SERVICE]

        env = service.get("environment", {})
        assert env.get("AUTHENTIK_EMAIL__HOST") == "smtp.example.com"
        assert env.get("AUTHENTIK_EMAIL__PORT") == "587"
        assert env.get("AUTHENTIK_EMAIL__USERNAME") == "user"
        assert env.get("AUTHENTIK_EMAIL__PASSWORD") == "password"
        assert env.get("AUTHENTIK_EMAIL__USE_TLS") == "true"
        assert env.get("AUTHENTIK_EMAIL__USE_SSL") == "false"
        assert env.get("AUTHENTIK_EMAIL__FROM") == "sender@example.com"


class TestTraefikRouteEvents:
    def test_on_traefik_route_ready(
        self,
        context: testing.Context,
        mocked_holistic_handler: MagicMock,
        traefik_route_relation: testing.Relation,
    ) -> None:
        state = create_state(relations=[traefik_route_relation])

        context.run(context.on.relation_changed(traefik_route_relation), state)

        mocked_holistic_handler.assert_called_once()

    def test_traefik_route_variables_applied_to_pebble_layer(
        self,
        context: testing.Context,
        db_relation: testing.Relation,
        peer_relation: testing.PeerRelation,
        cluster_relation: testing.Relation,
        authentik_secrets: testing.Secret,
        traefik_route_relation: testing.Relation,
        all_satisfied_conditions: None,
    ) -> None:
        state = create_state(
            relations=[db_relation, peer_relation, cluster_relation, traefik_route_relation],
            secrets=[authentik_secrets],
        )

        state_out = context.run(context.on.config_changed(), state)

        container = state_out.get_container(WORKLOAD_CONTAINER)
        plan = container.plan.to_dict()
        services = plan.get("services", {})
        assert WORKLOAD_SERVICE in services
        service = services[WORKLOAD_SERVICE]

        env = service.get("environment", {})
        assert env.get("AUTHENTIK_OPTS__BASE_URL") == "https://authentik.example.com"

    def test_traefik_route_propagated_to_server_info(
        self,
        context: testing.Context,
        db_relation: testing.Relation,
        peer_relation: testing.PeerRelation,
        cluster_relation: testing.Relation,
        authentik_secrets: testing.Secret,
        traefik_route_relation: testing.Relation,
        server_info_relation: testing.Relation,
        all_satisfied_conditions: None,
        mocker: MockerFixture,
    ) -> None:
        api = mocker.patch("charm.AuthentikAPI", autospec=True).return_value
        api.is_service_available = True
        state = create_state(
            relations=[
                db_relation,
                peer_relation,
                cluster_relation,
                traefik_route_relation,
                server_info_relation,
            ],
            secrets=[authentik_secrets],
        )

        state_out = context.run(context.on.config_changed(), state)

        # Retrieve output databag for server-info relation
        server_info_out = state_out.get_relation(server_info_relation.id)
        # Check app databag of this unit's app
        assert (
            server_info_out.local_app_data.get("authentik_host")
            == "http://authentik-server.test-model.svc.cluster.local:9000"
        )

    def test_traefik_route_submits_to_traefik(
        self,
        context: testing.Context,
        db_relation: testing.Relation,
        peer_relation: testing.PeerRelation,
        cluster_relation: testing.Relation,
        authentik_secrets: testing.Secret,
        traefik_route_relation: testing.Relation,
        all_satisfied_conditions: None,
    ) -> None:
        state = create_state(
            relations=[db_relation, peer_relation, cluster_relation, traefik_route_relation],
            secrets=[authentik_secrets],
        )

        state_out = context.run(context.on.config_changed(), state)

        traefik_route_out = state_out.get_relation(traefik_route_relation.id)
        # Verify the submitted YAML config exists in local app data
        config_yaml = traefik_route_out.local_app_data.get("config")
        assert config_yaml is not None

        import yaml

        config_dict = yaml.safe_load(config_yaml)
        # Check router and service mappings
        assert "http" in config_dict
        assert "routers" in config_dict["http"]
        assert "services" in config_dict["http"]

        routers = config_dict["http"]["routers"]
        services = config_dict["http"]["services"]

        # Verify that isolation-guaranteed names exist
        router_key = "juju-test-model-authentik-server-router-root"
        service_key = "juju-test-model-authentik-server-service"
        assert router_key in routers
        assert service_key in services

        assert (
            routers[router_key]["rule"]
            == "PathPrefix(`/if`, `/flows`, `/api`, `/.well-known`, `/static`, `/media`, `/application/o`, `/outpost.goauthentik.io`, `/brand`, `/oauth2`, `/recovery`, `/source`) || Path(`/`)"
        )
        assert routers[router_key]["service"] == service_key
        assert routers[router_key]["tls"]["domains"][0]["main"] == "authentik.example.com"


class TestPebbleCheckEvents:
    def test_on_pebble_check_failed(
        self,
        context: testing.Context,
        container: testing.Container,
        all_satisfied_conditions: None,
        mocker: MockerFixture,
    ) -> None:
        mocked_logger = mocker.patch("charm.logger")
        check_info = testing.CheckInfo(
            name=PEBBLE_READY_CHECK_NAME,
            level="alive",
            status="down",
            startup=pebble.CheckStartup.UNSET,
            threshold=None,
        )
        state = create_state(
            containers=[
                testing.Container(
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
                    check_infos=[check_info],
                    _base_plan=_BASE_PLAN_WITH_CHECK,
                )
            ]
        )

        context.run(
            context.on.pebble_check_failed(container, check_info),
            state,
        )

        mocked_logger.warning.assert_called_once_with("The authentik service is not running")

    def test_on_pebble_check_recovered(
        self,
        context: testing.Context,
        container: testing.Container,
        all_satisfied_conditions: None,
        mocked_holistic_handler: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mocked_logger = mocker.patch("charm.logger")
        check_info = testing.CheckInfo(
            name=PEBBLE_READY_CHECK_NAME,
            level="alive",
            status="up",
            startup=pebble.CheckStartup.UNSET,
            threshold=None,
        )
        state = create_state(
            containers=[
                testing.Container(
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
                    check_infos=[check_info],
                    _base_plan=_BASE_PLAN_WITH_CHECK,
                )
            ]
        )

        context.run(
            context.on.pebble_check_recovered(container, check_info),
            state,
        )

        mocked_logger.info.assert_called_once_with("The authentik service is online again")
        mocked_holistic_handler.assert_called_once()


class TestClusterRelationEvents:
    def test_on_cluster_relation_created(
        self,
        context: testing.Context,
        cluster_relation: testing.Relation,
        mocked_holistic_handler: MagicMock,
    ) -> None:
        state = create_state(relations=[cluster_relation])

        context.run(context.on.relation_created(cluster_relation), state)

        mocked_holistic_handler.assert_called_once()


class TestServerInfoRelationEvents:
    def test_on_server_info_relation_created(
        self,
        context: testing.Context,
        server_info_relation: testing.Relation,
        mocked_holistic_handler: MagicMock,
    ) -> None:
        state = create_state(relations=[server_info_relation])

        context.run(context.on.relation_created(server_info_relation), state)

        mocked_holistic_handler.assert_called_once()


class TestCertificateEvents:
    def test_on_certificate_changed(
        self,
        context: testing.Context,
        certificate_transfer_relation: testing.Relation,
        db_relation: testing.Relation,
        cluster_relation: testing.Relation,
        peer_relation: testing.PeerRelation,
        traefik_route_relation: testing.Relation,
        authentik_secrets: testing.Secret,
        mocked_subprocess_run: MagicMock,
        all_satisfied_conditions: None,
        mocker: MockerFixture,
    ) -> None:
        """Test that certificate changed event updates local certs and runs update-ca-certificates."""
        mock_path = mocker.patch("charm.LOCAL_CHARM_CERTIFICATES_FILE")
        mock_path.exists.return_value = False
        mock_path.parent.mkdir.return_value = None

        mock_tls = mocker.patch("charm.TLSCertificates")
        mock_tls.load.return_value.ca_bundle = "some-ca-cert"

        state = create_state(
            relations=[
                certificate_transfer_relation,
                db_relation,
                cluster_relation,
                peer_relation,
                traefik_route_relation,
            ],
            secrets=[authentik_secrets],
        )

        context.run(context.on.relation_changed(certificate_transfer_relation), state)

        mock_path.write_text.assert_called_with("some-ca-cert")
        mocked_subprocess_run.assert_called()


class TestTLSFailure:
    def test_ensure_tls_subprocess_failure_blocks_plan(
        self,
        context: testing.Context,
        certificate_transfer_relation: testing.Relation,
        db_relation: testing.Relation,
        cluster_relation: testing.Relation,
        peer_relation: testing.PeerRelation,
        traefik_route_relation: testing.Relation,
        authentik_secrets: testing.Secret,
        mocked_subprocess_run: MagicMock,
        all_satisfied_conditions: None,
        mocker: MockerFixture,
    ) -> None:
        """Test that TLS subprocess failure unlinks cert and blocks pebble planning."""
        import subprocess

        mock_path = mocker.patch("charm.LOCAL_CHARM_CERTIFICATES_FILE")
        mock_path.exists.return_value = False
        mock_path.parent.mkdir.return_value = None

        mock_tls = mocker.patch("charm.TLSCertificates")
        mock_tls.load.return_value.ca_bundle = "new-ca-cert"

        mocked_subprocess_run.side_effect = subprocess.CalledProcessError(
            1, "update-ca-certificates"
        )

        state = create_state(
            relations=[
                certificate_transfer_relation,
                db_relation,
                cluster_relation,
                peer_relation,
                traefik_route_relation,
            ],
            secrets=[authentik_secrets],
        )

        state_out = context.run(context.on.config_changed(), state)

        mock_path.unlink.assert_called_with(missing_ok=True)
        container_out = state_out.get_container(WORKLOAD_CONTAINER)
        assert WORKLOAD_SERVICE not in container_out.layers


class TestCharmActions:
    def test_get_bootstrap_admin_credentials_success(
        self,
        context: testing.Context,
        peer_relation: testing.PeerRelation,
        authentik_secrets: testing.Secret,
        all_satisfied_conditions: None,
    ) -> None:
        state = create_state(
            relations=[peer_relation],
            secrets=[authentik_secrets],
        )

        context.run(context.on.action("get-bootstrap-admin-credentials"), state)

        assert context.action_results == {
            "username": "akadmin",
            "password": "test-bootstrap-password",
            "bootstrap-token": "test-bootstrap-token",
            "warning": (
                "These are initial bootstrap credentials generated at deployment time. "
                "If the administrator password was subsequently changed via the web UI or "
                "recovery flows, the password returned here will be stale."
            ),
        }

    def test_get_bootstrap_admin_credentials_secrets_not_ready(
        self,
        context: testing.Context,
    ) -> None:
        state = create_state(relations=[])

        with pytest.raises(ActionFailed) as exc_info:
            context.run(context.on.action("get-bootstrap-admin-credentials"), state)
        assert "Admin credentials are not ready yet." in str(exc_info.value)

    def test_create_recovery_link_success(
        self,
        context: testing.Context,
        peer_relation: testing.PeerRelation,
        authentik_secrets: testing.Secret,
        all_satisfied_conditions: None,
        mocker: MockerFixture,
    ) -> None:
        state = create_state(
            relations=[peer_relation],
            secrets=[authentik_secrets],
        )

        # Mock WorkloadService.create_recovery_link
        mock_create_recovery_link = mocker.patch(
            "charm.WorkloadService.create_recovery_link",
            return_value="/recovery/use-token/token123/",
        )

        context.run(
            context.on.action(
                "create-recovery-link", params={"username": "user1", "duration": 15}
            ),
            state,
        )

        mock_create_recovery_link.assert_called_once_with("user1", 15)
        assert context.action_results == {
            "status": "success",
            "url": "http://authentik-server.test-model.svc.cluster.local:9000/recovery/use-token/token123/",
            "path": "/recovery/use-token/token123/",
        }

    def test_create_recovery_link_cannot_connect(
        self,
        context: testing.Context,
    ) -> None:
        state = create_state(can_connect=False)

        with pytest.raises(ActionFailed) as exc_info:
            context.run(context.on.action("create-recovery-link"), state)
        assert "Cannot connect to the workload container" in str(exc_info.value)

    def test_create_recovery_link_command_failure(
        self,
        context: testing.Context,
        peer_relation: testing.PeerRelation,
        authentik_secrets: testing.Secret,
        all_satisfied_conditions: None,
        mocker: MockerFixture,
    ) -> None:
        state = create_state(
            relations=[peer_relation],
            secrets=[authentik_secrets],
        )

        # Mock WorkloadService.create_recovery_link to raise an exception
        mocker.patch(
            "charm.WorkloadService.create_recovery_link",
            side_effect=ValueError("Failed to run"),
        )

        with pytest.raises(ActionFailed) as exc_info:
            context.run(context.on.action("create-recovery-link"), state)
        assert "Failed to create recovery link" in str(exc_info.value)


class TestOauthCredentials:
    def test_transient_secret_read_error_raises_instead_of_rotating(
        self,
        context: testing.Context,
        container: testing.Container,
        mocker: MockerFixture,
    ) -> None:
        """A transient Juju secret-read error must not silently rotate OAuth credentials."""
        oauth_relation = testing.Relation(
            endpoint=OAUTH_RELATION_NAME,
            interface="oauth",
            local_app_data={"client_id": "existing-id", "client_secret_id": "secret-xyz"},
        )
        state = testing.State(leader=True, relations={oauth_relation}, containers={container})

        with context(context.on.update_status(), state) as manager:
            charm = manager.charm
            relation = charm.model.get_relation(OAUTH_RELATION_NAME)
            mocker.patch.object(
                charm.model, "get_secret", side_effect=ModelError("controller unavailable")
            )
            with pytest.raises(AuthentikTransientError):
                charm._get_or_generate_credentials(relation)

    def test_missing_client_secret_regenerates_credentials(
        self,
        context: testing.Context,
        container: testing.Container,
        mocker: MockerFixture,
    ) -> None:
        """A genuinely missing client secret regenerates credentials rather than failing."""
        oauth_relation = testing.Relation(
            endpoint=OAUTH_RELATION_NAME,
            interface="oauth",
            local_app_data={"client_id": "existing-id", "client_secret_id": "secret-xyz"},
        )
        state = testing.State(leader=True, relations={oauth_relation}, containers={container})

        with context(context.on.update_status(), state) as manager:
            charm = manager.charm
            relation = charm.model.get_relation(OAUTH_RELATION_NAME)
            mocker.patch.object(charm.model, "get_secret", side_effect=SecretNotFoundError())
            _, client_secret, is_new = charm._get_or_generate_credentials(relation)

        assert is_new is True
        assert client_secret
