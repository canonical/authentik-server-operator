# Secret Management

## Problem

`_ensure_secrets()` in `charm.py` calls `self.app.add_secret(...)` unconditionally without first checking if the secret already exists. On second startup this raises `SecretAlreadyExistsError`. No labels are passed so secrets cannot be found by label.

## Corrected Pattern

```python
from ops.exceptions import SecretNotFoundError
import secrets as _secrets

_SECRET_KEY_LABEL = "authentik-secret-key"
_BOOTSTRAP_TOKEN_LABEL = "authentik-bootstrap-token"
_BOOTSTRAP_PASSWORD_LABEL = "authentik-bootstrap-password"


def _ensure_secrets(self) -> None:
    if not self.unit.is_leader():
        return
    peer = self.model.get_relation(PEER_RELATION_NAME)
    if not peer:
        return
    self._ensure_secret(
        peer, "secret_key_secret_id", _SECRET_KEY_LABEL,
        lambda: {"secret-key": _secrets.token_hex(32)},
    )
    self._ensure_secret(
        peer, "bootstrap_token_secret_id", _BOOTSTRAP_TOKEN_LABEL,
        lambda: {"bootstrap-token": _secrets.token_hex(16)},
    )
    self._ensure_secret(
        peer, "bootstrap_password_secret_id", _BOOTSTRAP_PASSWORD_LABEL,
        lambda: {"bootstrap-password": _secrets.token_urlsafe(24)},
    )


def _ensure_secret(
    self,
    peer: ops.Relation,
    databag_key: str,
    label: str,
    content_factory: Callable[[], dict[str, str]],
) -> None:
    try:
        secret = self.model.get_secret(label=label)
    except SecretNotFoundError:
        secret = self.app.add_secret(content_factory(), label=label)
    if databag_key not in peer.data[self.app]:
        peer.data[self.app][databag_key] = secret.id
```

Note: `secrets` (Python stdlib) is imported as `_secrets` to avoid shadowing the `ops.Secret` type that may be referenced elsewhere.

## Peer relation requirement

`_ensure_secrets()` returns early if the peer relation is not yet joined. This is correct — the peer relation is always present for deployed Kubernetes charms but may not be joined on the very first `install` event before `peer-relation-created`.

## Acceptance Criteria

- `_ensure_secrets()` called twice produces no exception
- Three Juju secrets exist after first call, each with the correct label
- Peer app databag contains `secret_key_secret_id`, `bootstrap_token_secret_id`, `bootstrap_password_secret_id`
- Non-leader units skip secret creation without error
- Unit tests: first call creates secrets; second call finds by label and updates; non-leader is a no-op
