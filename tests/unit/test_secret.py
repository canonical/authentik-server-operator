# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the Secrets class."""

from unittest.mock import MagicMock, create_autospec

import pytest
from ops import Model, SecretNotFoundError

from constants import (
    BOOTSTRAP_PASSWORD_KEY,
    BOOTSTRAP_PASSWORD_LABEL,
    BOOTSTRAP_TOKEN_KEY,
    BOOTSTRAP_TOKEN_LABEL,
    SECRET_KEY_KEY,
    SECRET_KEY_LABEL,
)
from exceptions import SecretError
from secret import Secrets


def _make_secret(content: dict[str, str]) -> MagicMock:
    """Create a mock secret object that returns the given content."""
    secret = MagicMock()
    secret.get_content.return_value = content
    return secret


class TestSecrets:
    @pytest.fixture
    def mocked_model(self) -> MagicMock:
        return create_autospec(Model)

    @pytest.fixture
    def secrets(self, mocked_model: MagicMock) -> Secrets:
        return Secrets(mocked_model)

    @pytest.fixture
    def model_with_all_secrets(self, mocked_model: MagicMock) -> MagicMock:
        """Model with all three secrets present."""

        def get_secret(label: str) -> MagicMock:
            contents = {
                SECRET_KEY_LABEL: {SECRET_KEY_KEY: "test-secret-key"},
                BOOTSTRAP_TOKEN_LABEL: {BOOTSTRAP_TOKEN_KEY: "test-token"},
                BOOTSTRAP_PASSWORD_LABEL: {BOOTSTRAP_PASSWORD_KEY: "test-password"},
            }
            return _make_secret(contents[label])

        mocked_model.get_secret.side_effect = get_secret
        return mocked_model

    # --- __getitem__ ---

    def test_getitem_exists(self, secrets: Secrets, mocked_model: MagicMock) -> None:
        content = {SECRET_KEY_KEY: "value"}
        mocked_model.get_secret.return_value = _make_secret(content)

        result = secrets[SECRET_KEY_LABEL]

        assert result == content

    def test_getitem_not_found(self, secrets: Secrets, mocked_model: MagicMock) -> None:
        mocked_model.get_secret.side_effect = SecretNotFoundError("not found")

        result = secrets[SECRET_KEY_LABEL]

        assert result is None

    def test_getitem_invalid_label(self, secrets: Secrets) -> None:
        result = secrets["invalid-label"]

        assert result is None

    # --- __setitem__ ---

    def test_setitem(self, secrets: Secrets, mocked_model: MagicMock) -> None:
        content = {SECRET_KEY_KEY: "value"}
        mocked_model.get_secret.side_effect = SecretNotFoundError("not found")

        secrets[SECRET_KEY_LABEL] = content

        mocked_model.app.add_secret.assert_called_once_with(content, label=SECRET_KEY_LABEL)

    def test_setitem_idempotent(self, secrets: Secrets, mocked_model: MagicMock) -> None:
        content = {SECRET_KEY_KEY: "value"}
        mocked_model.get_secret.return_value = _make_secret(content)

        secrets[SECRET_KEY_LABEL] = content

        mocked_model.app.add_secret.assert_not_called()

    def test_setitem_invalid_label(self, secrets: Secrets) -> None:
        with pytest.raises(ValueError, match="Invalid label"):
            secrets["invalid-label"] = {"key": "value"}

    # --- is_ready ---

    def test_is_ready_true(self, secrets: Secrets, model_with_all_secrets: MagicMock) -> None:
        assert secrets.is_ready() is True

    def test_is_ready_false(self, secrets: Secrets, mocked_model: MagicMock) -> None:
        mocked_model.get_secret.side_effect = SecretNotFoundError("not found")

        assert secrets.is_ready() is False

    # --- to_env_vars ---

    def test_to_env_vars(self, secrets: Secrets, model_with_all_secrets: MagicMock) -> None:
        env = secrets.to_env_vars()

        assert env["AUTHENTIK_SECRET_KEY"] == "test-secret-key"
        assert env["AUTHENTIK_BOOTSTRAP_TOKEN"] == "test-token"
        assert env["AUTHENTIK_BOOTSTRAP_PASSWORD"] == "test-password"

    # --- Properties ---

    def test_secret_key_property(self, secrets: Secrets, mocked_model: MagicMock) -> None:
        mocked_model.get_secret.return_value = _make_secret({SECRET_KEY_KEY: "my-key"})

        assert secrets.secret_key == "my-key"

    def test_secret_key_not_available(self, secrets: Secrets, mocked_model: MagicMock) -> None:
        mocked_model.get_secret.side_effect = SecretNotFoundError("not found")

        with pytest.raises(SecretError, match="Secret key is not available"):
            _ = secrets.secret_key

    def test_bootstrap_token_property(self, secrets: Secrets, mocked_model: MagicMock) -> None:
        mocked_model.get_secret.return_value = _make_secret({BOOTSTRAP_TOKEN_KEY: "my-token"})

        assert secrets.bootstrap_token == "my-token"

    def test_bootstrap_token_not_available(
        self, secrets: Secrets, mocked_model: MagicMock
    ) -> None:
        mocked_model.get_secret.side_effect = SecretNotFoundError("not found")

        with pytest.raises(SecretError, match="Bootstrap token is not available"):
            _ = secrets.bootstrap_token

    def test_bootstrap_password_property(self, secrets: Secrets, mocked_model: MagicMock) -> None:
        mocked_model.get_secret.return_value = _make_secret({BOOTSTRAP_PASSWORD_KEY: "my-pass"})

        assert secrets.bootstrap_password == "my-pass"

    def test_bootstrap_password_not_available(
        self, secrets: Secrets, mocked_model: MagicMock
    ) -> None:
        mocked_model.get_secret.side_effect = SecretNotFoundError("not found")

        with pytest.raises(SecretError, match="Bootstrap password is not available"):
            _ = secrets.bootstrap_password
