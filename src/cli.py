# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helper class to access the Authentik CLI and management tools."""

import logging

from ops import Container
from ops.pebble import ExecError

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
        # Run `/lifecycle/ak version` to fetch the Authentik version
        try:
            stdout, _ = self._run_cmd(["/lifecycle/ak", "version"])
            return stdout.strip()
        except Exception as err:
            logger.warning(
                "Failed to fetch the service version via CLI: %s. Falling back to python import check.",
                err,
            )
            # Fallback to the Python import method if the CLI version command fails
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
            except Exception as fallback_err:
                logger.error(
                    "Failed to fetch the service version via Python fallback: %s", fallback_err
                )
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
                    "authentik.manage",
                    "migrate",
                    "--check",
                ],
                environment={"PYTHONPATH": "/"},
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

    def _run_cmd(
        self, cmd: list[str], environment: dict[str, str] | None = None
    ) -> tuple[str, str]:
        """Run a command in the workload container.

        Args:
            cmd: The command to run.
            environment: Optional environment variables to set.

        Returns:
            A tuple of (stdout, stderr).

        Raises:
            PebbleError: If the container cannot connect or command execution fails.
        """
        logger.debug("Running command in container: %s", cmd)
        process = self.container.exec(cmd, environment=environment)
        stdout, stderr = process.wait_output()
        return stdout, stderr
