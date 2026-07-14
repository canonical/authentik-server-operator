# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Utility functions."""

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

from constants import DATABASE_RELATION, TRAEFIK_ROUTE_RELATION, WORKLOAD_CONTAINER
from integrations import TraefikRouteIntegration

if TYPE_CHECKING:
    from charm import AuthentikServerCharm

logger = logging.getLogger(__name__)

CharmEventHandler = TypeVar("CharmEventHandler", bound=Callable[..., Any])
Condition = Callable[["AuthentikServerCharm"], bool]


def container_connectivity(charm: "AuthentikServerCharm") -> bool:
    """Check if the workload container is reachable."""
    return charm.unit.get_container(WORKLOAD_CONTAINER).can_connect()


def database_integration_exists(charm: "AuthentikServerCharm") -> bool:
    """Check if the pg-database relation exists."""
    return bool(charm.model.relations[DATABASE_RELATION])


def database_resource_is_created(charm: "AuthentikServerCharm") -> bool:
    """Check if the database resource has been created."""
    return charm.database.is_resource_created()


def traefik_route_integration_exists(charm: "AuthentikServerCharm") -> bool:
    """Check if the traefik-route relation exists."""
    return bool(charm.model.relations[TRAEFIK_ROUTE_RELATION])


def traefik_route_is_ready(charm: "AuthentikServerCharm") -> bool:
    """Check if the traefik-route integration is ready with an external host."""
    return bool(TraefikRouteIntegration.load(charm.traefik_route).external_host)


def traefik_route_is_secure(charm: "AuthentikServerCharm") -> bool:
    """Check if the traefik-route integration is secure."""
    return TraefikRouteIntegration.load(charm.traefik_route).secure


NOOP_CONDITIONS: tuple[Condition, ...] = (
    container_connectivity,
    database_integration_exists,
    database_resource_is_created,
    traefik_route_integration_exists,
)
