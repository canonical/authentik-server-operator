## MODIFIED Requirements

### Requirement: Provision OAuth Relation

The Authentik Server charm SHALL implement the `provides` side of the `oauth` Juju integration interface, and register OIDC providers and client applications directly with the Authentik Server API during active state-based reconciliation.

#### Scenario: Registering an OIDC Client Application
- **WHEN** a client charm integrates with the Authentik Server charm via the `oauth` relation
- **THEN** the Authentik Server charm MUST register the provider and application via the Authentik REST API using a unique slug `{remote_app_name}-{relation_id}` to support multi-tenancy, and write the generated client credentials to the Juju relation databag.

### Requirement: Centralized OIDC Endpoint Updates

The Authentik Server charm MUST update the `issuer_url` (format `{host}/application/o/{application_slug}/`) and other OIDC discovery endpoints dynamically within its holistic reconciliation handler whenever the external hostname, ingress configuration, or relation settings change.

#### Scenario: Ingress Update Triggers Endpoint Changes
- **WHEN** the ingress URL or client configuration is updated or revoked
- **THEN** the Authentik Server charm MUST update the endpoints in the active `oauth` relation databags and in the registered Authentik applications.

## ADDED Requirements

### Requirement: Delete OAuth Client on Relation Removal

The Authentik Server charm MUST clean up and delete the corresponding OIDC provider and application in Authentik when an `oauth` relation is removed/broken.

#### Scenario: OAuth Relation Removed
- **WHEN** an `oauth` relation is broken
- **THEN** the Authentik Server charm MUST delete the corresponding provider and application from Authentik via the Authentik REST API.
