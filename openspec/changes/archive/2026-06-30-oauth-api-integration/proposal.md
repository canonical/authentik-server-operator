## Why

The current oauth relation does not actually interact with the Authentik API to register OIDC client applications and providers. Additionally, using custom Juju events for client registration poses a data-loss risk upon pod/container restart. This change shifts client registration to active state-based reconciliation, supports multi-tenancy via formatted slugs, and ensures client deletion on relation removal.

## What Changes

- **Active State-Based Reconciliation**: Register and update OAuth clients dynamically inside the holistic `_ensure_oauth_relation` rather than relying on custom Juju events.
- **Authentik API Client**: Implement REST API interaction (creation, updating, deletion of OIDC providers and applications) using Authentik's `api/v3` endpoints.
- **Formatted Slug & Multi-Tenancy**: Use unique client identifier pattern `{remote_app_name}-{relation_id}` to allow multiple separate integrations.
- **Client Removal**: Automatically delete providers and applications in Authentik when an `oauth` relation is removed.

## Capabilities

### New Capabilities

<!-- No new capabilities -->

### Modified Capabilities

- `oauth-relation`: Update client registration requirements to use active state-based reconciliation and the Authentik REST API for creation and deletion.

## Impact

- **Affected files**: `src/charm.py`, `src/integrations.py`, `tests/unit/test_oauth.py`.
- **APIs**: Authentik REST API (`/api/v3/providers/oauth2/`, `/api/v3/core/applications/`).
- **Dependencies**: Uses `requests` for REST client calls.

## Non-goals

- Implementing other Authentik API endpoints (e.g., LDAP or SAML configuration) beyond OIDC providers and applications.
- Rewriting core Juju operator event system itself.
