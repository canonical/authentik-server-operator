## Context

The Authentik Server Operator is being extended to provide the `oauth` integration interface, allowing client charms to query OIDC configuration and register OAuth2/OIDC clients.

## Goals / Non-Goals

**Goals:**
- Implement the `provides` side of the `oauth` relation.
- Store client secrets safely as Juju secrets using the `OAuthProvider` utility methods.
- Coordinate OIDC endpoint generation with the ingress domain via `_holistic_handler` integration.

**Non-Goals:**
- Implementing fine-grained scopes or client administration via the Authentik container CLI/API (which is left as a future manual or automated task).

## Decisions

### 1. Integration of `charms.hydra.v0.oauth.OAuthProvider`
- **Choice**: Use the standard `OAuthProvider` helper class from the `hydra` library.
- **Rationale**: Since Canonical's standard Identity Platform charms (e.g. `identity-platform-admin-ui`) use the `charms.hydra.v0.oauth` library as requirer, using the corresponding `OAuthProvider` guarantees interface and schema compatibility.
- **Alternatives Considered**: Writing custom relation parsing logic. Rejected because it is error-prone and does not benefit from upstream updates.

### 2. Client Credentials Generation
- **Choice**: Generate random, secure `client_id` and `client_secret` values upon `client_created` event, storing them in Juju secrets.
- **Rationale**: Keeps client application registrations completely secure and separate per relation.

### 3. Integration with the Holistic Handler
- **Choice**: Call `_update_oauth_provider_info` from a dedicated `_ensure_oauth_relation` method inside `_holistic_handler`.
- **Rationale**: If the ingress domain changes (e.g. external host name changes), all client OIDC URLs must be updated. Re-running this inside the centralized holistic handler ensures the endpoints are kept perfectly in sync automatically.

## Risks / Trade-offs

- **[Risk]** Ingress domain is not ready when relation joins.
  - **Mitigation**: The OIDC endpoints are generated dynamically. If ingress is not ready, we fall back to the cluster-local service address (using `self._authentik_host`). Once ingress becomes ready, the holistic handler runs again and updates all relation databags automatically.
