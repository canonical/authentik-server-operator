# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helper class to access the Authentik CLI and management tools."""

import logging
import re

from ops import Container
from ops.pebble import ExecError

from constants import WORKLOAD_SERVICE
from exceptions import DatabaseConnectionError, MigrationFailedError, MigrationPendingError

logger = logging.getLogger(__name__)


class CommandLine:
    """A class to handle command line interactions with Authentik."""

    def __init__(self, container: Container) -> None:
        """Initialize the CommandLine helper.

        Args:
            container: The workload container.
        """
        self.container = container

    def get_version(self) -> str:
        """Get the version of the Authentik workload.

        Returns:
            The version string, or an empty string if it could not be determined.
        """
        # `/lifecycle/ak version` runs Django's `manage version` (the framework
        # version, e.g. 5.2.x), not Authentik's, so read Authentik's VERSION directly.
        # An absolute interpreter path is used so this does not depend on the service
        # PATH (no service_context needed).
        try:
            stdout, _ = self._run_cmd(
                [
                    "/ak-root/.venv/bin/python",
                    "-c",
                    "from authentik import VERSION; print(VERSION)",
                ],
                environment={"PYTHONPATH": "/"},
            )
            return stdout.strip()
        except Exception as err:
            logger.error("Failed to fetch the Authentik version: %s", err)
            return ""

    def check_migrations(self) -> None:
        """Check the status of database migrations.

        Raises:
            MigrationPendingError: If migrations are currently running.
            DatabaseConnectionError: If the database connection failed.
            MigrationFailedError: If database migration failed.
        """
        try:
            self._run_cmd(
                [
                    "/ak-root/.venv/bin/python",
                    "-m",
                    "manage",
                    "migrate",
                    "--check",
                ],
                service_context=WORKLOAD_SERVICE,
            )
        except ExecError as e:
            if e.exit_code == 1:
                raise MigrationPendingError("running database migrations") from e
            stderr = getattr(e, "stderr", "") or ""
            if "OperationalError" in stderr or "connection" in stderr.lower():
                raise DatabaseConnectionError(
                    "database connection failed, please check credentials"
                ) from e
            raise MigrationFailedError(f"database migration failed: {stderr[:50]}") from e

    def create_recovery_key(self, username: str, duration: int) -> str:
        """Create a recovery key for the specified user and return the path.

        Args:
            username: The username of the account to recover.
            duration: The validity of the recovery link in minutes.

        Returns:
            The recovery path (e.g., /recovery/use-token/.../).

        Raises:
            ExecError: If running the command fails.
            ValueError: If the recovery token path could not be parsed from output.
        """
        # Runs `/lifecycle/ak create_recovery_key <duration> <username>`
        stdout, _ = self._run_cmd(
            ["/lifecycle/ak", "create_recovery_key", str(duration), username],
            service_context=WORKLOAD_SERVICE,
        )

        match = re.search(r"/recovery/use-token/[^/]+/?", stdout)
        if not match:
            raise ValueError(f"Failed to find recovery token path in command output: {stdout}")

        return match.group(0)

    def _run_cmd(
        self,
        cmd: list[str],
        environment: dict[str, str] | None = None,
        service_context: str | None = None,
    ) -> tuple[str, str]:
        """Run a command in the workload container.

        Args:
            cmd: The command to run.
            environment: Optional environment variables to set.
            service_context: Optional service context to run in.

        Returns:
            A tuple of (stdout, stderr).

        Raises:
            PebbleError: If the container cannot connect or command execution fails.
        """
        logger.debug("Running command in container: %s", cmd)
        process = self.container.exec(
            cmd, environment=environment, service_context=service_context
        )
        stdout, stderr = process.wait_output()
        return stdout, stderr
