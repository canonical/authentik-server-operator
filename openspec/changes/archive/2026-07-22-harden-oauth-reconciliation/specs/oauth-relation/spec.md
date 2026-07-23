## MODIFIED Requirements

### Requirement: Provision OAuth Relation

The Authentik Server charm SHALL implement the `provides` side of the `oauth` Juju integration, SHALL provision a uniquely owned Authentik provider and application for each relation, and SHALL expose client credentials only after those Authentik resources are synchronized.

#### Scenario: Registering an OIDC Client Application
- **WHEN** a client charm integrates with the Authentik Server charm via the `oauth` relation
- **THEN** the charm MUST generate unique client credentials, create or adopt the relation's owned provider and application, and publish the credentials with standard OIDC endpoint details

#### Scenario: A later provisioning step fails
- **WHEN** provider creation succeeds but application creation or update fails
- **THEN** the charm SHALL retain enough ownership state to reuse the provider and resume on the next reconciliation

### Requirement: Centralized OIDC Endpoint Updates

The Authentik Server charm MUST update the `issuer_url` and other OIDC discovery endpoints within holistic reconciliation whenever the external hostname or ingress configuration changes.

#### Scenario: Ingress Update Triggers Endpoint Changes
- **WHEN** the ingress URL is updated or revoked
- **THEN** the charm MUST update the OIDC endpoints in every active `oauth` relation databag

## ADDED Requirements

### Requirement: OAuth resource ownership

The charm SHALL mutate or delete only Authentik applications and providers whose ownership is proven by managed identity or persisted peer state.

#### Scenario: New resource namespace
- **WHEN** a new OAuth relation is provisioned
- **THEN** its Authentik objects SHALL use a namespace containing a stable server-model identity and the relation ID

#### Scenario: Active legacy resource migration
- **WHEN** an active relation has no new-format cache but its exact expected legacy application exists and references the expected provider
- **THEN** the charm MAY adopt and record that resource for the active relation

#### Scenario: Unrelated numeric slug
- **WHEN** an Authentik application outside the managed namespace has a slug ending in digits
- **THEN** the charm SHALL NOT infer ownership or delete it

### Requirement: Successful synchronization cache

The charm SHALL record a relation configuration hash only after every required provider and application mutation succeeds.

#### Scenario: Provider update fails
- **WHEN** the provider update fails but the application already exists
- **THEN** the configuration hash SHALL remain absent or unchanged and the next hook SHALL retry reconciliation

#### Scenario: Application update fails
- **WHEN** the application update fails after a successful provider update
- **THEN** the configuration hash SHALL remain absent or unchanged and the next hook SHALL resume reconciliation

### Requirement: Retriable orphan cleanup

The charm SHALL retain cleanup tracking until both the owned application and provider are confirmed deleted or already absent.

#### Scenario: Transient deletion failure
- **WHEN** deletion fails because of a transient API error
- **THEN** the cache entry SHALL remain for a later retry

#### Scenario: Objects are absent
- **WHEN** application and provider deletion each succeeds or reports not-found
- **THEN** the charm SHALL remove the relation's cache entry

### Requirement: Exact OIDC scope mappings

The charm SHALL resolve requested OIDC scopes through the explicit Authentik scope field and SHALL never fall back to every available property mapping.

#### Scenario: Supported scopes
- **WHEN** every requested scope has an exact Authentik mapping
- **THEN** only those mapping identifiers SHALL be attached to the provider

#### Scenario: Unsupported scope
- **WHEN** a requested scope has no exact mapping
- **THEN** reconciliation SHALL fail without attaching unrelated mappings
