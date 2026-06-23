# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm libraries owned by authentik-server-operator.

Libraries under test:
  - charms.authentik_server.v0.authentik_cluster  (provider + requirer)
  - charms.authentik_server.v0.authentik_server_info  (provider + requirer)

Each library is exercised through a minimal test-only charm class.
All tests use ops.testing (Scenario); no Harness is used.
"""

from typing import Any

import ops
import pytest
from charms.authentik_server.v0.authentik_cluster import (
    AuthentikClusterProvider,
    AuthentikClusterRequirer,
)
from charms.authentik_server.v0.authentik_cluster import ProviderData as ClusterProviderData
from charms.authentik_server.v0.authentik_server_info import (
    AuthentikServerInfoProvider,
    AuthentikServerInfoRequirer,
)
from charms.authentik_server.v0.authentik_server_info import ProviderData as ServerInfoProviderData
from ops import testing

# ---------------------------------------------------------------------------
# Metadata for minimal test charms
# ---------------------------------------------------------------------------

_CLUSTER_PROVIDER_META: dict[str, Any] = {
    "name": "cluster-provider-tester",
    "provides": {"authentik-cluster": {"interface": "authentik_cluster"}},
}

_CLUSTER_REQUIRER_META: dict[str, Any] = {
    "name": "cluster-requirer-tester",
    "requires": {"authentik-cluster": {"interface": "authentik_cluster"}},
}

_SERVER_INFO_PROVIDER_META: dict[str, Any] = {
    "name": "server-info-provider-tester",
    "provides": {"authentik-server-info": {"interface": "authentik_server_info"}},
}

_SERVER_INFO_REQUIRER_META: dict[str, Any] = {
    "name": "server-info-requirer-tester",
    "requires": {"authentik-server-info": {"interface": "authentik_server_info"}},
}

# ---------------------------------------------------------------------------
# Minimal test charm classes
# ---------------------------------------------------------------------------


class _ClusterProviderCharm(ops.CharmBase):
    """Minimal charm exercising AuthentikClusterProvider."""

    def __init__(self, *args: Any) -> None:
        super().__init__(*args)
        self.cluster_provider = AuthentikClusterProvider(self)
        self.framework.observe(self.cluster_provider.on.ready, self._on_ready)

    def _on_ready(self, event: ops.EventBase) -> None:
        self.cluster_provider.update_relations_app_data(
            secret_key="test-secret-key", server_version="2026.1.0"
        )


class _ClusterRequirerCharm(ops.CharmBase):
    """Minimal charm exercising AuthentikClusterRequirer."""

    def __init__(self, *args: Any) -> None:
        super().__init__(*args)
        self.cluster = AuthentikClusterRequirer(self)
        self.framework.observe(self.cluster.on.cluster_changed, self._on_cluster_changed)
        self.framework.observe(self.cluster.on.cluster_removed, self._on_cluster_removed)
        self.framework.observe(self.on.config_changed, self._on_config_changed)

    def _on_cluster_changed(self, event: ops.EventBase) -> None:
        if self.cluster.is_ready():
            self.unit.status = ops.ActiveStatus("ready")
        else:
            self.unit.status = ops.WaitingStatus("not ready")

    def _on_cluster_removed(self, event: ops.EventBase) -> None:
        self.unit.status = ops.BlockedStatus("cluster removed")

    def _on_config_changed(self, event: ops.EventBase) -> None:
        if self.cluster.is_ready():
            self.unit.status = ops.ActiveStatus("ready")
        else:
            self.unit.status = ops.WaitingStatus("not ready")


class _ServerInfoProviderCharm(ops.CharmBase):
    """Minimal charm exercising AuthentikServerInfoProvider."""

    def __init__(self, *args: Any) -> None:
        super().__init__(*args)
        self.server_info_provider = AuthentikServerInfoProvider(self)
        self.framework.observe(self.server_info_provider.on.ready, self._on_ready)

    def _on_ready(self, event: ops.EventBase) -> None:
        self.server_info_provider.update_relations_app_data(
            authentik_host="http://authentik:9000",
            bootstrap_token="test-token",
            bootstrap_password="test-password",
        )


class _ServerInfoRequirerCharm(ops.CharmBase):
    """Minimal charm exercising AuthentikServerInfoRequirer."""

    def __init__(self, *args: Any) -> None:
        super().__init__(*args)
        self.server_info = AuthentikServerInfoRequirer(self)
        self.framework.observe(self.server_info.on.info_changed, self._on_info_changed)
        self.framework.observe(self.server_info.on.info_removed, self._on_info_removed)
        self.framework.observe(self.on.config_changed, self._on_config_changed)

    def _on_info_changed(self, event: ops.EventBase) -> None:
        if self.server_info.is_ready():
            self.unit.status = ops.ActiveStatus("ready")
        else:
            self.unit.status = ops.WaitingStatus("not ready")

    def _on_info_removed(self, event: ops.EventBase) -> None:
        self.unit.status = ops.BlockedStatus("info removed")

    def _on_config_changed(self, event: ops.EventBase) -> None:
        if self.server_info.is_ready():
            self.unit.status = ops.ActiveStatus("ready")
        else:
            self.unit.status = ops.WaitingStatus("not ready")


# ---------------------------------------------------------------------------
# Tests: AuthentikClusterProvider
# ---------------------------------------------------------------------------


class TestAuthentikClusterProvider:
    @pytest.fixture
    def context(self) -> testing.Context:
        return testing.Context(_ClusterProviderCharm, meta=_CLUSTER_PROVIDER_META)

    def test_update_relations_app_data_creates_secret_and_publishes(
        self, context: testing.Context
    ) -> None:
        relation = testing.Relation("authentik-cluster")
        state = testing.State(leader=True, relations=[relation])

        state_out = context.run(context.on.relation_created(relation), state)

        assert any(s.label == "authentik-secret-key" for s in state_out.secrets)
        secret = next(s for s in state_out.secrets if s.label == "authentik-secret-key")
        assert secret.tracked_content == {"secret-key": "test-secret-key"}
        rel_out = state_out.get_relation(relation.id)
        assert "secret_key_secret_id" in rel_out.local_app_data
        assert rel_out.local_app_data.get("server_version") == "2026.1.0"

    def test_update_relations_app_data_noop_for_non_leader(self, context: testing.Context) -> None:
        relation = testing.Relation("authentik-cluster")
        state = testing.State(leader=False, relations=[relation])

        state_out = context.run(context.on.relation_created(relation), state)

        assert not any(s.label == "authentik-secret-key" for s in state_out.secrets)

    def test_relation_broken_removes_secret(self, context: testing.Context) -> None:
        relation = testing.Relation("authentik-cluster")
        secret = testing.Secret(
            label="authentik-secret-key",
            tracked_content={"secret-key": "test-secret-key"},
            owner="app",
        )
        state = testing.State(leader=True, relations=[relation], secrets=[secret])

        state_out = context.run(context.on.relation_broken(relation), state)

        assert not any(s.label == "authentik-secret-key" for s in state_out.secrets)

    def test_relation_broken_keeps_secret_if_other_relations_exist(
        self, context: testing.Context
    ) -> None:
        relation_broken = testing.Relation("authentik-cluster", id=1)
        relation_active = testing.Relation("authentik-cluster", id=2)
        secret = testing.Secret(
            label="authentik-secret-key",
            tracked_content={"secret-key": "test-secret-key"},
            owner="app",
            remote_grants={
                relation_broken.id: {relation_broken.remote_app_name},
                relation_active.id: {relation_active.remote_app_name},
            },
        )
        state = testing.State(
            leader=True,
            relations=[relation_broken, relation_active],
            secrets=[secret],
        )

        state_out = context.run(context.on.relation_broken(relation_broken), state)

        assert any(s.label == "authentik-secret-key" for s in state_out.secrets)
        secret_out = next(s for s in state_out.secrets if s.label == "authentik-secret-key")
        assert relation_broken.id not in secret_out.remote_grants
        assert relation_active.id in secret_out.remote_grants


# ---------------------------------------------------------------------------
# Tests: AuthentikClusterRequirer
# ---------------------------------------------------------------------------


class TestAuthentikClusterRequirer:
    @pytest.fixture
    def context(self) -> testing.Context:
        return testing.Context(_ClusterRequirerCharm, meta=_CLUSTER_REQUIRER_META)

    @pytest.fixture
    def cluster_secret(self) -> testing.Secret:
        return testing.Secret(tracked_content={"secret-key": "test-secret-key"})

    @pytest.fixture
    def cluster_relation(self, cluster_secret: testing.Secret) -> testing.Relation:
        return testing.Relation(
            "authentik-cluster",
            remote_app_data={
                "secret_key_secret_id": cluster_secret.id,
                "server_version": "2026.1.0",
            },
        )

    def test_cluster_changed_calls_handler(
        self,
        context: testing.Context,
        cluster_relation: testing.Relation,
        cluster_secret: testing.Secret,
    ) -> None:
        state = testing.State(leader=False, relations=[cluster_relation], secrets=[cluster_secret])

        state_out = context.run(context.on.relation_changed(cluster_relation), state)

        assert state_out.unit_status == testing.ActiveStatus("ready")

    def test_cluster_removed_calls_handler(
        self,
        context: testing.Context,
        cluster_relation: testing.Relation,
        cluster_secret: testing.Secret,
    ) -> None:
        state = testing.State(leader=False, relations=[cluster_relation], secrets=[cluster_secret])

        state_out = context.run(context.on.relation_broken(cluster_relation), state)

        assert state_out.unit_status == testing.BlockedStatus("cluster removed")

    def test_is_ready_true_when_secret_key_available(
        self,
        context: testing.Context,
        cluster_relation: testing.Relation,
        cluster_secret: testing.Secret,
    ) -> None:
        state = testing.State(leader=False, relations=[cluster_relation], secrets=[cluster_secret])

        state_out = context.run(context.on.relation_changed(cluster_relation), state)

        assert state_out.unit_status == testing.ActiveStatus("ready")

    def test_get_provider_data_returns_none_when_no_relation(
        self, context: testing.Context
    ) -> None:
        state = testing.State(leader=False)

        state_out = context.run(context.on.config_changed(), state)

        assert state_out.unit_status == testing.WaitingStatus("not ready")

    def test_get_provider_data_returns_parsed_model(
        self,
        context: testing.Context,
        cluster_relation: testing.Relation,
        cluster_secret: testing.Secret,
    ) -> None:
        state = testing.State(leader=False, relations=[cluster_relation], secrets=[cluster_secret])

        with context(context.on.relation_changed(cluster_relation), state) as mgr:
            data = mgr.charm.cluster.get_provider_data()

        assert isinstance(data, ClusterProviderData)
        assert data.secret_key_secret_id == cluster_secret.id
        assert data.server_version == "2026.1.0"

    def test_is_ready_false_when_no_relation(self, context: testing.Context) -> None:
        state = testing.State(leader=False)

        state_out = context.run(context.on.config_changed(), state)

        assert state_out.unit_status == testing.WaitingStatus("not ready")


# ---------------------------------------------------------------------------
# Tests: AuthentikServerInfoProvider
# ---------------------------------------------------------------------------


class TestAuthentikServerInfoProvider:
    @pytest.fixture
    def context(self) -> testing.Context:
        return testing.Context(_ServerInfoProviderCharm, meta=_SERVER_INFO_PROVIDER_META)

    def test_update_relations_app_data_creates_secrets_and_publishes(
        self, context: testing.Context
    ) -> None:
        relation = testing.Relation("authentik-server-info")
        state = testing.State(leader=True, relations=[relation])

        state_out = context.run(context.on.relation_created(relation), state)

        assert any(s.label == "authentik-bootstrap-token" for s in state_out.secrets)
        assert any(s.label == "authentik-bootstrap-password" for s in state_out.secrets)
        rel_out = state_out.get_relation(relation.id)
        assert rel_out.local_app_data.get("authentik_host") == "http://authentik:9000"
        assert "authentik_token_secret_id" in rel_out.local_app_data
        assert "bootstrap_password_secret_id" in rel_out.local_app_data

    def test_update_relations_app_data_noop_for_non_leader(self, context: testing.Context) -> None:
        relation = testing.Relation("authentik-server-info")
        state = testing.State(leader=False, relations=[relation])

        state_out = context.run(context.on.relation_created(relation), state)

        assert not any(s.label == "authentik-bootstrap-token" for s in state_out.secrets)
        assert not any(s.label == "authentik-bootstrap-password" for s in state_out.secrets)

    def test_relation_broken_removes_secrets(self, context: testing.Context) -> None:
        relation = testing.Relation("authentik-server-info")
        token_secret = testing.Secret(
            label="authentik-bootstrap-token",
            tracked_content={"bootstrap-token": "test-token"},
            owner="app",
        )
        password_secret = testing.Secret(
            label="authentik-bootstrap-password",
            tracked_content={"bootstrap-password": "test-password"},
            owner="app",
        )
        state = testing.State(
            leader=True,
            relations=[relation],
            secrets=[token_secret, password_secret],
        )

        state_out = context.run(context.on.relation_broken(relation), state)

        assert not any(s.label == "authentik-bootstrap-token" for s in state_out.secrets)
        assert not any(s.label == "authentik-bootstrap-password" for s in state_out.secrets)

    def test_relation_broken_keeps_secrets_if_other_relations_exist(
        self, context: testing.Context
    ) -> None:
        relation_broken = testing.Relation("authentik-server-info", id=1)
        relation_active = testing.Relation("authentik-server-info", id=2)
        token_secret = testing.Secret(
            label="authentik-bootstrap-token",
            tracked_content={"bootstrap-token": "test-token"},
            owner="app",
            remote_grants={
                relation_broken.id: {relation_broken.remote_app_name},
                relation_active.id: {relation_active.remote_app_name},
            },
        )
        password_secret = testing.Secret(
            label="authentik-bootstrap-password",
            tracked_content={"bootstrap-password": "test-password"},
            owner="app",
            remote_grants={
                relation_broken.id: {relation_broken.remote_app_name},
                relation_active.id: {relation_active.remote_app_name},
            },
        )
        state = testing.State(
            leader=True,
            relations=[relation_broken, relation_active],
            secrets=[token_secret, password_secret],
        )

        state_out = context.run(context.on.relation_broken(relation_broken), state)

        assert any(s.label == "authentik-bootstrap-token" for s in state_out.secrets)
        assert any(s.label == "authentik-bootstrap-password" for s in state_out.secrets)

        token_secret_out = next(
            s for s in state_out.secrets if s.label == "authentik-bootstrap-token"
        )
        password_secret_out = next(
            s for s in state_out.secrets if s.label == "authentik-bootstrap-password"
        )

        assert relation_broken.id not in token_secret_out.remote_grants
        assert relation_active.id in token_secret_out.remote_grants

        assert relation_broken.id not in password_secret_out.remote_grants
        assert relation_active.id in password_secret_out.remote_grants


# ---------------------------------------------------------------------------
# Tests: AuthentikServerInfoRequirer
# ---------------------------------------------------------------------------


class TestAuthentikServerInfoRequirer:
    @pytest.fixture
    def context(self) -> testing.Context:
        return testing.Context(_ServerInfoRequirerCharm, meta=_SERVER_INFO_REQUIRER_META)

    @pytest.fixture
    def token_secret(self) -> testing.Secret:
        return testing.Secret(tracked_content={"bootstrap-token": "test-token"})

    @pytest.fixture
    def password_secret(self) -> testing.Secret:
        return testing.Secret(tracked_content={"bootstrap-password": "test-password"})

    @pytest.fixture
    def server_info_relation(
        self,
        token_secret: testing.Secret,
        password_secret: testing.Secret,
    ) -> testing.Relation:
        return testing.Relation(
            "authentik-server-info",
            remote_app_data={
                "authentik_host": "http://authentik:9000",
                "authentik_token_secret_id": token_secret.id,
                "bootstrap_password_secret_id": password_secret.id,
            },
        )

    def test_info_changed_calls_handler(
        self,
        context: testing.Context,
        server_info_relation: testing.Relation,
        token_secret: testing.Secret,
        password_secret: testing.Secret,
    ) -> None:
        state = testing.State(
            leader=False,
            relations=[server_info_relation],
            secrets=[token_secret, password_secret],
        )

        state_out = context.run(context.on.relation_changed(server_info_relation), state)

        assert state_out.unit_status == testing.ActiveStatus("ready")

    def test_info_removed_calls_handler(
        self,
        context: testing.Context,
        server_info_relation: testing.Relation,
        token_secret: testing.Secret,
        password_secret: testing.Secret,
    ) -> None:
        state = testing.State(
            leader=False,
            relations=[server_info_relation],
            secrets=[token_secret, password_secret],
        )

        state_out = context.run(context.on.relation_broken(server_info_relation), state)

        assert state_out.unit_status == testing.BlockedStatus("info removed")

    def test_is_ready_true_when_all_fields_available(
        self,
        context: testing.Context,
        server_info_relation: testing.Relation,
        token_secret: testing.Secret,
        password_secret: testing.Secret,
    ) -> None:
        state = testing.State(
            leader=False,
            relations=[server_info_relation],
            secrets=[token_secret, password_secret],
        )

        state_out = context.run(context.on.relation_changed(server_info_relation), state)

        assert state_out.unit_status == testing.ActiveStatus("ready")

    def test_get_provider_data_returns_parsed_model(
        self,
        context: testing.Context,
        server_info_relation: testing.Relation,
        token_secret: testing.Secret,
        password_secret: testing.Secret,
    ) -> None:
        state = testing.State(
            leader=False,
            relations=[server_info_relation],
            secrets=[token_secret, password_secret],
        )

        with context(context.on.relation_changed(server_info_relation), state) as mgr:
            data = mgr.charm.server_info.get_provider_data()

        assert isinstance(data, ServerInfoProviderData)
        assert data.authentik_host == "http://authentik:9000"
        assert data.authentik_token_secret_id == token_secret.id
        assert data.bootstrap_password_secret_id == password_secret.id

    def test_is_ready_false_when_no_relation(self, context: testing.Context) -> None:
        state = testing.State(leader=False)

        state_out = context.run(context.on.config_changed(), state)

        assert state_out.unit_status == testing.WaitingStatus("not ready")
