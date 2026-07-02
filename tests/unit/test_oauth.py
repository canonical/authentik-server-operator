# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the OAuth relation."""

import json
from unittest.mock import MagicMock

import pytest
from ops import testing
from pytest_mock import MockerFixture
from unit.conftest import create_state

from constants import OAUTH_RELATION_NAME


@pytest.fixture(autouse=True)
def mock_authentik_api(mocker: MockerFixture):
    """Fixture to mock AuthentikAPI globally to avoid live HTTP requests in unit tests."""
    mock_api_class = mocker.patch("charm.AuthentikAPI", autospec=True)
    mock_api_instance = mock_api_class.return_value

    # Setup standard mocked responses
    mock_api_instance.is_service_available.return_value = True
    mock_api_instance.get_authorization_flow_uuid.return_value = "test-flow-uuid"
    mock_api_instance.get_property_mappings.return_value = ["mapping-1", "mapping-2"]
    mock_api_instance.get_application.return_value = None  # Default to not existing yet
    mock_api_instance.create_oauth_provider.return_value = 123
    mock_api_instance.create_application.return_value = True
    mock_api_instance.list_applications.return_value = []
    mock_api_instance.update_oauth_provider.return_value = True
    mock_api_instance.update_application.return_value = True
    mock_api_instance.delete_oauth_provider.return_value = True
    mock_api_instance.delete_application.return_value = True

    return mock_api_instance


def test_oauth_client_created_leader(
    context: testing.Context,
    db_relation: testing.Relation,
    peer_relation: testing.PeerRelation,
    cluster_relation: testing.Relation,
    authentik_secrets: testing.Secret,
    all_satisfied_conditions: None,
) -> None:
    """Test that a leader generates credentials on client_created."""
    oauth_relation = testing.Relation(
        endpoint=OAUTH_RELATION_NAME,
        interface="oauth",
        remote_app_name="client-app",
    )
    state = create_state(
        leader=True,
        relations=[db_relation, peer_relation, cluster_relation, oauth_relation],
        secrets=[authentik_secrets],
    )

    # 1. Trigger relation_created to populate provider endpoints
    state_out = context.run(context.on.relation_created(oauth_relation), state)

    rel_out = state_out.get_relation(oauth_relation.id)
    assert "issuer_url" in rel_out.local_app_data

    # 2. Trigger relation_changed with the client config to simulate registration
    oauth_relation_with_config = testing.Relation(
        endpoint=OAUTH_RELATION_NAME,
        interface="oauth",
        id=oauth_relation.id,
        remote_app_name="client-app",
        remote_app_data={
            "redirect_uri": "https://client.example.com/oauth/callback",
            "scope": "openid email",
            "grant_types": json.dumps(["authorization_code"]),
            "token_endpoint_auth_method": "client_secret_basic",
            "audience": json.dumps([]),
        },
        local_app_data=rel_out.local_app_data,
    )
    next_state = create_state(
        leader=True,
        relations=[db_relation, peer_relation, cluster_relation, oauth_relation_with_config],
        secrets=[authentik_secrets],
    )
    state_out = context.run(context.on.relation_changed(oauth_relation_with_config), next_state)

    # Check that client credentials are populated in the relation data
    rel_out = state_out.get_relation(oauth_relation.id)
    assert "client_id" in rel_out.local_app_data
    assert "client_secret_id" in rel_out.local_app_data

    # Check standard OIDC endpoints are updated correctly
    # By default, since no ingress is ready, it should fall back to local cluster address
    assert "issuer_url" in rel_out.local_app_data
    assert "authorization_endpoint" in rel_out.local_app_data
    assert "token_endpoint" in rel_out.local_app_data
    assert "jwks_endpoint" in rel_out.local_app_data
    assert (
        rel_out.local_app_data["issuer_url"]
        == f"http://authentik-server.test-model.svc.cluster.local:9000/application/o/client-app-{oauth_relation.id}/"
    )


def test_oauth_client_created_non_leader(
    context: testing.Context,
    db_relation: testing.Relation,
    peer_relation: testing.PeerRelation,
    cluster_relation: testing.Relation,
    authentik_secrets: testing.Secret,
    all_satisfied_conditions: None,
) -> None:
    """Test that a non-leader does not generate credentials."""
    oauth_relation = testing.Relation(
        endpoint=OAUTH_RELATION_NAME,
        interface="oauth",
        remote_app_name="client-app",
        local_app_data={
            "issuer_url": "http://dummy/application/o/identity-platform/",
            "authorization_endpoint": "http://dummy/application/o/authorize/",
            "token_endpoint": "http://dummy/application/o/token/",
            "introspection_endpoint": "http://dummy/application/o/introspect/",
            "userinfo_endpoint": "http://dummy/application/o/userinfo/",
            "jwks_endpoint": "http://dummy/application/o/identity-platform/jwks/",
            "scope": "openid email profile",
            "jwt_access_token": "False",
        },
        remote_app_data={
            "redirect_uri": "https://client.example.com/oauth/callback",
            "scope": "openid email",
            "grant_types": json.dumps(["authorization_code"]),
            "token_endpoint_auth_method": "client_secret_basic",
            "audience": json.dumps([]),
        },
    )
    state = create_state(
        leader=False,
        relations=[db_relation, peer_relation, cluster_relation, oauth_relation],
        secrets=[authentik_secrets],
    )

    state_out = context.run(context.on.relation_changed(oauth_relation), state)

    rel_out = state_out.get_relation(oauth_relation.id)
    assert "client_id" not in rel_out.local_app_data
    assert "client_secret_id" not in rel_out.local_app_data


def test_oauth_endpoints_update_on_ingress_change(
    context: testing.Context,
    db_relation: testing.Relation,
    peer_relation: testing.PeerRelation,
    cluster_relation: testing.Relation,
    authentik_secrets: testing.Secret,
    all_satisfied_conditions: None,
) -> None:
    """Test that OIDC endpoints are updated dynamically when ingress hostname changes."""
    oauth_relation = testing.Relation(
        endpoint=OAUTH_RELATION_NAME,
        interface="oauth",
        remote_app_name="client-app",
        # Already has client credentials populated in local app data
        local_app_data={
            "client_id": "test-client-id",
            "client_secret_id": "secret:123",
        },
    )
    # Define Traefik ingress relation with a specific URL
    ingress_relation = testing.Relation(
        endpoint="ingress",
        interface="ingress",
        remote_app_name="traefik",
        remote_app_data={
            "ingress": json.dumps({"url": "https://authentik.mycompany.org"}),
        },
    )
    state = create_state(
        leader=True,
        relations=[db_relation, peer_relation, cluster_relation, oauth_relation, ingress_relation],
        secrets=[authentik_secrets],
    )

    # Run any event to trigger reconciliation (e.g. config_changed)
    state_out = context.run(context.on.config_changed(), state)

    rel_out = state_out.get_relation(oauth_relation.id)
    assert (
        rel_out.local_app_data["issuer_url"]
        == f"https://authentik.mycompany.org/application/o/client-app-{oauth_relation.id}/"
    )
    assert (
        rel_out.local_app_data["authorization_endpoint"]
        == "https://authentik.mycompany.org/application/o/authorize/"
    )
    assert (
        rel_out.local_app_data["token_endpoint"]
        == "https://authentik.mycompany.org/application/o/token/"
    )
    assert (
        rel_out.local_app_data["jwks_endpoint"]
        == f"https://authentik.mycompany.org/application/o/client-app-{oauth_relation.id}/jwks/"
    )


def test_oauth_relation_broken(
    context: testing.Context,
    db_relation: testing.Relation,
    peer_relation: testing.PeerRelation,
    cluster_relation: testing.Relation,
    authentik_secrets: testing.Secret,
    all_satisfied_conditions: None,
    mock_authentik_api: MagicMock,
) -> None:
    """Test that relation_broken triggers garbage collection of Authentik objects."""
    oauth_relation = testing.Relation(
        endpoint=OAUTH_RELATION_NAME,
        interface="oauth",
        remote_app_name="client-app",
        local_app_data={
            "client_id": "test-client-id",
            "client_secret_id": "secret:123",
        },
    )
    state = create_state(
        leader=True,
        relations=[db_relation, peer_relation, cluster_relation, oauth_relation],
        secrets=[authentik_secrets],
    )

    # Mock list_applications to return an application matching our slug format with provider info
    mock_authentik_api.list_applications.return_value = [
        {
            "name": f"client-app (Relation {oauth_relation.id})",
            "slug": f"client-app-{oauth_relation.id}",
            "provider": 123,
        }
    ]

    # Trigger relation_broken
    context.run(context.on.relation_broken(oauth_relation), state)

    # Verify that the API delete methods were called for the broken relation slug and provider ID
    mock_authentik_api.delete_oauth_provider.assert_called_once_with(123)
    mock_authentik_api.delete_application.assert_called_once_with(
        f"client-app-{oauth_relation.id}"
    )


def test_oauth_leader_election_heals_unprovisioned_relation(
    context: testing.Context,
    db_relation: testing.Relation,
    peer_relation: testing.PeerRelation,
    cluster_relation: testing.Relation,
    authentik_secrets: testing.Secret,
    all_satisfied_conditions: None,
    mock_authentik_api: MagicMock,
) -> None:
    """Test that leader promotion triggers self-healing credentials and API provisioning."""
    # 1. State representing when this unit was a follower
    # The relation has been joined, the remote unit provided redirect_uri
    # but since leader=False, no client_id or client_secret were generated or registered.
    oauth_relation = testing.Relation(
        endpoint=OAUTH_RELATION_NAME,
        interface="oauth",
        remote_app_name="client-app",
        remote_app_data={
            "redirect_uri": "https://client.example.com/oauth/callback",
            "scope": "openid email",
            "grant_types": json.dumps(["authorization_code"]),
            "token_endpoint_auth_method": "client_secret_basic",
            "audience": json.dumps([]),
        },
    )
    state = create_state(
        leader=False,
        relations=[db_relation, peer_relation, cluster_relation, oauth_relation],
        secrets=[authentik_secrets],
    )

    # 2. Trigger a relation_changed event as a follower: no credentials should be generated
    state_out = context.run(context.on.relation_changed(oauth_relation), state)
    rel_out = state_out.get_relation(oauth_relation.id)
    assert "client_id" not in rel_out.local_app_data

    # 3. Simulate leader election (leader=True) and run the leader_elected event
    promoted_state = create_state(
        leader=True,
        relations=[db_relation, peer_relation, cluster_relation, rel_out],
        secrets=[authentik_secrets],
    )

    # Trigger leader_elected event
    state_after_promotion = context.run(context.on.leader_elected(), promoted_state)

    # 4. Verify that the new leader successfully healed the unprovisioned relation:
    # Credentials should now be generated and published
    rel_after = state_after_promotion.get_relation(oauth_relation.id)
    assert "client_id" in rel_after.local_app_data
    assert "client_secret_id" in rel_after.local_app_data
    assert "issuer_url" in rel_after.local_app_data

    # Verify that the REST API was called to register the client on the new leader
    mock_authentik_api.create_oauth_provider.assert_called_once()
    mock_authentik_api.create_application.assert_called_once()


def test_oauth_dynamic_scopes(
    context: testing.Context,
    db_relation: testing.Relation,
    peer_relation: testing.PeerRelation,
    cluster_relation: testing.Relation,
    authentik_secrets: testing.Secret,
    all_satisfied_conditions: None,
    mock_authentik_api: MagicMock,
) -> None:
    """Test that client requested scopes are fetched dynamically from the relation."""
    oauth_relation = testing.Relation(
        endpoint=OAUTH_RELATION_NAME,
        interface="oauth",
        remote_app_name="client-app",
        remote_app_data={
            "redirect_uri": "https://client.example.com/oauth/callback",
            "scope": "openid email group profile",
            "grant_types": json.dumps(["authorization_code"]),
            "token_endpoint_auth_method": "client_secret_basic",
            "audience": json.dumps([]),
        },
    )
    state = create_state(
        leader=True,
        relations=[db_relation, peer_relation, cluster_relation, oauth_relation],
        secrets=[authentik_secrets],
    )

    # Trigger relation_changed
    state_out = context.run(context.on.relation_changed(oauth_relation), state)

    # Verify that the correct dynamically filtered scopes are published in the relation data
    rel_out = state_out.get_relation(oauth_relation.id)
    assert rel_out.local_app_data["scope"] == "email group openid profile"

    # Verify that the REST API was queried for exactly the list of sorted dynamic scopes requested
    mock_authentik_api.get_property_mappings.assert_called_with([
        "email",
        "group",
        "openid",
        "profile",
    ])
