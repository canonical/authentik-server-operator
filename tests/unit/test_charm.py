# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the Authentik Server charm."""

from charm import AuthentikServerCharm
from constants import HEALTH_CHECK_URL, SERVICE_NAME, WORKLOAD_CONTAINER
from ops import pebble, testing


def _pebble_layer(env: dict[str, str] | None = None) -> pebble.Layer:
    if env is None:
        env = {
            "AUTHENTIK_POSTGRESQL__HOST": "test-host",
            "AUTHENTIK_POSTGRESQL__PORT": "5432",
            "AUTHENTIK_POSTGRESQL__USER": "test-user",
            "AUTHENTIK_POSTGRESQL__PASSWORD": "test-pass",
            "AUTHENTIK_POSTGRESQL__NAME": "authentik",
            "AUTHENTIK_SECRET_KEY": "test-secret-key",
            "AUTHENTIK_BOOTSTRAP_TOKEN": "test-bootstrap-token",
            "AUTHENTIK_BOOTSTRAP_PASSWORD": "test-bootstrap-password",
            "AUTHENTIK_LISTEN__HTTP": "0.0.0.0:9000",
            "AUTHENTIK_LISTEN__HTTPS": "0.0.0.0:9443",
            "AUTHENTIK_ERROR_REPORTING__ENABLED": "false",
            "AUTHENTIK_LOG_LEVEL": "info",
        }
    return pebble.Layer(
        {
            "services": {
                SERVICE_NAME: {
                    "override": "replace",
                    "summary": "Authentik server",
                    "command": "ak server",
                    "startup": "enabled",
                    "environment": env,
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
    )


def test_container_cannot_connect():
    """Test status is WaitingStatus when pebble is not ready."""
    ctx = testing.Context(AuthentikServerCharm)
    container = testing.Container(WORKLOAD_CONTAINER, can_connect=False)
    state_in = testing.State(containers={container})

    state_out = ctx.run(ctx.on.install(), state_in)

    assert state_out.unit_status == testing.WaitingStatus("waiting for pebble")


def test_missing_database_relation():
    """Test status is BlockedStatus when pg-database is missing."""
    ctx = testing.Context(AuthentikServerCharm)
    container = testing.Container(WORKLOAD_CONTAINER, can_connect=True)
    state_in = testing.State(containers={container})

    state_out = ctx.run(ctx.on.collect_unit_status(), state_in)

    assert state_out.unit_status == testing.BlockedStatus("missing pg-database relation")


def test_waiting_for_secrets():
    """Test status is WaitingStatus when secrets are not yet generated."""
    ctx = testing.Context(AuthentikServerCharm)
    container = testing.Container(WORKLOAD_CONTAINER, can_connect=True)
    relation = testing.Relation(
        "pg-database",
        testing.RelationEndpoint("authentik-server", "pg-database", role="requires"),
        remote_app_data={
            "database": "authentik",
            "endpoints": "test-host:5432",
            "username": "test-user",
            "password": "test-pass",
        },
    )
    state_in = testing.State(
        containers={container},
        relations={relation},
    )

    state_out = ctx.run(ctx.on.collect_unit_status(), state_in)

    assert state_out.unit_status == testing.WaitingStatus("waiting for secrets")


def test_active_status():
    """Test status is ActiveStatus when all prerequisites are met."""
    ctx = testing.Context(AuthentikServerCharm)
    container = testing.Container(WORKLOAD_CONTAINER, can_connect=True)
    db_relation = testing.Relation(
        "pg-database",
        testing.RelationEndpoint("authentik-server", "pg-database", role="requires"),
        remote_app_data={
            "database": "authentik",
            "endpoints": "test-host:5432",
            "username": "test-user",
            "password": "test-pass",
        },
    )
    peer_relation = testing.Relation(
        "authentik-peers",
        testing.RelationEndpoint("authentik-server", "authentik-peers"),
        local_app_data={"secret_key_secret_id": "secret:test"},
    )
    state_in = testing.State(
        containers={container},
        relations={db_relation, peer_relation},
    )

    state_out = ctx.run(ctx.on.collect_unit_status(), state_in)

    assert state_out.unit_status == testing.ActiveStatus()


def test_pebble_layer_applied():
    """Test that the correct pebble layer is applied when all prerequisites are met."""
    ctx = testing.Context(AuthentikServerCharm)
    container = testing.Container(WORKLOAD_CONTAINER, can_connect=True)
    db_relation = testing.Relation(
        "pg-database",
        testing.RelationEndpoint("authentik-server", "pg-database", role="requires"),
        remote_app_data={
            "database": "authentik",
            "endpoints": "test-host:5432",
            "username": "test-user",
            "password": "test-pass",
        },
    )
    peer_relation = testing.Relation(
        "authentik-peers",
        testing.RelationEndpoint("authentik-server", "authentik-peers"),
        local_app_data={
            "secret_key_secret_id": "secret://test",
            "bootstrap_token_secret_id": "secret://test",
            "bootstrap_password_secret_id": "secret://test",
        },
    )
    state_in = testing.State(
        containers={container},
        relations={db_relation, peer_relation},
    )
    state_out = ctx.run(ctx.on.install(), state_in)
    container_out = state_out.get_container(WORKLOAD_CONTAINER)

    assert len(container_out.layers) == 1
