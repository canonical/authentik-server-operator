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


class AuthentikAPIError(Exception):
    """Base class for Authentik API errors that must fail reconciliation."""


class AuthentikNotFoundError(AuthentikAPIError):
    """An Authentik resource does not exist."""


class AuthentikAuthenticationError(AuthentikAPIError):
    """Authentik rejected the API credentials."""


class AuthentikAuthorizationError(AuthentikAPIError):
    """The API credentials cannot perform the requested operation."""


class AuthentikConflictError(AuthentikAPIError):
    """The Authentik request conflicts with existing state."""


class AuthentikTransientError(AuthentikAPIError):
    """A transient Authentik transport or server failure exhausted its retry budget."""


class AuthentikRequestValidationError(AuthentikAPIError):
    """Authentik rejected a permanently invalid request."""
