## ADDED Requirements

### Requirement: Provision OAuth Relation

The Authentik Server charm SHALL implement the `provides` side of the `oauth` Juju integration interface.

#### Scenario: Registering an OIDC Client Application
- **WHEN** a client charm integrates with the Authentik Server charm via the `oauth` relation
- **THEN** the Authentik Server charm MUST generate unique client credentials (`client_id` and `client_secret`) and populate them in the relation data along with standard OIDC provider endpoint details.

### Requirement: Centralized OIDC Endpoint Updates

The Authentik Server charm MUST update the `issuer_url` and other OIDC discovery endpoints dynamically within its holistic reconciliation handler whenever the external hostname or ingress configuration changes.

#### Scenario: Ingress Update Triggers Endpoint Changes
- **WHEN** the ingress URL is updated or revoked
- **THEN** the Authentik Server charm MUST update the `issuer_url` in all active `oauth` relation databags.
