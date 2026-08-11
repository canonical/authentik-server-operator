# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the OAuth relation."""

import hashlib
import json
from unittest.mock import MagicMock

import pytest
from ops import testing
from pytest_mock import MockerFixture
from unit.conftest import create_state

from constants import (
    AUTHORIZATION_FLOW_CACHE_PEER_KEY,
    INVALIDATION_FLOW_CACHE_PEER_KEY,
    OAUTH_RELATION_NAME,
)
from exceptions import (
    AuthentikConflictError,
    AuthentikRequestValidationError,
    AuthentikTransientError,
)
from oauth import OauthReconciler


@pytest.fixture(autouse=True)
def mock_authentik_api(mocker: MockerFixture):
    """Fixture to mock AuthentikAPI globally to avoid live HTTP requests in unit tests."""
    mock_api_class = mocker.patch("charm.AuthentikAPI", autospec=True)
    mock_api_instance = mock_api_class.return_value

    # Setup standard mocked responses
    mock_api_instance.is_service_available = True
    mock_api_instance.get_authorization_flow_uuid.return_value = "test-flow-uuid"
    mock_api_instance.get_invalidation_flow_uuid.return_value = "test-invalidation-flow-uuid"
    mock_api_instance.get_property_mappings.return_value = ["mapping-1", "mapping-2"]
    mock_api_instance.get_application.return_value = None  # Default to not existing yet
    mock_api_instance.get_oauth_provider.return_value = {"pk": 123}
    mock_api_instance.find_oauth_provider.return_value = None
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
    traefik_route_relation: testing.Relation,
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
        relations=[
            db_relation,
            peer_relation,
            cluster_relation,
            oauth_relation,
            traefik_route_relation,
        ],
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
        relations=[
            db_relation,
            peer_relation,
            cluster_relation,
            oauth_relation_with_config,
            traefik_route_relation,
        ],
        secrets=[authentik_secrets],
    )
    state_out = context.run(context.on.relation_changed(oauth_relation_with_config), next_state)

    # Check that client credentials are populated in the relation data
    rel_out = state_out.get_relation(oauth_relation.id)
    assert "client_id" in rel_out.local_app_data
    assert "client_secret_id" in rel_out.local_app_data

    # Check standard OIDC endpoints are updated correctly using the external host from traefik-route
    assert "issuer_url" in rel_out.local_app_data
    assert "authorization_endpoint" in rel_out.local_app_data
    assert "token_endpoint" in rel_out.local_app_data
    assert "jwks_endpoint" in rel_out.local_app_data
    assert rel_out.local_app_data["issuer_url"].startswith(
        "https://authentik.example.com/application/o/juju-"
    )
    assert rel_out.local_app_data["issuer_url"].endswith(f"-oauth-{oauth_relation.id}/")


def test_oauth_client_created_non_leader(
    context: testing.Context,
    db_relation: testing.Relation,
    peer_relation: testing.PeerRelation,
    cluster_relation: testing.Relation,
    authentik_secrets: testing.Secret,
    traefik_route_relation: testing.Relation,
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
        relations=[
            db_relation,
            peer_relation,
            cluster_relation,
            oauth_relation,
            traefik_route_relation,
        ],
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
    # Define Traefik route relation with a specific URL
    traefik_route_relation = testing.Relation(
        endpoint="traefik-route",
        interface="traefik_route",
        remote_app_name="traefik",
        remote_app_data={
            "external_host": "authentik.mycompany.org",
            "scheme": "https",
        },
    )
    state = create_state(
        leader=True,
        relations=[
            db_relation,
            peer_relation,
            cluster_relation,
            oauth_relation,
            traefik_route_relation,
        ],
        secrets=[authentik_secrets],
    )

    # Run any event to trigger reconciliation (e.g. config_changed)
    state_out = context.run(context.on.config_changed(), state)

    rel_out = state_out.get_relation(oauth_relation.id)
    assert rel_out.local_app_data["issuer_url"].startswith(
        "https://authentik.mycompany.org/application/o/juju-"
    )
    assert rel_out.local_app_data["issuer_url"].endswith(f"-oauth-{oauth_relation.id}/")
    assert (
        rel_out.local_app_data["authorization_endpoint"]
        == "https://authentik.mycompany.org/application/o/authorize/"
    )
    assert (
        rel_out.local_app_data["token_endpoint"]
        == "https://authentik.mycompany.org/application/o/token/"
    )
    assert rel_out.local_app_data["jwks_endpoint"].startswith(
        "https://authentik.mycompany.org/application/o/juju-"
    )
    assert rel_out.local_app_data["jwks_endpoint"].endswith(f"-oauth-{oauth_relation.id}/jwks/")


def test_oauth_relation_broken(
    context: testing.Context,
    db_relation: testing.Relation,
    peer_relation: testing.PeerRelation,
    cluster_relation: testing.Relation,
    authentik_secrets: testing.Secret,
    traefik_route_relation: testing.Relation,
    all_satisfied_conditions: None,
    mock_authentik_api: MagicMock,
) -> None:
    """Test that an uncached numeric legacy slug is never treated as owned."""
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
        relations=[
            db_relation,
            peer_relation,
            cluster_relation,
            oauth_relation,
            traefik_route_relation,
        ],
        secrets=[authentik_secrets],
    )

    mock_authentik_api.list_applications.return_value = [
        {
            "name": f"client-app (Relation {oauth_relation.id})",
            "slug": f"client-app-{oauth_relation.id}",
            "provider": 123,
        }
    ]

    context.run(context.on.relation_broken(oauth_relation), state)

    mock_authentik_api.list_applications.assert_not_called()
    mock_authentik_api.delete_oauth_provider.assert_not_called()
    mock_authentik_api.delete_application.assert_not_called()


def test_oauth_leader_election_heals_unprovisioned_relation(
    context: testing.Context,
    db_relation: testing.Relation,
    peer_relation: testing.PeerRelation,
    cluster_relation: testing.Relation,
    authentik_secrets: testing.Secret,
    traefik_route_relation: testing.Relation,
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
        relations=[
            db_relation,
            peer_relation,
            cluster_relation,
            oauth_relation,
            traefik_route_relation,
        ],
        secrets=[authentik_secrets],
    )

    # 2. Trigger a relation_changed event as a follower: no credentials should be generated
    state_out = context.run(context.on.relation_changed(oauth_relation), state)
    rel_out = state_out.get_relation(oauth_relation.id)
    assert "client_id" not in rel_out.local_app_data

    # 3. Simulate leader election (leader=True) and run the leader_elected event
    promoted_state = create_state(
        leader=True,
        relations=[
            db_relation,
            peer_relation,
            cluster_relation,
            rel_out,
            traefik_route_relation,
        ],
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
    traefik_route_relation: testing.Relation,
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
        relations=[
            db_relation,
            peer_relation,
            cluster_relation,
            oauth_relation,
            traefik_route_relation,
        ],
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


def test_oauth_relation_reconcile_uses_cache(
    context: testing.Context,
    db_relation: testing.Relation,
    authentik_secrets: testing.Secret,
    cluster_relation: testing.Relation,
    traefik_route_relation: testing.Relation,
    all_satisfied_conditions: None,
    mock_authentik_api: MagicMock,
    mocker: MockerFixture,
) -> None:
    """Test that if the cache is hit, no API calls are made to Authentik during reconciliation."""
    oauth_relation = testing.Relation(
        endpoint=OAUTH_RELATION_NAME,
        interface="oauth",
        id=12,
        remote_app_name="client-app",
        remote_app_data={
            "redirect_uri": "https://client.example.com/oauth/callback",
            "scope": "openid email",
            "grant_types": json.dumps(["authorization_code"]),
            "token_endpoint_auth_method": "client_secret_basic",
            "audience": json.dumps([]),
        },
        local_app_data={
            "client_id": "test-client-id",
            "client_secret_id": "secret:123",
            "scope": "email openid",
            "issuer_url": "http://authentik-server.test-model.svc.cluster.local:9000/application/o/client-app-12/",
            "authorization_endpoint": "http://authentik-server.test-model.svc.cluster.local:9000/application/o/authorize/",
            "token_endpoint": "http://authentik-server.test-model.svc.cluster.local:9000/application/o/token/",
            "introspection_endpoint": "http://authentik-server.test-model.svc.cluster.local:9000/application/o/introspect/",
            "userinfo_endpoint": "http://authentik-server.test-model.svc.cluster.local:9000/application/o/client-app-12/userinfo/",
            "jwks_endpoint": "http://authentik-server.test-model.svc.cluster.local:9000/application/o/client-app-12/jwks/",
        },
    )

    config_str = "https://client.example.com/oauth/callback:test-flow-uuid:test-invalidation-flow-uuid:email,openid"
    config_hash = hashlib.sha256(config_str.encode("utf-8")).hexdigest()

    peer_relation_with_cache = testing.PeerRelation(
        endpoint="authentik-peers",
        interface="authentik_peers",
        local_app_data={
            "secrets_id": authentik_secrets.id,
            "oauth_sync_cache": json.dumps({
                str(oauth_relation.id): {
                    "schema_version": 2,
                    "config_hash": config_hash,
                    "provider_pk": 123,
                    "slug": f"client-app-{oauth_relation.id}",
                }
            }),
            "authorization_flow_cache": "test-flow-uuid",
            "invalidation_flow_cache": "test-invalidation-flow-uuid",
        },
    )

    state = create_state(
        leader=True,
        relations=[
            db_relation,
            peer_relation_with_cache,
            cluster_relation,
            oauth_relation,
            traefik_route_relation,
        ],
        secrets=[authentik_secrets],
    )

    mocker.patch(
        "charm.AuthentikServerCharm._get_or_generate_credentials",
        return_value=("test-client-id", "test-secret", False),
    )

    # Trigger reconcile via relation_changed event
    context.run(context.on.relation_changed(oauth_relation), state)

    # API calls should NOT be made since it's cached and fully in sync!
    mock_authentik_api.get_authorization_flow_uuid.assert_not_called()
    mock_authentik_api.get_invalidation_flow_uuid.assert_not_called()
    mock_authentik_api.get_property_mappings.assert_not_called()
    mock_authentik_api.create_oauth_provider.assert_not_called()
    mock_authentik_api.update_oauth_provider.assert_not_called()
    mock_authentik_api.get_application.assert_not_called()
    mock_authentik_api.list_applications.assert_not_called()


def test_oauth_relation_broken_uses_cache(
    context: testing.Context,
    db_relation: testing.Relation,
    authentik_secrets: testing.Secret,
    cluster_relation: testing.Relation,
    traefik_route_relation: testing.Relation,
    all_satisfied_conditions: None,
    mock_authentik_api: MagicMock,
) -> None:
    """Test that relation_broken deletes objects using cached info without listing applications."""
    oauth_relation = testing.Relation(
        endpoint=OAUTH_RELATION_NAME,
        interface="oauth",
        remote_app_name="client-app",
        local_app_data={
            "client_id": "test-client-id",
            "client_secret_id": "secret:123",
        },
    )

    peer_relation_with_cache = testing.PeerRelation(
        endpoint="authentik-peers",
        interface="authentik_peers",
        local_app_data={
            "secrets_id": authentik_secrets.id,
            "oauth_sync_cache": json.dumps({
                str(oauth_relation.id): {
                    "provider_pk": 123,
                    "slug": f"client-app-{oauth_relation.id}",
                }
            }),
        },
    )

    state = create_state(
        leader=True,
        relations=[
            db_relation,
            peer_relation_with_cache,
            cluster_relation,
            oauth_relation,
            traefik_route_relation,
        ],
        secrets=[authentik_secrets],
    )

    # Trigger relation_broken
    context.run(context.on.relation_broken(oauth_relation), state)

    # Verify that list_applications was NOT called (it was bypassed because of the cache)
    mock_authentik_api.list_applications.assert_not_called()

    # Verify that the API delete methods were called for the cached slug and provider ID
    mock_authentik_api.delete_oauth_provider.assert_called_once_with(123)
    mock_authentik_api.delete_application.assert_called_once_with(
        f"client-app-{oauth_relation.id}"
    )


class FakePeerData:
    """In-memory peer data with copy-on-read/write semantics."""

    def __init__(self, cache: dict | None = None) -> None:
        self.data = {"oauth_sync_cache": cache or {}}

    def __getitem__(self, key: str) -> dict:
        return json.loads(json.dumps(self.data.get(key, {})))

    def __setitem__(self, key: str, value: dict) -> None:
        self.data[key] = json.loads(json.dumps(value))

    def get_string(self, key: str) -> str | None:
        return self.data.get(key)

    def set_string(self, key: str, value: str) -> None:
        self.data[key] = value


def make_reconciler(mocker: MockerFixture, api: MagicMock, peer: FakePeerData) -> OauthReconciler:
    charm = MagicMock()
    charm.model.uuid = "12345678-1234-5678-1234-567812345678"
    charm._clean_slug.side_effect = lambda value: value.lower().replace(" ", "-")
    mocker.patch("oauth.PeerData", return_value=peer)
    return OauthReconciler(charm, api)


def relation(relation_id: int = 7) -> MagicMock:
    """Build the relation identity required by private reconciliation helpers."""
    result = MagicMock()
    result.id = relation_id
    result.app.name = "Client App"
    return result


def sync_objects(
    reconciler: OauthReconciler, oauth_relation: MagicMock, cache: dict
) -> tuple[str, int]:
    """Invoke object synchronization with stable test configuration."""
    return reconciler._sync_authentik_objects(
        oauth_relation,
        cache,
        "client-id",
        "client-secret",
        "https://client.test/callback",
        "authorization-flow",
        "invalidation-flow",
        ["openid-mapping"],
    )


def test_active_relation_adopts_only_its_exact_legacy_application(
    mocker: MockerFixture,
) -> None:
    api = MagicMock()
    api.get_application.side_effect = [None, {"slug": "client-app-7", "provider": 123}]
    api.get_oauth_provider.return_value = {
        "pk": 123,
        "name": "Client App (Relation 7)",
    }
    peer = FakePeerData()
    reconciler = make_reconciler(mocker, api, peer)

    slug, provider_pk = sync_objects(reconciler, relation(), {})

    assert (slug, provider_pk) == ("client-app-7", 123)
    assert [call.args[0] for call in api.get_application.call_args_list] == [
        reconciler._managed_identifier(7),
        "client-app-7",
    ]
    api.create_oauth_provider.assert_not_called()
    assert peer.data["oauth_sync_cache"]["7"]["slug"] == "client-app-7"


def test_active_relation_rejects_legacy_application_with_unexpected_provider(
    mocker: MockerFixture,
) -> None:
    api = MagicMock()
    api.get_application.side_effect = [None, {"slug": "client-app-7", "provider": 999}]
    api.get_oauth_provider.return_value = {"pk": 999, "name": "Unrelated provider"}
    peer = FakePeerData()
    reconciler = make_reconciler(mocker, api, peer)

    with pytest.raises(AuthentikConflictError, match="expected OAuth provider"):
        sync_objects(reconciler, relation(), {})

    assert peer.data["oauth_sync_cache"] == {}
    api.update_oauth_provider.assert_not_called()


def test_provider_discovery_is_persisted_before_later_update_failure(
    mocker: MockerFixture,
) -> None:
    api = MagicMock()
    api.get_application.side_effect = [None, None]
    # An existing provider is discovered (not freshly created), so the update runs.
    api.find_oauth_provider.return_value = {"pk": 123}
    api.update_oauth_provider.side_effect = AuthentikTransientError("update failed")
    peer = FakePeerData()
    reconciler = make_reconciler(mocker, api, peer)

    with pytest.raises(AuthentikTransientError, match="update failed"):
        sync_objects(reconciler, relation(), {})

    partial = peer.data["oauth_sync_cache"]["7"]
    assert partial["provider_pk"] == 123
    assert partial["slug"] == reconciler._managed_identifier(7)
    assert "config_hash" not in partial
    api.create_oauth_provider.assert_not_called()
    api.create_application.assert_not_called()


def test_freshly_created_provider_skips_redundant_update(
    mocker: MockerFixture,
) -> None:
    api = MagicMock()
    api.get_application.side_effect = [None, None]
    api.find_oauth_provider.return_value = None
    api.create_oauth_provider.return_value = 123
    peer = FakePeerData()
    reconciler = make_reconciler(mocker, api, peer)

    slug, provider_pk = sync_objects(reconciler, relation(), {})

    assert provider_pk == 123
    api.create_oauth_provider.assert_called_once()
    # The create call already persisted every field the update would set.
    api.update_oauth_provider.assert_not_called()
    api.create_application.assert_called_once()


def test_application_update_failure_leaves_unsynchronized_partial_cache(
    mocker: MockerFixture,
) -> None:
    api = MagicMock()
    oauth_relation = relation()
    peer = FakePeerData()
    reconciler = make_reconciler(mocker, api, peer)
    api.get_application.return_value = {"provider": 123}
    api.get_oauth_provider.return_value = {
        "pk": 123,
        "name": reconciler._provider_name(oauth_relation),
    }
    api.update_application.side_effect = AuthentikTransientError("application update failed")

    with pytest.raises(AuthentikTransientError, match="application update failed"):
        sync_objects(reconciler, oauth_relation, {})

    partial = peer.data["oauth_sync_cache"]["7"]
    assert partial["provider_pk"] == 123
    assert "config_hash" not in partial


def test_cleanup_retains_remaining_provider_after_transient_failure(
    mocker: MockerFixture,
) -> None:
    peer = FakePeerData({"7": {"schema_version": 2, "slug": "owned-app", "provider_pk": 123}})
    api = MagicMock()
    api.delete_application.return_value = True
    api.delete_oauth_provider.side_effect = AuthentikTransientError("provider unavailable")
    reconciler = make_reconciler(mocker, api, peer)

    with pytest.raises(AuthentikTransientError, match="provider unavailable"):
        reconciler.garbage_collect(set())

    assert peer.data["oauth_sync_cache"] == {"7": {"schema_version": 2, "provider_pk": 123}}

    api.delete_oauth_provider.side_effect = None
    api.delete_oauth_provider.return_value = True
    reconciler.garbage_collect(set())
    assert peer.data["oauth_sync_cache"] == {}


def test_oauth_default_scope_excludes_phone(
    context: testing.Context,
    db_relation: testing.Relation,
    peer_relation: testing.PeerRelation,
    cluster_relation: testing.Relation,
    authentik_secrets: testing.Secret,
    traefik_route_relation: testing.Relation,
    all_satisfied_conditions: None,
    mock_authentik_api: MagicMock,
) -> None:
    """A requirer with an empty `scope` gets only default scopes with Authentik mappings (no `phone`)."""
    oauth_relation = testing.Relation(
        endpoint=OAUTH_RELATION_NAME,
        interface="oauth",
        remote_app_name="client-app",
        remote_app_data={
            "redirect_uri": "https://client.example.com/oauth/callback",
            "scope": "",
            "grant_types": json.dumps(["authorization_code"]),
            "token_endpoint_auth_method": "client_secret_basic",
            "audience": json.dumps([]),
        },
    )
    state = create_state(
        leader=True,
        relations=[
            db_relation,
            peer_relation,
            cluster_relation,
            oauth_relation,
            traefik_route_relation,
        ],
        secrets=[authentik_secrets],
    )

    state_out = context.run(context.on.relation_changed(oauth_relation), state)

    mock_authentik_api.get_property_mappings.assert_called_with(["email", "openid", "profile"])
    rel_out = state_out.get_relation(oauth_relation.id)
    assert "phone" not in rel_out.local_app_data["scope"]


def test_stale_cached_provider_is_rediscovered_after_external_deletion(
    mocker: MockerFixture,
) -> None:
    """A cached provider deleted out-of-band is dropped and recreated, not PUT into a 404 loop."""
    api = MagicMock()
    # Fast path: the cached application still resolves and references the cached pk...
    api.get_application.side_effect = [{"provider": 123}, None, None]
    # ...but the cached provider itself no longer exists in Authentik.
    api.get_oauth_provider.return_value = None
    api.find_oauth_provider.return_value = None
    api.create_oauth_provider.return_value = 456
    peer = FakePeerData({
        "7": {"schema_version": 2, "slug": "owned-app", "provider_pk": 123, "config_hash": "x"}
    })
    reconciler = make_reconciler(mocker, api, peer)

    slug, provider_pk = sync_objects(reconciler, relation(), peer["oauth_sync_cache"])

    api.get_oauth_provider.assert_called_once_with(123)
    api.create_oauth_provider.assert_called_once()
    assert provider_pk == 456
    # The provider was recreated, so the redundant update is skipped and the new
    # pk is wired into the application instead.
    api.update_oauth_provider.assert_not_called()
    assert api.create_application.call_args.kwargs["provider_pk"] == 456
    api.create_application.assert_called_once()
    assert peer.data["oauth_sync_cache"]["7"]["provider_pk"] == 456


def test_reconcile_invalidates_flow_cache_when_a_sync_hits_a_stale_flow(
    mocker: MockerFixture,
) -> None:
    """A stale cached flow UUID (flow recreated in Authentik) is dropped so it re-resolves."""
    api = MagicMock()
    peer = FakePeerData()
    peer.set_string(AUTHORIZATION_FLOW_CACHE_PEER_KEY, "stale-auth-flow")
    peer.set_string(INVALIDATION_FLOW_CACHE_PEER_KEY, "stale-inval-flow")
    reconciler = make_reconciler(mocker, api, peer)
    reconciler._charm.unit.is_leader.return_value = True
    reconciler._charm.model.get_relation.return_value = relation()
    mocker.patch.object(
        reconciler, "_sync_relation", side_effect=AuthentikRequestValidationError("stale flow")
    )

    with pytest.raises(AuthentikRequestValidationError, match="stale flow"):
        reconciler.reconcile({7})

    assert peer.get_string(AUTHORIZATION_FLOW_CACHE_PEER_KEY) == ""
    assert peer.get_string(INVALIDATION_FLOW_CACHE_PEER_KEY) == ""
    api.get_authorization_flow_uuid.assert_not_called()
