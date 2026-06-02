# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Services module for the Authentik server charm."""

import copy
import logging

from constants import (
    COMMAND,
    HEALTH_CHECK_URL,
    HTTP_PORT,
    HTTPS_PORT,
    SERVICE_NAME,
    WORKLOAD_CONTAINER,
)
from env_vars import DEFAULT_SERVER_ENV, EnvVarConvertible
from exceptions import PebbleError
from ops import Unit
from ops.pebble import Layer, LayerDict

logger = logging.getLogger(__name__)

PEBBLE_LAYER_DICT: LayerDict = {
    "services": {
        SERVICE_NAME: {
            "override": "replace",
            "summary": "Authentik server",
            "command": COMMAND,
            "startup": "enabled",
        }
    },
    "checks": {
        "health": {
            "override": "replace",
            "level": "alive",
            "http": {
                "url": HEALTH_CHECK_URL,
            },
        }
    },
}


class PebbleService:
    """Manages the workload Pebble layer for the Authentik server.

    Args:
        unit: The Juju unit owning the workload container.
    """

    def __init__(self, unit: Unit) -> None:
        self._unit = unit
        self._container = unit.get_container(WORKLOAD_CONTAINER)
        self._layer_dict: LayerDict = copy.deepcopy(PEBBLE_LAYER_DICT)

    def plan(self, layer: Layer) -> None:
        """Apply a Pebble layer and replan the container.

        Args:
            layer: The Pebble layer to apply.

        Raises:
            PebbleError: If the service fails to start.
        """
        self._container.add_layer(SERVICE_NAME, layer, combine=True)
        try:
            self._container.replan()
        except Exception as e:
            raise PebbleError(f"Pebble failed to replan the workload service. Error: {e}")

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
        self._layer_dict["services"][SERVICE_NAME]["environment"] = env_vars
        self._layer_dict["services"][SERVICE_NAME]["environment"][
            "AUTHENTIK_LISTEN__HTTP"
        ] = f"0.0.0.0:{HTTP_PORT}"
        self._layer_dict["services"][SERVICE_NAME]["environment"][
            "AUTHENTIK_LISTEN__HTTPS"
        ] = f"0.0.0.0:{HTTPS_PORT}"
        return Layer(self._layer_dict)
