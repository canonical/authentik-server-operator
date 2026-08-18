# authentik_cluster Library

## Purpose

Defines the `authentik-cluster` library contract by which the Authentik Server charm shares cluster-formation data (such as the shared secret key and database configuration) with Authentik worker units, and the `LIBPATCH` revisioning discipline consumers rely on to detect updates.

## Requirements

### Requirement: AuthentikClusterProvider must publish cluster data to the relation databag

`lib/charms/authentik_server/v0/authentik_cluster.py` MUST implement
`AuthentikClusterProvider`. When `update_relations_app_data()` is called by the
leader unit with `secret_key`, `db_host`, `db_port`, `db_user`, `db_password`,
`db_name`, and optionally `server_version`, the method must:

1. Create or update an app-owned Juju secret labelled `authentik-secret-key`
   holding the content keys `secret-key` and `db-password`.
2. Grant that secret to every active `authentik-cluster` relation.
3. Write `ProviderData` into the provider app databag for every relation.

`ProviderData` MUST carry `secret_key_secret_id`, `db_host`, `db_port`,
`db_user`, `db_name`, and `server_version`. The sensitive `secret_key` and
`db_password` fields MUST be declared with `exclude=True` so they never
serialise into a databag: they travel only inside the Juju secret.

`update_relations_app_data()` MUST be idempotent: calling it multiple times must
not raise errors, and must update the existing secret's content rather than
attempting to create a second secret.

The provider MUST emit `on.ready` on `relation_created` so that `charm.py` can
reconcile holistically. It MUST also observe `relation_broken` to revoke the
secret grant from the departing relation, deleting the secret entirely when no
cluster relation remains. `relation_broken` MUST NOT emit `on.ready`.

#### Scenario: Provider publishes cluster data on relation created

Given an `authentik-cluster` relation is created and the unit is leader, when
`AuthentikClusterProvider.update_relations_app_data()` is called, then the Juju
secret labelled `authentik-secret-key` is created, granted to the relation, and
`secret_key_secret_id` appears in the provider app databag.

#### Scenario: No credential is written in plaintext to the databag

Given `update_relations_app_data()` has been called with a secret key and a
database password, when the provider app databag is inspected, then it contains
neither value, and both are retrievable only from the granted Juju secret.

#### Scenario: update_relations_app_data is idempotent

Given `update_relations_app_data()` has already been called once, when it is
called again, then no error is raised and the existing secret's content is
updated in place.

#### Scenario: Non-leader skips write

Given the current unit is not the leader, when `update_relations_app_data()` is
called, then the method returns without error and no secret is created or
modified.

### Requirement: AuthentikClusterRequirer must resolve cluster data from the granted Juju secret

`AuthentikClusterRequirer` MUST implement a `get_secret_key()` method that:

- Returns `None` when no `authentik-cluster` relation exists.
- Returns `None` when `secret_key_secret_id` is absent from the provider databag.
- Returns the `secret-key` value from the Juju secret when the relation is ready.

`AuthentikClusterRequirer` MUST additionally implement `get_database_config()`,
returning the database host, port, user, name, and the `db-password` value read
from the granted secret, and `get_server_version()`. The worker declares no
database relation of its own, so this is its only source of database credentials.

The requirer MUST emit `on.cluster_changed` on `relation_changed` whenever the
provider app databag is non-empty, and `on.cluster_removed` on
`relation_broken`. Emission is deliberately not conditioned on
`secret_key_secret_id`: readiness is determined separately by `is_ready()`,
which requires `secret_key_secret_id` to be present and the granted secret to be
readable. `AuthentikClusterRequirerEvents` declares only `cluster_changed` and
`cluster_removed`; there is no requirer-side `ready` event.

#### Scenario: get_secret_key returns None without relation

Given no `authentik-cluster` relation exists, when `get_secret_key()` is called,
then `None` is returned.

#### Scenario: get_secret_key returns value when relation is ready

Given an `authentik-cluster` relation exists and the provider has written
`secret_key_secret_id` to the databag and granted the secret, when `get_secret_key()`
is called, then the correct secret key string is returned.

#### Scenario: cluster_changed fires on relation_changed

Given the requirer is observing `relation_changed`, when the provider writes a
non-empty app databag, then `AuthentikClusterRequirerEvents.cluster_changed` is
emitted.

### Requirement: LIBPATCH must be incremented after changes to authentik_cluster library

Any modification to `lib/charms/authentik_server/v0/authentik_cluster.py` MUST
increment the `LIBPATCH` constant so consumers can detect the update.

#### Scenario: LIBPATCH is incremented

Given the library file has been modified, when the file is inspected, then the
`LIBPATCH` value is greater than before the change.
