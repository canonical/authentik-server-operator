# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helper class to manage the charm's secrets."""

from ops import Model, Relation, SecretNotFoundError

from constants import (
    BOOTSTRAP_PASSWORD_KEY,
    BOOTSTRAP_TOKEN_KEY,
    SECRET_KEY_KEY,
    SECRETS_LABEL,
    SECRETS_PEER_KEY,
)
from env_vars import EnvVars
from exceptions import SecretError


class Secrets:
    """An abstraction of the charm secret management.

    All three credential values (secret-key, bootstrap-token, bootstrap-password)
    are stored in a single Juju secret.  The secret ID is persisted in the peer
    app databag under ``SECRETS_PEER_KEY`` so that every unit can retrieve it
    without relying on label lookups.
    """

    def __init__(self, model: Model, peer_relation: Relation | None) -> None:
        self._model = model
        self._peer_relation = peer_relation

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def _secret_id(self) -> str | None:
        """The Juju secret ID stored in the peer app databag, or None."""
        if self._peer_relation is None:
            return None
        return self._peer_relation.data[self._model.app].get(SECRETS_PEER_KEY)

    def _get_content(self) -> dict[str, str] | None:
        """Fetch the secret content, or None if the secret does not exist yet."""
        secret_id = self._secret_id
        if not secret_id:
            return None
        try:
            return self._model.get_secret(id=secret_id).get_content(refresh=True)
        except SecretNotFoundError:
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create(
        self,
        secret_key: str,
        bootstrap_token: str,
        bootstrap_password: str,
    ) -> None:
        """Create the consolidated secret and record its ID in the peer databag.

        Idempotent: does nothing if the secret already exists.

        Args:
            secret_key: Value for ``AUTHENTIK_SECRET_KEY``.
            bootstrap_token: Value for ``AUTHENTIK_BOOTSTRAP_TOKEN``.
            bootstrap_password: Value for ``AUTHENTIK_BOOTSTRAP_PASSWORD``.
        """
        if self._secret_id is not None:
            return
        secret = self._model.app.add_secret(
            {
                SECRET_KEY_KEY: secret_key,
                BOOTSTRAP_TOKEN_KEY: bootstrap_token,
                BOOTSTRAP_PASSWORD_KEY: bootstrap_password,
            },
            label=SECRETS_LABEL,
        )
        if self._peer_relation is not None:
            self._peer_relation.data[self._model.app][SECRETS_PEER_KEY] = secret.id

    def is_ready(self) -> bool:
        """Return True when the secret exists and all keys are populated."""
        content = self._get_content()
        if not content:
            return False
        return all(
            content.get(k) for k in (SECRET_KEY_KEY, BOOTSTRAP_TOKEN_KEY, BOOTSTRAP_PASSWORD_KEY)
        )

    def to_env_vars(self) -> EnvVars:
        """Return the three Authentik credential environment variables."""
        return {
            "AUTHENTIK_SECRET_KEY": self.secret_key,
            "AUTHENTIK_BOOTSTRAP_TOKEN": self.bootstrap_token,
            "AUTHENTIK_BOOTSTRAP_PASSWORD": self.bootstrap_password,
        }

    @property
    def secret_key(self) -> str:
        """The AUTHENTIK_SECRET_KEY value.

        Raises:
            SecretError: If the secret has not been created yet.
        """
        content = self._get_content()
        if not content or not content.get(SECRET_KEY_KEY):
            raise SecretError("Secret key is not available")
        return content[SECRET_KEY_KEY]

    @property
    def bootstrap_token(self) -> str:
        """The AUTHENTIK_BOOTSTRAP_TOKEN value.

        Raises:
            SecretError: If the secret has not been created yet.
        """
        content = self._get_content()
        if not content or not content.get(BOOTSTRAP_TOKEN_KEY):
            raise SecretError("Bootstrap token is not available")
        return content[BOOTSTRAP_TOKEN_KEY]

    @property
    def bootstrap_password(self) -> str:
        """The AUTHENTIK_BOOTSTRAP_PASSWORD value.

        Raises:
            SecretError: If the secret has not been created yet.
        """
        content = self._get_content()
        if not content or not content.get(BOOTSTRAP_PASSWORD_KEY):
            raise SecretError("Bootstrap password is not available")
        return content[BOOTSTRAP_PASSWORD_KEY]
