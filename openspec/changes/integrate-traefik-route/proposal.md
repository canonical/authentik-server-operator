## Why

The Authentik Server requires high-availability external HTTP/HTTPS access for the Admin Console, User Portal, and OIDC/SAML endpoints. Standardizing on the `traefik-route` relation allows the charm to dynamically declare custom routing configurations and paths natively on Traefik, establishing a robust and scalable L7 ingress path.

## What Changes

- **Adopt `traefik-route` Interface**: Replace the legacy `ingress` relation with the `traefik-route` relation interface, enabling the server charm to define explicit path-routing policies on Traefik.
- **Unified Path Routing**: Configure Traefik to route all core Authentik paths (Console, API, OIDC, flows, and static files) to the backend server pods.
- **Dynamic Endpoint Updates**: Keep the external URL in the `authentik-server-info` relation databag dynamically in sync whenever the ingress configuration or external hostname changes.

## Non-goals

- Implementing or handling any L4 TCP or LDAPS traffic routing in the server operator (handled exclusively by the LDAP outpost operator).
- Supporting legacy `ingress` interface relations once `traefik-route` is active.

## Capabilities

### New Capabilities
- `traefik-route-integration`: Configure and manage custom Traefik routing rules and paths for Authentik Server L7 traffic.

### Modified Capabilities
<!-- Leave empty as we do not modify any existing spec requirements -->

## Impact

- `src/charm.py`: Define `TraefikRouteRequirer` handlers and trigger unified `_reconcile()` upon ingress changes.
- `src/integrations.py`: Implement the `TraefikRouteIntegration` helper class with Pydantic validation and JSON config rendering.
- `src/constants.py`: Add port and relation name constants.
- `charmcraft.yaml`: Declare the `traefik-route` relation interface.
