# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the Authentik Server charm."""

import json
import logging
import platform
from pathlib import Path
from typing import Callable

import jubilant
import pytest
import requests
from integration.conftest import integrate_dependencies
from integration.constants import (
    APP_IMAGE,
    APP_NAME,
    CERTIFICATES_APP,
    CERTIFICATES_CHANNEL,
    DB_APP,
    DB_CHANNEL,
    TRAEFIK_APP,
    TRAEFIK_CHANNEL,
    WORKER_APP,
    WORKER_CHANNEL,
)
from integration.utils import (
    StatusPredicate,
    all_active,
    and_,
    any_error,
    get_app_integration_data,
    is_blocked,
    remove_integration,
    unit_number,
)

from src.constants import CLUSTER_RELATION, DATABASE_RELATION, TRAEFIK_ROUTE_RELATION

logger = logging.getLogger(__name__)


@pytest.mark.juju_setup
def test_build_and_deploy(juju: jubilant.Juju, charm: Path) -> None:
    """Build and deploy the charm-under-test together with related charms."""
    # Set model constraints dynamically based on native host architecture
    arch_map = {
        "aarch64": "arm64",
        "arm64": "arm64",
        "x86_64": "amd64",
        "amd64": "amd64",
    }
    host_arch = arch_map.get(platform.machine().lower(), "amd64")
    juju.cli("set-model-constraints", f"arch={host_arch}")

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
        TRAEFIK_APP,
        channel=TRAEFIK_CHANNEL,
        config={"external_hostname": "authentik.example.com"},
        trust=True,
    )

    juju.deploy(
        CERTIFICATES_APP,
        channel=CERTIFICATES_CHANNEL,
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
        ready=all_active(APP_NAME, DB_APP, WORKER_APP, TRAEFIK_APP, CERTIFICATES_APP),
        error=any_error(APP_NAME, DB_APP, WORKER_APP, TRAEFIK_APP, CERTIFICATES_APP),
        timeout=20 * 60,
    )


def test_app_health(
    juju: jubilant.Juju,
    public_address: str,
    http_client: requests.Session,
) -> None:
    """Test workload health endpoint is accessible."""
    resp = http_client.get(f"http://{public_address}:9000/-/health/live/")
    resp.raise_for_status()


def test_traefik_route_integration(juju: jubilant.Juju) -> None:
    """Test that the Traefik Route integration configures routing rules correctly."""
    relation_data = get_app_integration_data(juju, TRAEFIK_APP, "traefik-route")
    assert relation_data
    assert "config" in relation_data
    config_yaml = relation_data["config"]
    assert "PathPrefix" in config_yaml
    assert "authentik.example.com" in config_yaml


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


def test_admin_actions(juju: jubilant.Juju) -> None:
    """Test get-admin-credentials and create-recovery-link actions."""
    # Run get-admin-credentials action
    output_str = juju.cli("run", f"{APP_NAME}/0", "get-admin-credentials", "--format=json")
    try:
        results = json.loads(output_str)
    except Exception:
        results = output_str

    if isinstance(results, dict):
        unit_results = results.get(f"{APP_NAME}/0", {}).get("results", {})
        if not unit_results and "results" in results:
            unit_results = results["results"]
        if not unit_results:
            unit_results = results
    else:
        unit_results = {}

    assert unit_results.get("username") == "akadmin", (
        f"Expected username 'akadmin', got results: {results}"
    )
    assert "password" in unit_results
    assert "bootstrap-token" in unit_results
    assert "warning" in unit_results

    # Run create-recovery-link action with custom parameters
    output_str = juju.cli(
        "run",
        f"{APP_NAME}/0",
        "create-recovery-link",
        "username=akadmin",
        "duration=15",
        "--format=json",
    )
    try:
        results = json.loads(output_str)
    except Exception:
        results = output_str

    if isinstance(results, dict):
        unit_results = results.get(f"{APP_NAME}/0", {}).get("results", {})
        if not unit_results and "results" in results:
            unit_results = results["results"]
        if not unit_results:
            unit_results = results
    else:
        unit_results = {}

    assert unit_results.get("status") == "success", (
        f"Expected status 'success', got results: {results}"
    )
    assert "url" in unit_results
    assert "path" in unit_results
    assert "/recovery/use-token/" in unit_results["path"]


@pytest.mark.parametrize(
    "remote_app_name,integration_name,is_status",
    [
        (DB_APP, DATABASE_RELATION, is_blocked),
        (WORKER_APP, CLUSTER_RELATION, is_blocked),
        ("traefik-k8s", TRAEFIK_ROUTE_RELATION, is_blocked),
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
