# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the Secrets class."""

from unittest.mock import MagicMock, create_autospec

import pytest
from ops import Model, SecretNotFoundError

from constants import (
    BOOTSTRAP_PASSWORD_KEY,
    BOOTSTRAP_TOKEN_KEY,
    SECRET_KEY_KEY,
    SECRETS_LABEL,
    SECRETS_PEER_KEY,
)
from exceptions import SecretError
from secret import Secrets

_SECRET_ID = "secret:abc123"
_FULL_CONTENT = {
    SECRET_KEY_KEY: "test-secret-key",
    BOOTSTRAP_TOKEN_KEY: "test-token",
    BOOTSTRAP_PASSWORD_KEY: "test-password",
}


def _make_secret(content: dict[str, str], secret_id: str = _SECRET_ID) -> MagicMock:
    """Create a mock Juju secret that returns the given content."""
    secret = MagicMock()
    secret.id = secret_id
    secret.get_content.return_value = content
    return secret


def _make_peer_relation(secret_id: str | None = _SECRET_ID) -> MagicMock:
    """Create a mock peer Relation with an optional secret ID in the app databag."""
    app_data: dict[str, str] = {}
    if secret_id is not None:
        app_data[SECRETS_PEER_KEY] = secret_id
    # Use a plain MagicMock so .data can be freely assigned.
    # rel.data[anything] returns the same app_data dict, mirroring RelationData.
    rel = MagicMock()
    rel.data = MagicMock()
    rel.data.__getitem__ = MagicMock(return_value=app_data)
    return rel


class TestSecrets:
    @pytest.fixture
    def mocked_model(self) -> MagicMock:
        return create_autospec(Model)

    @pytest.fixture
    def peer_relation_with_secret(self) -> MagicMock:
        return _make_peer_relation(secret_id=_SECRET_ID)

    @pytest.fixture
    def peer_relation_empty(self) -> MagicMock:
        return _make_peer_relation(secret_id=None)

    @pytest.fixture
    def secrets_ready(
        self, mocked_model: MagicMock, peer_relation_with_secret: MagicMock
    ) -> Secrets:
        """Secrets instance backed by a model that has the consolidated secret."""
        mocked_model.get_secret.return_value = _make_secret(_FULL_CONTENT)
        return Secrets(mocked_model, peer_relation_with_secret)

    @pytest.fixture
    def secrets_no_peer(self, mocked_model: MagicMock) -> Secrets:
        return Secrets(mocked_model, peer_relation=None)

    # --- create ---

    def test_create_stores_secret_id_in_peer_databag(
        self, mocked_model: MagicMock, peer_relation_empty: MagicMock
    ) -> None:
        created_secret = _make_secret(_FULL_CONTENT)
        mocked_model.app.add_secret.return_value = created_secret
        secrets = Secrets(mocked_model, peer_relation_empty)

        secrets.create("sk", "bt", "bp")

        mocked_model.app.add_secret.assert_called_once_with(
            {SECRET_KEY_KEY: "sk", BOOTSTRAP_TOKEN_KEY: "bt", BOOTSTRAP_PASSWORD_KEY: "bp"},
            label=SECRETS_LABEL,
        )
        peer_relation_empty.data[mocked_model.app][SECRETS_PEER_KEY] = created_secret.id

    def test_create_is_idempotent(
        self, mocked_model: MagicMock, peer_relation_with_secret: MagicMock
    ) -> None:
        secrets = Secrets(mocked_model, peer_relation_with_secret)

        secrets.create("sk", "bt", "bp")

        mocked_model.app.add_secret.assert_not_called()

    def test_create_without_peer_relation_does_not_raise(self, mocked_model: MagicMock) -> None:
        secrets = Secrets(mocked_model, peer_relation=None)
        mocked_model.app.add_secret.return_value = _make_secret(_FULL_CONTENT)

        # Should not raise even when there is no peer relation to write to
        secrets.create("sk", "bt", "bp")

    # --- is_ready ---

    def test_is_ready_true(self, secrets_ready: Secrets) -> None:
        assert secrets_ready.is_ready() is True

    def test_is_ready_false_no_peer_relation(self, secrets_no_peer: Secrets) -> None:
        assert secrets_no_peer.is_ready() is False

    def test_is_ready_false_secret_not_found(
        self, mocked_model: MagicMock, peer_relation_with_secret: MagicMock
    ) -> None:
        mocked_model.get_secret.side_effect = SecretNotFoundError("not found")
        secrets = Secrets(mocked_model, peer_relation_with_secret)

        assert secrets.is_ready() is False

    # --- to_env_vars ---

    def test_to_env_vars(self, secrets_ready: Secrets) -> None:
        env = secrets_ready.to_env_vars()

        assert env["AUTHENTIK_SECRET_KEY"] == "test-secret-key"
        assert env["AUTHENTIK_BOOTSTRAP_TOKEN"] == "test-token"
        assert env["AUTHENTIK_BOOTSTRAP_PASSWORD"] == "test-password"

    # --- Properties ---

    def test_secret_key_property(self, secrets_ready: Secrets) -> None:
        assert secrets_ready.secret_key == "test-secret-key"

    def test_secret_key_not_available(self, secrets_no_peer: Secrets) -> None:
        with pytest.raises(SecretError, match="Secret key is not available"):
            _ = secrets_no_peer.secret_key

    def test_bootstrap_token_property(self, secrets_ready: Secrets) -> None:
        assert secrets_ready.bootstrap_token == "test-token"

    def test_bootstrap_token_not_available(self, secrets_no_peer: Secrets) -> None:
        with pytest.raises(SecretError, match="Bootstrap token is not available"):
            _ = secrets_no_peer.bootstrap_token

    def test_bootstrap_password_property(self, secrets_ready: Secrets) -> None:
        assert secrets_ready.bootstrap_password == "test-password"

    def test_bootstrap_password_not_available(self, secrets_no_peer: Secrets) -> None:
        with pytest.raises(SecretError, match="Bootstrap password is not available"):
            _ = secrets_no_peer.bootstrap_password
