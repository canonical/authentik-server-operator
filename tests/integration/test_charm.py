# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the Authentik Server charm."""

import logging
from pathlib import Path
from typing import Callable

import jubilant
import pytest
import requests
from integration.conftest import integrate_dependencies
from integration.constants import (
    APP_IMAGE,
    APP_NAME,
    DB_APP,
    DB_CHANNEL,
    WORKER_APP,
    WORKER_CHANNEL,
)
from integration.utils import (
    StatusPredicate,
    all_active,
    and_,
    any_error,
    is_blocked,
    remove_integration,
    unit_number,
)

from src.constants import CLUSTER_RELATION, DATABASE_RELATION

logger = logging.getLogger(__name__)


@pytest.mark.juju_setup
def test_build_and_deploy(juju: jubilant.Juju, charm: Path) -> None:
    """Build and deploy the charm-under-test together with related charms."""
    juju.deploy(
        DB_APP,
        channel=DB_CHANNEL,
        trust=True,
    )

    juju.deploy(
        WORKER_APP,
        channel=WORKER_CHANNEL,
        trust=True,
    )

    juju.deploy(
        str(charm),
        app=APP_NAME,
        resources={"oci-image": APP_IMAGE},
        trust=True,
    )

    integrate_dependencies(juju)

    juju.wait(
        ready=all_active(APP_NAME, DB_APP, WORKER_APP),
        error=any_error(APP_NAME, DB_APP, WORKER_APP),
        timeout=15 * 60,
    )


def test_app_health(
    juju: jubilant.Juju,
    public_address: str,
    http_client: requests.Session,
) -> None:
    """Test workload health endpoint is accessible."""
    resp = http_client.get(f"http://{public_address}:9000/-/health/live/")
    resp.raise_for_status()


def test_scale_up(juju: jubilant.Juju) -> None:
    """Test scaling up to verify HA and leader election."""
    target_unit_number = 2
    juju.cli("scale-application", APP_NAME, str(target_unit_number))

    juju.wait(
        ready=and_(
            all_active(APP_NAME),
            unit_number(APP_NAME, target_unit_number),
        ),
        error=any_error(APP_NAME),
        timeout=5 * 60,
    )


@pytest.mark.parametrize(
    "remote_app_name,integration_name,is_status",
    [
        (DB_APP, DATABASE_RELATION, is_blocked),
        (WORKER_APP, CLUSTER_RELATION, is_blocked),
    ],
)
def test_remove_integration(
    juju: jubilant.Juju,
    remote_app_name: str,
    integration_name: str,
    is_status: Callable[[str], StatusPredicate],
) -> None:
    """Test removing and re-adding integration."""
    with remove_integration(juju, remote_app_name, integration_name):
        juju.wait(
            ready=is_status(APP_NAME),
            error=any_error(APP_NAME),
            timeout=10 * 60,
        )
    juju.wait(
        ready=all_active(APP_NAME, remote_app_name),
        error=any_error(APP_NAME, remote_app_name),
        timeout=10 * 60,
    )


def test_scale_down(juju: jubilant.Juju) -> None:
    """Test scaling down to verify cluster stability."""
    target_unit_num = 1
    juju.cli("scale-application", APP_NAME, str(target_unit_num))

    juju.wait(
        ready=and_(
            all_active(APP_NAME),
            unit_number(APP_NAME, target_unit_num),
        ),
        error=any_error(APP_NAME),
        timeout=5 * 60,
    )


@pytest.mark.juju_teardown
def test_remove_application(juju: jubilant.Juju) -> None:
    """Test removing the application."""
    juju.remove_application(APP_NAME, destroy_storage=True)
    juju.wait(lambda s: APP_NAME not in s.apps, timeout=1000)
