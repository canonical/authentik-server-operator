# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the Authentik Server charm."""

from unittest.mock import MagicMock, patch

import pytest
from ops import StatusBase, pebble, testing
from pytest_mock import MockerFixture
from unit.conftest import create_state

from constants import (
    HEALTH_CHECK_URL,
    PEBBLE_READY_CHECK_NAME,
    WORKLOAD_CONTAINER,
    WORKLOAD_SERVICE,
)
from exceptions import SecretError

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
        mocker.patch("charm.Secrets.__setitem__", side_effect=SecretError("fail"))
        state = create_state(
            relations=[db_relation, peer_relation, cluster_relation],
        )

        # Should not raise — CharmError is caught and can_plan set to False
        context.run(context.on.config_changed(), state)


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
                "WorkloadService.is_failing",
                True,
                testing.BlockedStatus,
                f"failed to start the service, please check the "
                f"{WORKLOAD_CONTAINER} container logs",
            ),
            (
                "WorkloadService.is_running",
                False,
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

        with patch(f"charm.{condition}", return_value=condition_value):
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


class TestIngressEvents:
    def test_on_ingress_ready(
        self,
        context: testing.Context,
        mocked_holistic_handler: MagicMock,
        ingress_relation: testing.Relation,
    ) -> None:
        state = create_state(relations=[ingress_relation])

        context.run(context.on.relation_changed(ingress_relation), state)

        mocked_holistic_handler.assert_called_once()

    def test_on_ingress_revoked(
        self,
        context: testing.Context,
        mocked_holistic_handler: MagicMock,
        ingress_relation: testing.Relation,
    ) -> None:
        state = create_state(relations=[ingress_relation])

        context.run(context.on.relation_broken(ingress_relation), state)

        mocked_holistic_handler.assert_called_once()


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
