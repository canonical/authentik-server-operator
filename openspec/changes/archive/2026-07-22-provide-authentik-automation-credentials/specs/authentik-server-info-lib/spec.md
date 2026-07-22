## MODIFIED Requirements

### Requirement: AuthentikServerInfoProvider must publish host and credentials to relation databag

`lib/charms/authentik_server/v0/authentik_server_info.py` MUST implement `AuthentikServerInfoProvider`. When the leader unit publishes server info with an Authentik host and API token, the provider MUST:
1. Create or update one app-owned Juju secret, labeled `authentik-api-token`, containing only the `api-token` content key.
2. Grant that secret to every active `authentik-server-info` relation and revoke it on relation departure.
3. Write `authentik_host` and `authentik_token_secret_id` to the provider app databag for every relation.

No `bootstrap-token` content key, `bootstrap_password_secret_id` databag field, or bootstrap-password secret SHALL be published. Publication MUST be idempotent and MUST no-op on non-leader units.

#### Scenario: Provider publishes the api-token contract on relation joined

Given an `authentik-server-info` relation is joined and the unit is leader, when the leader publishes the host and API token, then the provider app databag contains `authentik_host` and `authentik_token_secret_id`, the granted secret contains only the `api-token` key, and no bootstrap-password secret or `bootstrap-token` key is present.

#### Scenario: Publication is idempotent

Given publication has already occurred once, when it runs again with the same inputs, then no `SecretAlreadyExistsError` is raised and the databag values remain correct.

#### Scenario: Non-leader skips publish

Given the current unit is not the leader, when publication is attempted, then it returns without error and no secrets or databag entries are created.

### Requirement: AuthentikServerInfoRequirer must read host and credentials from relation databag

`AuthentikServerInfoRequirer` MUST expose the Authentik `host` and the `api-token` value when the relation is complete, and MUST report not-ready (returning no server-info data) when any required field is missing. Readiness MUST NOT require a bootstrap password.

#### Scenario: Requirer reports not-ready without a complete relation

Given no complete `authentik-server-info` relation exists, when the requirer is queried, then it reports not-ready and returns no server-info data.

#### Scenario: Requirer resolves api-token when the relation is complete

Given the provider has written `authentik_host` and `authentik_token_secret_id` and granted the token secret, when the requirer is queried, then it returns the correct host and resolves the token from the `api-token` key, with no dependency on a bootstrap password.

#### Scenario: on.ready fires when host and token secret id are present

Given the requirer observes `relation_changed`, when the provider writes `authentik_host` and `authentik_token_secret_id`, then the requirer ready event is emitted.
