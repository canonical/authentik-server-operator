# authentik_server_info Library

## ADDED Requirements

### Requirement: AuthentikServerInfoProvider must publish host and credentials to relation databag

`lib/charms/authentik_server/v0/authentik_server_info.py` MUST implement
`AuthentikServerInfoProvider`. When `publish(host, bootstrap_token, bootstrap_password)`
is called by the leader unit, the method must:
1. Create or update two Juju secrets with labels `authentik-server-info-bootstrap-token`
   and `authentik-server-info-bootstrap-password`.
2. Grant both secrets to every active `authentik-server-info` relation.
3. Write `host`, `bootstrap_token_secret_id`, and `bootstrap_password_secret_id` to
   the provider app databag for every relation.

`publish()` MUST be idempotent: calling it multiple times must not raise errors.

The provider MUST emit `on.ready` on `relation_created` and `relation_joined`.

#### Scenario: Provider publishes all fields on relation joined

Given an `authentik-server-info` relation is joined and the unit is leader, when
`publish("https://authentik.example.com", "tok", "pass")` is called, then the provider
app databag contains `host`, `bootstrap_token_secret_id`, and
`bootstrap_password_secret_id`, and both secrets are granted to the relation.

#### Scenario: publish() is idempotent

Given `publish()` has already been called once, when it is called again with the same
arguments, then no `SecretAlreadyExistsError` is raised and the databag values remain
correct.

#### Scenario: Non-leader skips publish

Given the current unit is not the leader, when `publish(...)` is called, then the
method returns without error and no secrets or databag entries are created.

### Requirement: AuthentikServerInfoRequirer must read host and credentials from relation databag

`AuthentikServerInfoRequirer` MUST implement a `get_info()` method that returns a
`ServerInfoData` dataclass (fields: `host`, `bootstrap_token`, `bootstrap_password`)
when the relation is complete, or `None` when any required field is missing.

The requirer MUST emit `on.ready` on `relation_changed` when all three databag fields
(`host`, `bootstrap_token_secret_id`, `bootstrap_password_secret_id`) are present.

#### Scenario: get_info returns None without relation

Given no `authentik-server-info` relation exists, when `get_info()` is called, then
`None` is returned.

#### Scenario: get_info returns ServerInfoData when relation is complete

Given an `authentik-server-info` relation exists and the provider has written all three
fields and granted both secrets, when `get_info()` is called, then a `ServerInfoData`
object is returned with the correct `host`, `bootstrap_token`, and `bootstrap_password`.

#### Scenario: on.ready fires when all databag fields are present

Given the requirer is observing `relation_changed`, when the provider writes all three
required fields to the databag, then `AuthentikServerInfoRequirerEvents.ready` is emitted.

### Requirement: LIBPATCH must be incremented after changes to authentik_server_info library

Any modification to `lib/charms/authentik_server/v0/authentik_server_info.py` MUST
increment the `LIBPATCH` constant so consumers can detect the update.

#### Scenario: LIBPATCH is incremented

Given the library file has been modified, when the file is inspected, then the
`LIBPATCH` value is greater than before the change.
