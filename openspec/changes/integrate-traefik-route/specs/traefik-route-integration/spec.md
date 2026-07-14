## Purpose
The `traefik-route-integration` specification defines how the Authentik Server Operator negotiates external L7 HTTP/HTTPS ingress paths using Juju's `traefik_route` relation interface. This ensures all core user portal, administrator console, OIDC discovery, authentication flows, and API endpoints are exposed under a single, highly available virtual IP/external hostname managed by Traefik.

## ADDED Requirements

### Requirement: Expose traefik-route integration
The charm SHALL define a `traefik-route` integration of interface `traefik_route` to declare L7 path-routing rules.

#### Scenario: Charm configures traefik-route relation
- **WHEN** the `traefik-route` relation is established
- **THEN** the charm configures custom entrypoints and path routing rules for OIDC, API, Console, and flow endpoints on Traefik

### Requirement: Propagate dynamic endpoint updates
The charm SHALL dynamically update the external URL advertised in any outgoing relations (e.g. `authentik-server-info`) whenever the ingress external hostname or scheme changes.

#### Scenario: Base URL changes upon ingress hostname update
- **WHEN** the external hostname on the Traefik relation is updated
- **THEN** the charm triggers reconciliation, recalculates the base external URL, updates its internal config, and advertises the new URL in relation databags
