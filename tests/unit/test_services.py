# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the WorkloadService class."""

from unittest.mock import MagicMock

import pytest
from ops import ModelError
from ops.pebble import CheckStatus, ExecError, ServiceStatus

from constants import PEBBLE_READY_CHECK_NAME
from exceptions import (
    DatabaseConnectionError,
    MigrationFailedError,
    MigrationPendingError,
    ServiceBackoffError,
    WorkloadNotRunningError,
)
from services import WorkloadService


class TestWorkloadService:
    @pytest.fixture
    def mocked_unit(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mocked_container(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def workload_service(
        self, mocked_unit: MagicMock, mocked_container: MagicMock
    ) -> WorkloadService:
        mocked_unit.get_container.return_value = mocked_container
        return WorkloadService(mocked_unit)

    # --- is_running tests ---

    def test_is_running_true(
        self, workload_service: WorkloadService, mocked_container: MagicMock
    ) -> None:
        service_mock = MagicMock()
        service_mock.is_running.return_value = True
        mocked_container.get_service.return_value = service_mock

        check_mock = MagicMock()
        check_mock.status = CheckStatus.UP
        check_mock.successes = 5
        mocked_container.get_checks.return_value = {PEBBLE_READY_CHECK_NAME: check_mock}

        assert workload_service.is_running() is True

    def test_is_running_false_no_service(
        self, workload_service: WorkloadService, mocked_container: MagicMock
    ) -> None:
        mocked_container.get_service.side_effect = ModelError("no service")
        assert workload_service.is_running() is False

    def test_is_running_false_not_running(
        self, workload_service: WorkloadService, mocked_container: MagicMock
    ) -> None:
        service_mock = MagicMock()
        service_mock.is_running.return_value = False
        mocked_container.get_service.return_value = service_mock
        assert workload_service.is_running() is False

    def test_is_running_false_no_check(
        self, workload_service: WorkloadService, mocked_container: MagicMock
    ) -> None:
        service_mock = MagicMock()
        service_mock.is_running.return_value = True
        mocked_container.get_service.return_value = service_mock
        mocked_container.get_checks.return_value = {}
        assert workload_service.is_running() is False

    def test_is_running_false_check_down(
        self, workload_service: WorkloadService, mocked_container: MagicMock
    ) -> None:
        service_mock = MagicMock()
        service_mock.is_running.return_value = True
        mocked_container.get_service.return_value = service_mock

        check_mock = MagicMock()
        check_mock.status = CheckStatus.DOWN
        check_mock.successes = 5
        mocked_container.get_checks.return_value = {PEBBLE_READY_CHECK_NAME: check_mock}

        assert workload_service.is_running() is False

    def test_is_running_false_check_no_successes(
        self, workload_service: WorkloadService, mocked_container: MagicMock
    ) -> None:
        service_mock = MagicMock()
        service_mock.is_running.return_value = True
        mocked_container.get_service.return_value = service_mock

        check_mock = MagicMock()
        check_mock.status = CheckStatus.UP
        check_mock.successes = 0
        mocked_container.get_checks.return_value = {PEBBLE_READY_CHECK_NAME: check_mock}

        assert workload_service.is_running() is False

    # --- is_failing tests ---

    def test_is_failing_true_backoff(
        self, workload_service: WorkloadService, mocked_container: MagicMock
    ) -> None:
        service_mock = MagicMock()
        service_mock.current = "backoff"
        mocked_container.get_service.return_value = service_mock
        assert workload_service.is_failing() is True

    def test_is_failing_true_check_down(
        self, workload_service: WorkloadService, mocked_container: MagicMock
    ) -> None:
        service_mock = MagicMock()
        service_mock.current = ServiceStatus.ACTIVE
        service_mock.is_running.return_value = True
        mocked_container.get_service.return_value = service_mock

        check_mock = MagicMock()
        check_mock.status = CheckStatus.DOWN
        mocked_container.get_checks.return_value = {PEBBLE_READY_CHECK_NAME: check_mock}

        assert workload_service.is_failing() is True

    def test_is_failing_false_not_running(
        self, workload_service: WorkloadService, mocked_container: MagicMock
    ) -> None:
        service_mock = MagicMock()
        service_mock.current = ServiceStatus.INACTIVE
        service_mock.is_running.return_value = False
        mocked_container.get_service.return_value = service_mock
        assert workload_service.is_failing() is False

    # --- check_health tests ---

    def test_check_health_success(
        self, workload_service: WorkloadService, mocked_container: MagicMock
    ) -> None:
        service_mock = MagicMock()
        service_mock.is_running.return_value = True
        service_mock.current = ServiceStatus.ACTIVE
        mocked_container.get_service.return_value = service_mock

        check_mock = MagicMock()
        check_mock.status = CheckStatus.UP
        check_mock.successes = 1
        mocked_container.get_checks.return_value = {PEBBLE_READY_CHECK_NAME: check_mock}

        # Should not raise any exceptions
        workload_service.check_health()

    def test_check_health_no_pebble_error(
        self, workload_service: WorkloadService, mocked_container: MagicMock
    ) -> None:
        mocked_container.get_service.side_effect = ModelError("Pebble is dead")
        with pytest.raises(WorkloadNotRunningError) as exc_info:
            workload_service.check_health()
        assert "connect to Pebble" in str(exc_info.value)

    def test_check_health_service_backoff(
        self, workload_service: WorkloadService, mocked_container: MagicMock
    ) -> None:
        service_mock = MagicMock()
        service_mock.current = "backoff"
        mocked_container.get_service.return_value = service_mock

        with pytest.raises(ServiceBackoffError):
            workload_service.check_health()

    def test_check_health_service_not_running(
        self, workload_service: WorkloadService, mocked_container: MagicMock
    ) -> None:
        service_mock = MagicMock()
        service_mock.current = ServiceStatus.INACTIVE
        service_mock.is_running.return_value = False
        mocked_container.get_service.return_value = service_mock

        with pytest.raises(WorkloadNotRunningError) as exc_info:
            workload_service.check_health()
        assert "not running" in str(exc_info.value)

    def test_check_health_ready_check_not_found(
        self, workload_service: WorkloadService, mocked_container: MagicMock
    ) -> None:
        service_mock = MagicMock()
        service_mock.current = ServiceStatus.ACTIVE
        service_mock.is_running.return_value = True
        mocked_container.get_service.return_value = service_mock
        mocked_container.get_checks.return_value = {}

        with pytest.raises(WorkloadNotRunningError) as exc_info:
            workload_service.check_health()
        assert "ready check not found" in str(exc_info.value)

    def test_check_health_ready_check_down_migrations_completed(
        self, workload_service: WorkloadService, mocked_container: MagicMock
    ) -> None:
        service_mock = MagicMock()
        service_mock.current = ServiceStatus.ACTIVE
        service_mock.is_running.return_value = True
        mocked_container.get_service.return_value = service_mock

        check_mock = MagicMock()
        check_mock.status = CheckStatus.DOWN
        mocked_container.get_checks.return_value = {PEBBLE_READY_CHECK_NAME: check_mock}

        exec_mock = MagicMock()
        exec_mock.wait_output.return_value = ("", "")
        mocked_container.exec.return_value = exec_mock

        with pytest.raises(WorkloadNotRunningError) as exc_info:
            workload_service.check_health()
        assert "starting up" in str(exc_info.value)

    def test_check_health_ready_check_down_migrations_pending(
        self, workload_service: WorkloadService, mocked_container: MagicMock
    ) -> None:
        service_mock = MagicMock()
        service_mock.current = ServiceStatus.ACTIVE
        service_mock.is_running.return_value = True
        mocked_container.get_service.return_value = service_mock

        check_mock = MagicMock()
        check_mock.status = CheckStatus.DOWN
        mocked_container.get_checks.return_value = {PEBBLE_READY_CHECK_NAME: check_mock}

        exec_mock = MagicMock()
        exec_error = ExecError(
            command=["migrate"], exit_code=1, stdout="", stderr="Pending migrations"
        )
        exec_mock.wait_output.side_effect = exec_error
        mocked_container.exec.return_value = exec_mock

        with pytest.raises(MigrationPendingError):
            workload_service.check_health()

    def test_check_health_ready_check_down_db_connection_error(
        self, workload_service: WorkloadService, mocked_container: MagicMock
    ) -> None:
        service_mock = MagicMock()
        service_mock.current = ServiceStatus.ACTIVE
        service_mock.is_running.return_value = True
        mocked_container.get_service.return_value = service_mock

        check_mock = MagicMock()
        check_mock.status = CheckStatus.DOWN
        mocked_container.get_checks.return_value = {PEBBLE_READY_CHECK_NAME: check_mock}

        exec_mock = MagicMock()
        exec_error = ExecError(
            command=["migrate"],
            exit_code=2,
            stdout="",
            stderr="OperationalError: database is down",
        )
        exec_mock.wait_output.side_effect = exec_error
        mocked_container.exec.return_value = exec_mock

        with pytest.raises(DatabaseConnectionError):
            workload_service.check_health()

    def test_check_health_ready_check_down_migration_failed(
        self, workload_service: WorkloadService, mocked_container: MagicMock
    ) -> None:
        service_mock = MagicMock()
        service_mock.current = ServiceStatus.ACTIVE
        service_mock.is_running.return_value = True
        mocked_container.get_service.return_value = service_mock

        check_mock = MagicMock()
        check_mock.status = CheckStatus.DOWN
        mocked_container.get_checks.return_value = {PEBBLE_READY_CHECK_NAME: check_mock}

        exec_mock = MagicMock()
        exec_error = ExecError(
            command=["migrate"], exit_code=3, stdout="", stderr="Some migration error occurred"
        )
        exec_mock.wait_output.side_effect = exec_error
        mocked_container.exec.return_value = exec_mock

        with pytest.raises(MigrationFailedError):
            workload_service.check_health()
