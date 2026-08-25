# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the Secrets class."""

from unittest.mock import MagicMock, create_autospec

import pytest
from ops import Model, ModelError, SecretNotFoundError

from constants import (
    BOOTSTRAP_PASSWORD_KEY,
    BOOTSTRAP_TOKEN_KEY,
    SECRET_KEY_KEY,
    SECRETS_LABEL,
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


class TestSecrets:
    @pytest.fixture
    def mocked_model(self) -> MagicMock:
        return create_autospec(Model)

    @pytest.fixture
    def secrets_ready(self, mocked_model: MagicMock) -> Secrets:
        """Secrets instance backed by a model that resolves the secret by label."""
        mocked_model.get_secret.return_value = _make_secret(_FULL_CONTENT)
        return Secrets(mocked_model)

    @pytest.fixture
    def secrets_missing(self, mocked_model: MagicMock) -> Secrets:
        # The labeled secret cannot be resolved.
        mocked_model.get_secret.side_effect = SecretNotFoundError("not found")
        return Secrets(mocked_model)

    # --- create ---

    def test_create_adds_labeled_secret_when_absent(self, mocked_model: MagicMock) -> None:
        # No labeled secret exists yet, so create() must add one.
        mocked_model.get_secret.side_effect = SecretNotFoundError("not found")
        mocked_model.app.add_secret.return_value = _make_secret(_FULL_CONTENT)
        secrets = Secrets(mocked_model)

        secrets.create("sk", "bt", "bp")

        mocked_model.app.add_secret.assert_called_once_with(
            {SECRET_KEY_KEY: "sk", BOOTSTRAP_TOKEN_KEY: "bt", BOOTSTRAP_PASSWORD_KEY: "bp"},
            label=SECRETS_LABEL,
        )

    def test_create_is_idempotent_when_labeled_secret_exists(
        self, mocked_model: MagicMock
    ) -> None:
        # The labeled secret already exists (e.g. after unit recreation): adopt it.
        mocked_model.get_secret.return_value = _make_secret(_FULL_CONTENT)
        secrets = Secrets(mocked_model)

        secrets.create("sk", "bt", "bp")

        mocked_model.get_secret.assert_called_once_with(label=SECRETS_LABEL)
        mocked_model.app.add_secret.assert_not_called()

    def test_create_adopts_when_add_secret_reports_already_exists(
        self, mocked_model: MagicMock
    ) -> None:
        # First label lookup misses, add_secret races an "already exists" ModelError,
        # then the second label lookup adopts the concurrently created secret and a
        # third resolves its content.
        mocked_model.get_secret.side_effect = [
            SecretNotFoundError("not found"),
            _make_secret(_FULL_CONTENT),
            _make_secret(_FULL_CONTENT),
        ]
        mocked_model.app.add_secret.side_effect = ModelError("secret ... already exists")
        secrets = Secrets(mocked_model)

        # Must not propagate the "already exists" error.
        secrets.create("sk", "bt", "bp")

    def test_create_reraises_when_add_secret_fails_and_secret_absent(
        self, mocked_model: MagicMock
    ) -> None:
        # add_secret fails and no labeled secret can be adopted: the error propagates.
        mocked_model.get_secret.side_effect = SecretNotFoundError("not found")
        mocked_model.app.add_secret.side_effect = ModelError("boom")
        secrets = Secrets(mocked_model)

        with pytest.raises(ModelError):
            secrets.create("sk", "bt", "bp")

    # --- is_ready ---

    def test_is_ready_true(self, secrets_ready: Secrets) -> None:
        assert secrets_ready.is_ready() is True

    def test_is_ready_false_secret_not_found(self, secrets_missing: Secrets) -> None:
        assert secrets_missing.is_ready() is False

    # --- to_env_vars ---

    def test_to_env_vars(self, secrets_ready: Secrets) -> None:
        env = secrets_ready.to_env_vars()

        assert env["AUTHENTIK_SECRET_KEY"] == "test-secret-key"
        assert env["AUTHENTIK_BOOTSTRAP_TOKEN"] == "test-token"
        assert env["AUTHENTIK_BOOTSTRAP_PASSWORD"] == "test-password"

    # --- Properties ---

    def test_secret_key_property(self, secrets_ready: Secrets) -> None:
        assert secrets_ready.secret_key == "test-secret-key"

    def test_secret_key_not_available(self, secrets_missing: Secrets) -> None:
        with pytest.raises(SecretError, match="Secret key is not available"):
            _ = secrets_missing.secret_key

    def test_bootstrap_token_property(self, secrets_ready: Secrets) -> None:
        assert secrets_ready.bootstrap_token == "test-token"

    def test_bootstrap_token_not_available(self, secrets_missing: Secrets) -> None:
        with pytest.raises(SecretError, match="Bootstrap token is not available"):
            _ = secrets_missing.bootstrap_token

    def test_bootstrap_password_property(self, secrets_ready: Secrets) -> None:
        assert secrets_ready.bootstrap_password == "test-password"

    def test_bootstrap_password_not_available(self, secrets_missing: Secrets) -> None:
        with pytest.raises(SecretError, match="Bootstrap password is not available"):
            _ = secrets_missing.bootstrap_password

    def test_any_unit_resolves_content_by_label(self, mocked_model: MagicMock) -> None:
        # No peer pointer is involved: a Secrets on any unit resolves purely by label.
        mocked_model.get_secret.return_value = _make_secret(_FULL_CONTENT)
        secrets = Secrets(mocked_model)

        assert secrets.secret_key == "test-secret-key"
        assert secrets.bootstrap_token == "test-token"
        assert secrets.bootstrap_password == "test-password"
        mocked_model.get_secret.assert_called_with(label=SECRETS_LABEL)

    # --- Read amplification / revision tracking ---

    def test_secret_is_resolved_once_per_instance(self, mocked_model: MagicMock) -> None:
        # `Model.get_secret()` is a hook tool and it retrieves the content, so holding
        # the resolved Secret is what keeps a hook down to a single round trip.
        mocked_model.get_secret.return_value = _make_secret(_FULL_CONTENT)
        secrets = Secrets(mocked_model)

        assert secrets.is_ready() is True
        secrets.to_env_vars()

        assert mocked_model.get_secret.call_count == 1

    def test_reads_tracked_revision_by_default(self, mocked_model: MagicMock) -> None:
        # refresh=True re-issues the unit's secret backend token, so steady-state
        # reads must never ask for the latest revision.
        secret = _make_secret(_FULL_CONTENT)
        mocked_model.get_secret.return_value = secret
        secrets = Secrets(mocked_model)

        assert secrets.is_ready() is True
        secrets.to_env_vars()

        assert all(
            call.kwargs.get("refresh") is not True for call in secret.get_content.mock_calls
        )

    def test_refresh_reuses_the_resolved_secret(self, mocked_model: MagicMock) -> None:
        # One refreshed read, not a fresh lookup followed by a refreshed read.
        secret = _make_secret(_FULL_CONTENT)
        mocked_model.get_secret.return_value = secret
        secrets = Secrets(mocked_model)
        assert secrets.is_ready() is True

        secrets.refresh()

        assert mocked_model.get_secret.call_count == 1
        assert secret.get_content.call_args_list[-1].kwargs == {"refresh": True}

    def test_refresh_exposes_the_new_revision(self, mocked_model: MagicMock) -> None:
        stale = _make_secret(_FULL_CONTENT)
        mocked_model.get_secret.return_value = stale
        secrets = Secrets(mocked_model)
        assert secrets.secret_key == "test-secret-key"

        stale.get_content.return_value = {**_FULL_CONTENT, SECRET_KEY_KEY: "rotated-key"}
        secrets.refresh()

        assert secrets.secret_key == "rotated-key"

    def test_create_exposes_the_content_it_wrote(self, mocked_model: MagicMock) -> None:
        # _ensure_secrets checks is_ready() before create(), and Juju cannot serve a
        # just-added secret back within the same hook. ops returns a Secret carrying
        # the written content, so holding it is what makes the credentials readable to
        # later callers in this hook.
        mocked_model.get_secret.side_effect = SecretNotFoundError("not found")
        written = {
            SECRET_KEY_KEY: "sk",
            BOOTSTRAP_TOKEN_KEY: "bt",
            BOOTSTRAP_PASSWORD_KEY: "bp",
        }
        mocked_model.app.add_secret.return_value = _make_secret(written)
        secrets = Secrets(mocked_model)
        assert secrets.is_ready() is False

        secrets.create("sk", "bt", "bp")

        assert secrets.is_ready() is True
        assert secrets.secret_key == "sk"

    def test_create_adopts_the_content_of_a_concurrent_secret(
        self, mocked_model: MagicMock
    ) -> None:
        # The locally generated content was never stored, so the adopted secret's own
        # content must win.
        mocked_model.get_secret.side_effect = [
            SecretNotFoundError("not found"),
            _make_secret(_FULL_CONTENT),
        ]
        mocked_model.app.add_secret.side_effect = ModelError("already exists")
        secrets = Secrets(mocked_model)

        secrets.create("sk", "bt", "bp")

        assert secrets.secret_key == "test-secret-key"
