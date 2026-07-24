# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Services module for the Authentik server charm."""

import copy
import logging
from functools import cached_property

from ops import Container, ModelError, Unit
from ops.pebble import CheckStatus
from ops.pebble import ConnectionError as PebbleConnectionError
from ops.pebble import Error as PebbleExecError
from ops.pebble import Layer, LayerDict

from cli import CommandLine
from constants import (
    CERTIFICATES_FILE,
    COMMAND,
    HEALTH_CHECK_URL,
    HEALTH_READY_URL,
    HTTP_PORT,
    HTTPS_PORT,
    LOCAL_CERTIFICATES_FILE,
    PEBBLE_READY_CHECK_NAME,
    WORKLOAD_CONTAINER,
    WORKLOAD_SERVICE,
)
from env_vars import DEFAULT_SERVER_ENV, EnvVarConvertible
from exceptions import (
    PebbleError,
    ServiceBackoffError,
    WorkloadNotRunningError,
)

logger = logging.getLogger(__name__)

PEBBLE_LAYER_DICT: LayerDict = {
    "summary": "authentik-server-operator layer",
    "description": "pebble config layer for authentik-server-operator",
    "services": {
        WORKLOAD_SERVICE: {
            "override": "replace",
            "summary": "Authentik server",
            "command": COMMAND,
            "startup": "disabled",
        }
    },
    "checks": {
        "alive": {
            "override": "replace",
            "level": "alive",
            # A threshold of 10 attempts (at the standard 10s interval) provides 100 seconds
            # of grace period for database migrations and service warmup during startup,
            # preventing premature container restarts while maintaining reliable deadlock detection.
            "threshold": 15,
            "http": {
                "url": HEALTH_CHECK_URL,
            },
        },
        PEBBLE_READY_CHECK_NAME: {
            "override": "replace",
            "level": "ready",
            "timeout": "10s",
            "threshold": 3,
            "http": {
                "url": HEALTH_READY_URL,
            },
        },
    },
}


class WorkloadService:
    """Workload service abstraction running in a Juju unit."""

    def __init__(self, unit: Unit) -> None:
        self._unit = unit
        self._container: Container = unit.get_container(WORKLOAD_CONTAINER)
        self._cli = CommandLine(self._container)

    @cached_property
    def version(self) -> str:
        """The workload version via pebble exec (cached for the unit's lifetime)."""
        return self._cli.get_version()

    def set_version(self) -> None:
        """Set the workload version on the Juju unit."""
        try:
            self._unit.set_workload_version(self.version)
        except PebbleExecError as e:
            logger.error("Failed to set workload version: %s", e)

    def open_port(self) -> None:
        """Open the HTTP and HTTPS ports on the Juju unit."""
        self._unit.open_port(protocol="tcp", port=HTTP_PORT)
        self._unit.open_port(protocol="tcp", port=HTTPS_PORT)

    def is_running(self) -> bool:
        """Check if the workload service is running and healthy."""
        try:
            service = self._container.get_service(WORKLOAD_SERVICE)
        except (ModelError, PebbleConnectionError) as e:
            logger.error("Failed to get pebble service: %s", e)
            return False
        if not service.is_running():
            return False
        checks = self._container.get_checks()
        ready_check = checks.get(PEBBLE_READY_CHECK_NAME)
        if not ready_check:
            return False
        return ready_check.status == CheckStatus.UP and (ready_check.successes or 0) > 0

    def is_failing(self) -> bool:
        """Check if the workload service health check is failing."""
        try:
            service = self._container.get_service(WORKLOAD_SERVICE)
        except (ModelError, PebbleConnectionError):
            return False
        # service.current is typically an ops.pebble.ServiceStatus enum member.
        # However, for newer or unmapped Pebble states (such as "backoff"), ops might fall back
        # to a raw string instead of an enum. We handle this defensively using hasattr.
        current_str = (
            service.current.value if hasattr(service.current, "value") else service.current
        )
        if str(current_str).lower() in ("backoff", "error"):
            return True
        if not service.is_running():
            return False
        checks = self._container.get_checks()
        ready_check = checks.get(PEBBLE_READY_CHECK_NAME)
        if not ready_check:
            return False
        return ready_check.status == CheckStatus.DOWN

    def check_health(self) -> None:
        """Validate health and run diagnostics, raising custom exceptions on failure.

        Raises:
            ServiceBackoffError: If the service is in backoff/error.
            DatabaseConnectionError: If the database connection failed.
            MigrationPendingError: If migrations are currently running.
            MigrationFailedError: If database migration failed.
            WorkloadNotRunningError: If the workload service is not running.
        """
        try:
            service = self._container.get_service(WORKLOAD_SERVICE)
        except (ModelError, PebbleConnectionError) as e:
            raise WorkloadNotRunningError("Failed to connect to Pebble") from e

        current_str = (
            service.current.value if hasattr(service.current, "value") else service.current
        )
        if str(current_str).lower() in ("backoff", "error"):
            raise ServiceBackoffError("Service is in backoff/error")

        if not service.is_running():
            raise WorkloadNotRunningError("Service is not running")

        checks = self._container.get_checks()
        ready_check = checks.get(PEBBLE_READY_CHECK_NAME)
        if not ready_check:
            raise WorkloadNotRunningError("Pebble ready check not found")

        if ready_check.status == CheckStatus.DOWN:
            self._cli.check_migrations()

        if ready_check.status != CheckStatus.UP or (ready_check.successes or 0) == 0:
            raise WorkloadNotRunningError("Service is starting up")

    def create_recovery_link(self, username: str, duration: int) -> str:
        """Create a recovery key for the specified user and return the path.

        Args:
            username: The username of the account to recover.
            duration: The validity of the recovery link in minutes.

        Returns:
            The recovery path.
        """
        return self._cli.create_recovery_key(username, duration)

    def update_ca_certs(self) -> bool:
        """Update the CA certificates in the workload container.

        Returns:
            True if the certificate bundle was updated, False if it was already current.
        """
        ca_certs = LOCAL_CERTIFICATES_FILE.read_text() if LOCAL_CERTIFICATES_FILE.exists() else ""
        current = (
            self._container.pull(CERTIFICATES_FILE).read()
            if self._container.exists(CERTIFICATES_FILE)
            else ""
        )
        if current == ca_certs:
            return False
        self._container.push(CERTIFICATES_FILE, ca_certs, make_dirs=True)
        return True


class PebbleService:
    """Manages the workload Pebble layer for the Authentik server.

    Args:
        unit: The Juju unit owning the workload container.
    """

    def __init__(self, unit: Unit) -> None:
        self._unit = unit
        self._container = unit.get_container(WORKLOAD_CONTAINER)
        self._layer_dict: LayerDict = copy.deepcopy(PEBBLE_LAYER_DICT)

    def _restart_service(self, restart: bool = False) -> None:
        """Restart or start the pebble service.

        Args:
            restart: If True, force a restart. Otherwise, start or replan.
        """
        if restart:
            self._container.restart(WORKLOAD_SERVICE)
        elif not self._container.get_service(WORKLOAD_SERVICE).is_running():
            self._container.start(WORKLOAD_SERVICE)
        else:
            self._container.replan()

    def plan(self, layer: Layer, force_restart: bool = False) -> None:
        """Apply a Pebble layer and restart the workload service.

        Args:
            layer: The Pebble layer to apply.
            force_restart: If True, restart the service even if the layer is unchanged.

        Raises:
            PebbleError: If the service fails to start.
        """
        self._container.add_layer(WORKLOAD_SERVICE, layer, combine=True)
        try:
            self._restart_service(restart=force_restart)
        except Exception as e:
            raise PebbleError(f"Pebble failed to restart the workload service. Error: {e}")

    def render_pebble_layer(self, *env_var_sources: EnvVarConvertible) -> Layer:
        """Render a Pebble layer merging env vars from all sources.

        Precedence: DEFAULT_SERVER_ENV is the base; each successive source's
        ``to_env_vars()`` output is merged on top (last one wins).
        Intended order (lowest → highest priority): database, secrets, config.

        Args:
            *env_var_sources: Objects implementing EnvVarConvertible.

        Returns:
            The rendered Pebble Layer.
        """
        env_vars: dict[str, str | bool] = dict(DEFAULT_SERVER_ENV)
        for source in env_var_sources:
            env_vars.update(source.to_env_vars())
        self._layer_dict["services"][WORKLOAD_SERVICE]["environment"] = env_vars
        return Layer(self._layer_dict)
