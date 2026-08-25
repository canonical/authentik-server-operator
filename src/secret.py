# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helper class to manage the charm's secrets."""

import logging
from functools import cached_property

from ops import Model, ModelError, Secret, SecretNotFoundError

from constants import (
    BOOTSTRAP_PASSWORD_KEY,
    BOOTSTRAP_TOKEN_KEY,
    SECRET_KEY_KEY,
    SECRETS_LABEL,
)
from env_vars import EnvVars
from exceptions import SecretError

logger = logging.getLogger(__name__)


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

    def _lookup(self) -> Secret | None:
        """Resolve the labeled Juju secret, or None if it cannot be resolved."""
        try:
            return self._model.get_secret(label=SECRETS_LABEL)
        except SecretNotFoundError:
            return None
        except ModelError:
            # A transient controller error must not crash a status pass; the next
            # event re-resolves.
            logger.warning("Could not resolve the %s secret this hook", SECRETS_LABEL)
            return None

    @cached_property
    def _secret(self) -> Secret | None:
        """The labeled secret, resolved once per hook.

        ``Model.get_secret()`` retrieves the content too, and ``Secret.get_content()``
        memoises it on the object, so holding the object makes every later read in
        this hook free.
        """
        return self._lookup()

    @property
    def _content(self) -> dict[str, str] | None:
        """The secret content at the revision this unit tracks."""
        return self._secret.get_content() if self._secret else None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Re-read the secret at its latest revision and start tracking it.

        Only for ``secret-changed`` / ``secret-expired``: refreshing on every hook
        defeats the controller's secret-backend token reuse, and on Kubernetes each
        newly issued token leaks a ``juju-secret-consumer-<uuid>`` ServiceAccount,
        Role and RoleBinding into the model namespace.
        """
        if self._secret is not None:
            self._secret.get_content(refresh=True)

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
        if self._secret is not None:
            return
        content = {
            SECRET_KEY_KEY: secret_key,
            BOOTSTRAP_TOKEN_KEY: bootstrap_token,
            BOOTSTRAP_PASSWORD_KEY: bootstrap_password,
        }
        try:
            # Seeds the resolved-secret cache: ops returns a Secret carrying the
            # content just written, which Juju itself cannot serve back until the
            # hook completes.
            self._secret = self._model.app.add_secret(content, label=SECRETS_LABEL)
        except ModelError:
            # A concurrent or interrupted hook created it first. Adopt it rather than
            # propagating an "already exists" error; its content is whatever that hook
            # generated, not the content above.
            adopted = self._lookup()
            if adopted is None:
                raise
            self._secret = adopted

    def is_ready(self) -> bool:
        """Return True when the secret exists and all keys are populated."""
        content = self._content
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
        content = self._content
        if not content or not content.get(SECRET_KEY_KEY):
            raise SecretError("Secret key is not available")
        return content[SECRET_KEY_KEY]

    @property
    def bootstrap_token(self) -> str:
        """The AUTHENTIK_BOOTSTRAP_TOKEN value.

        Raises:
            SecretError: If the secret has not been created yet.
        """
        content = self._content
        if not content or not content.get(BOOTSTRAP_TOKEN_KEY):
            raise SecretError("Bootstrap token is not available")
        return content[BOOTSTRAP_TOKEN_KEY]

    @property
    def bootstrap_password(self) -> str:
        """The AUTHENTIK_BOOTSTRAP_PASSWORD value.

        Raises:
            SecretError: If the secret has not been created yet.
        """
        content = self._content
        if not content or not content.get(BOOTSTRAP_PASSWORD_KEY):
            raise SecretError("Bootstrap password is not available")
        return content[BOOTSTRAP_PASSWORD_KEY]
