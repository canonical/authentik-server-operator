# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the CommandLine abstraction."""

from unittest.mock import MagicMock

import pytest
from ops import Container
from ops.pebble import ExecError

from cli import CommandLine
from exceptions import DatabaseConnectionError, MigrationFailedError, MigrationPendingError


class TestCommandLine:
    @pytest.fixture
    def mocked_container(self) -> MagicMock:
        return MagicMock(spec=Container)

    @pytest.fixture
    def cli(self, mocked_container: MagicMock) -> CommandLine:
        return CommandLine(mocked_container)

    def test_get_version_success(self, cli: CommandLine, mocked_container: MagicMock) -> None:
        exec_mock = MagicMock()
        exec_mock.wait_output.return_value = ("2026.3.1\n", "")
        mocked_container.exec.return_value = exec_mock

        version = cli.get_version()
        assert version == "2026.3.1"
        mocked_container.exec.assert_called_once_with(
            ["/lifecycle/ak", "version"], environment=None, service_context=None
        )

    def test_get_version_fallback_success(
        self, cli: CommandLine, mocked_container: MagicMock
    ) -> None:
        exec_error = ExecError(
            command=["/lifecycle/ak", "version"], exit_code=1, stdout="", stderr="error"
        )
        exec_mock_error = MagicMock()
        exec_mock_error.wait_output.side_effect = exec_error

        exec_mock_success = MagicMock()
        exec_mock_success.wait_output.return_value = ("2026.3.2-fallback\n", "")

        mocked_container.exec.side_effect = [exec_mock_error, exec_mock_success]

        version = cli.get_version()
        assert version == "2026.3.2-fallback"
        assert mocked_container.exec.call_count == 2

    def test_get_version_failure_returns_empty_string(
        self, cli: CommandLine, mocked_container: MagicMock
    ) -> None:
        exec_error = ExecError(command=["cmd"], exit_code=1, stdout="", stderr="error")
        exec_mock_error = MagicMock()
        exec_mock_error.wait_output.side_effect = exec_error

        mocked_container.exec.return_value = exec_mock_error

        version = cli.get_version()
        assert version == ""

    def test_check_migrations_success(self, cli: CommandLine, mocked_container: MagicMock) -> None:
        exec_mock = MagicMock()
        exec_mock.wait_output.return_value = ("", "")
        mocked_container.exec.return_value = exec_mock

        # Should not raise
        cli.check_migrations()
        mocked_container.exec.assert_called_once_with(
            ["/ak-root/.venv/bin/python", "-m", "manage", "migrate", "--check"],
            environment=None,
            service_context="authentik-server",
        )

    def test_check_migrations_pending(self, cli: CommandLine, mocked_container: MagicMock) -> None:
        exec_error = ExecError(
            command=["migrate"], exit_code=1, stdout="", stderr="Pending migrations"
        )
        exec_mock = MagicMock()
        exec_mock.wait_output.side_effect = exec_error
        mocked_container.exec.return_value = exec_mock

        with pytest.raises(MigrationPendingError):
            cli.check_migrations()

    def test_check_migrations_db_connection_error(
        self, cli: CommandLine, mocked_container: MagicMock
    ) -> None:
        exec_error = ExecError(
            command=["migrate"],
            exit_code=2,
            stdout="",
            stderr="OperationalError: database is down",
        )
        exec_mock = MagicMock()
        exec_mock.wait_output.side_effect = exec_error
        mocked_container.exec.return_value = exec_mock

        with pytest.raises(DatabaseConnectionError):
            cli.check_migrations()

    def test_check_migrations_failed(self, cli: CommandLine, mocked_container: MagicMock) -> None:
        exec_error = ExecError(
            command=["migrate"], exit_code=3, stdout="", stderr="Some migration error occurred"
        )
        exec_mock = MagicMock()
        exec_mock.wait_output.side_effect = exec_error
        mocked_container.exec.return_value = exec_mock

        with pytest.raises(MigrationFailedError):
            cli.check_migrations()
