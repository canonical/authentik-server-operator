# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helper class to manage the charm's secrets."""

from collections.abc import ValuesView

from ops import Model, SecretNotFoundError

from constants import (
    BOOTSTRAP_PASSWORD_KEY,
    BOOTSTRAP_PASSWORD_LABEL,
    BOOTSTRAP_TOKEN_KEY,
    BOOTSTRAP_TOKEN_LABEL,
    SECRET_KEY_KEY,
    SECRET_KEY_LABEL,
)
from env_vars import EnvVars
from exceptions import SecretError


class Secrets:
    """An abstraction of the charm secret management."""

    KEYS = (SECRET_KEY_KEY, BOOTSTRAP_TOKEN_KEY, BOOTSTRAP_PASSWORD_KEY)
    LABELS = (SECRET_KEY_LABEL, BOOTSTRAP_TOKEN_LABEL, BOOTSTRAP_PASSWORD_LABEL)

    def __init__(self, model: Model) -> None:
        self._model = model

    def __getitem__(self, label: str) -> dict[str, str] | None:
        """Get secret content by label."""
        if label not in self.LABELS:
            return None
        try:
            secret = self._model.get_secret(label=label)
        except SecretNotFoundError:
            return None
        return secret.get_content()

    def __setitem__(self, label: str, content: dict[str, str]) -> None:
        """Create a secret with the given label and content.

        Idempotent: if the secret already exists, the existing value is kept.
        """
        if label not in self.LABELS:
            raise ValueError(f"Invalid label: '{label}'. Valid labels are: {self.LABELS}.")
        if self[label] is not None:
            return
        self._model.app.add_secret(content, label=label)

    def values(self) -> ValuesView:
        """Get all secret values."""
        secret_contents = {}
        for key, label in zip(self.KEYS, self.LABELS):
            try:
                secret = self._model.get_secret(label=label)
            except SecretNotFoundError:
                continue
            else:
                secret_contents[key] = secret.get_content()
        return secret_contents.values()

    def to_env_vars(self) -> EnvVars:
        """Get secret env vars."""
        return {
            "AUTHENTIK_SECRET_KEY": self.secret_key,
            "AUTHENTIK_BOOTSTRAP_TOKEN": self.bootstrap_token,
            "AUTHENTIK_BOOTSTRAP_PASSWORD": self.bootstrap_password,
        }

    def is_ready(self) -> bool:
        """Check if all secrets are ready."""
        secret_contents = {}
        for key, label in zip(self.KEYS, self.LABELS):
            try:
                secret = self._model.get_secret(label=label)
                secret_contents[key] = secret.get_content()
            except SecretNotFoundError:
                return False
        return all(secret_contents.values())

    @property
    def secret_key(self) -> str:
        """The AUTHENTIK_SECRET_KEY value.

        Raises:
            SecretError: If the secret key secret has not been created yet.
        """
        content = self[SECRET_KEY_LABEL]
        if content is None:
            raise SecretError("Secret key is not available")
        return content[SECRET_KEY_KEY]

    @property
    def bootstrap_token(self) -> str:
        """The AUTHENTIK_BOOTSTRAP_TOKEN value.

        Raises:
            SecretError: If the bootstrap token secret has not been created yet.
        """
        content = self[BOOTSTRAP_TOKEN_LABEL]
        if content is None:
            raise SecretError("Bootstrap token is not available")
        return content[BOOTSTRAP_TOKEN_KEY]

    @property
    def bootstrap_password(self) -> str:
        """The AUTHENTIK_BOOTSTRAP_PASSWORD value.

        Raises:
            SecretError: If the bootstrap password secret has not been created yet.
        """
        content = self[BOOTSTRAP_PASSWORD_LABEL]
        if content is None:
            raise SecretError("Bootstrap password is not available")
        return content[BOOTSTRAP_PASSWORD_KEY]
