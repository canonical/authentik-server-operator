# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

import os
import pathlib
import subprocess
from pathlib import Path
from typing import Generator

import jubilant
import pytest
import requests
from integration.constants import APP_NAME, DB_APP, WORKER_APP
from integration.utils import get_unit_address

from src.constants import CLUSTER_RELATION


@pytest.fixture(scope="session")
def charm() -> Path:
    """Return the path of the charm under test."""
    if "CHARM_PATH" in os.environ:
        charm_path = pathlib.Path(os.environ["CHARM_PATH"])
        if not charm_path.exists():
            raise FileNotFoundError(f"Charm does not exist: {charm_path}")
        return charm_path
    subprocess.run(["charmcraft", "pack"], check=True)
    if not (charms := list(Path(".").glob("*.charm"))):
        raise RuntimeError("Charm not found and build failed")
    return charms[0].absolute()


@pytest.fixture
def http_client() -> Generator[requests.Session, None, None]:
    """Provide an HTTP client with TLS verification disabled."""
    with requests.Session() as client:
        client.verify = False
        yield client


def integrate_dependencies(juju: jubilant.Juju) -> None:
    """Integrate the charm with all required dependencies."""
    juju.integrate(DB_APP, APP_NAME)
    juju.integrate(f"{APP_NAME}:{CLUSTER_RELATION}", WORKER_APP)


@pytest.fixture
def public_address(juju: jubilant.Juju) -> str:
    """Return the public address of the authentik-server unit."""
    return get_unit_address(juju, app_name=APP_NAME)
