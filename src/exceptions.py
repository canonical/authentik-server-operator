# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Exceptions."""


class CharmError(Exception):
    """Base class for custom charm errors."""


class PebbleError(CharmError):
    """Error for pebble related operations."""


class SecretError(CharmError):
    """Error for secret-related operations."""


class WorkloadNotRunningError(CharmError):
    """The workload service is not running."""


class ServiceBackoffError(CharmError):
    """The workload service is in backoff or error state."""


class DatabaseConnectionError(CharmError):
    """Database connection failed."""


class MigrationPendingError(CharmError):
    """Database migrations are currently running."""


class MigrationFailedError(CharmError):
    """Database migrations failed."""
