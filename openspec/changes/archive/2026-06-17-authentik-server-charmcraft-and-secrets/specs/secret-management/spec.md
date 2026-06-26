# Secret Management

## MODIFIED Requirements

### Requirement: _ensure_secrets() must be idempotent across restarts

`_ensure_secrets()` in `charm.py` MUST check whether each Juju secret already exists
(by label) before creating it. If the secret exists, no new secret is created. If it
does not exist, it is created with the appropriate label. This prevents
`SecretAlreadyExistsError` on subsequent startups.

Labels used:

| Secret | Label |
|--------|-------|
| secret key | `authentik-secret-key` |
| bootstrap token | `authentik-bootstrap-token` |
| bootstrap password | `authentik-bootstrap-password` |

```python
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

#### Scenario: First startup creates secrets without error

Given the charm is freshly deployed and no Juju secrets exist, when `_ensure_secrets()`
is called for the first time, then three Juju secrets are created (one per label) and
their IDs are written to the peer app databag.

#### Scenario: Second startup does not raise SecretAlreadyExistsError

Given the charm has been restarted and secrets already exist with the expected labels,
when `_ensure_secrets()` is called again, then no exception is raised and the peer
databag still contains the correct secret IDs.

#### Scenario: Non-leader unit skips secret creation

Given the current unit is not the leader, when `_ensure_secrets()` is called, then
the function returns immediately without creating or accessing any Juju secrets.

#### Scenario: Secret IDs stored in peer app databag

Given `_ensure_secrets()` runs successfully on the leader unit, then the peer app
databag contains `secret_key_secret_id`, `bootstrap_token_secret_id`, and
`bootstrap_password_secret_id` keys mapping to valid Juju secret IDs.

### Requirement: _ensure_secrets() must return early when peer relation is absent

`_ensure_secrets()` MUST return early if `self.model.get_relation(PEER_RELATION_NAME)`
returns `None`, since writing to the peer databag requires the relation to exist.

#### Scenario: No peer relation on install event

Given the peer relation has not yet been established (e.g. very first `install` event
before `peer-relation-created`), when `_ensure_secrets()` is called, then the function
returns without error and no secrets are created.
