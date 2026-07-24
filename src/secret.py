# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helper class to manage the charm's secrets."""

from ops import Model, ModelError

from constants import (
    BOOTSTRAP_PASSWORD_KEY,
    BOOTSTRAP_TOKEN_KEY,
    SECRET_KEY_KEY,
    SECRETS_LABEL,
)
from env_vars import EnvVars
from exceptions import SecretError


class Secrets:
    """An abstraction of the charm secret management.

    All three credential values (secret-key, bootstrap-token, bootstrap-password)
    are stored in a single application-owned Juju secret, resolved by its
    deterministic label ``SECRETS_LABEL``. The label is identical on every unit,
    so any unit can retrieve the secret without a peer-relation pointer.
    """

    def __init__(self, model: Model) -> None:
        self._model = model

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_secret_by_label(self):
        """Return the labeled Juju secret, or None if it cannot be resolved.

        A missing secret (``SecretNotFoundError``) or a transient controller error
        (``ModelError``) both yield None so this best-effort lookup never crashes a
        status/reconcile pass; it simply re-resolves on the next event.
        """
        try:
            return self._model.get_secret(label=SECRETS_LABEL)
        except ModelError:
            # SecretNotFoundError is a ModelError subclass; both are treated as
            # "not resolvable this pass".
            return None

    def _get_content(self) -> dict[str, str] | None:
        """Fetch the secret content, or None if the secret does not exist yet.

        Resolves the secret solely by its deterministic label, so any unit can read
        it regardless of which unit created it and without a peer-relation pointer.
        """
        secret = self._get_secret_by_label()
        if secret is None:
            return None
        return secret.get_content(refresh=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create(
        self,
        secret_key: str,
        bootstrap_token: str,
        bootstrap_password: str,
    ) -> None:
        """Create the consolidated secret (leader only), idempotent by label.

        Get-or-create keyed on the deterministic label: if the labeled Juju secret
        already exists it is adopted and left untouched, so a pointer/secret desync
        after unit recreation or an interrupted hook cannot trigger an "already
        exists" ModelError and crash-loop the hook.

        Args:
            secret_key: Value for ``AUTHENTIK_SECRET_KEY``.
            bootstrap_token: Value for ``AUTHENTIK_BOOTSTRAP_TOKEN``.
            bootstrap_password: Value for ``AUTHENTIK_BOOTSTRAP_PASSWORD``.
        """
        if self._get_secret_by_label() is not None:
            return
        content = {
            SECRET_KEY_KEY: secret_key,
            BOOTSTRAP_TOKEN_KEY: bootstrap_token,
            BOOTSTRAP_PASSWORD_KEY: bootstrap_password,
        }
        try:
            self._model.app.add_secret(content, label=SECRETS_LABEL)
        except ModelError:
            # The labeled secret may have appeared between the lookup above and
            # add_secret (concurrent/interrupted hook). Adopt it rather than
            # propagating an "already exists" model error.
            if self._get_secret_by_label() is None:
                raise

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
