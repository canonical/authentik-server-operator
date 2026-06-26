# authentik_cluster Library

## ADDED Requirements

### Requirement: AuthentikClusterProvider must write secret key to relation databag

`lib/charms/authentik_server/v0/authentik_cluster.py` MUST implement
`AuthentikClusterProvider`. When `set_secret_key(secret_key)` is called by the leader
unit, the method must:
1. Create or update a Juju secret with label `authentik-cluster-secret-key`.
2. Grant the secret to every active `authentik-cluster` relation.
3. Write `secret_key_secret_id` (the Juju secret ID) into the provider app databag
   for every relation.

`set_secret_key()` MUST be idempotent: calling it multiple times must not raise errors.

The provider MUST emit `on.ready` on `relation_created` and `relation_joined` so that
`charm.py` can react and call `set_secret_key()`.

#### Scenario: Provider publishes secret key on relation created

Given an `authentik-cluster` relation is created and the unit is leader, when
`AuthentikClusterProvider.set_secret_key("abc123")` is called, then the Juju secret
is created, granted to the relation, and `secret_key_secret_id` appears in the
provider app databag.

#### Scenario: set_secret_key is idempotent

Given `set_secret_key("abc123")` has already been called once, when it is called
again, then no `SecretAlreadyExistsError` is raised and the secret content is updated.

#### Scenario: Non-leader skips write

Given the current unit is not the leader, when `set_secret_key("abc123")` is called,
then the method returns without error and no secret is created or modified.

### Requirement: AuthentikClusterRequirer must read secret key from relation databag

`AuthentikClusterRequirer` MUST implement a `get_secret_key()` method that:
- Returns `None` when no `authentik-cluster` relation exists.
- Returns `None` when `secret_key_secret_id` is absent from the provider databag.
- Returns the `secret-key` value from the Juju secret when the relation is ready.

The requirer MUST emit `on.ready` on `relation_changed` when `secret_key_secret_id`
is present in the provider app databag.

#### Scenario: get_secret_key returns None without relation

Given no `authentik-cluster` relation exists, when `get_secret_key()` is called,
then `None` is returned.

#### Scenario: get_secret_key returns value when relation is ready

Given an `authentik-cluster` relation exists and the provider has written
`secret_key_secret_id` to the databag and granted the secret, when `get_secret_key()`
is called, then the correct secret key string is returned.

#### Scenario: on.ready fires on relation_changed with secret present

Given the requirer is observing `relation_changed`, when the provider writes
`secret_key_secret_id` to the databag, then `AuthentikClusterRequirerEvents.ready`
is emitted.

### Requirement: LIBPATCH must be incremented after changes to authentik_cluster library

Any modification to `lib/charms/authentik_server/v0/authentik_cluster.py` MUST
increment the `LIBPATCH` constant so consumers can detect the update.

#### Scenario: LIBPATCH is incremented

Given the library file has been modified, when the file is inspected, then the
`LIBPATCH` value is greater than before the change.
