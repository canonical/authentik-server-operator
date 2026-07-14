## Context

The Charmed Authentik Server requires high-availability external L7 access to route user authentication requests, administrative workflows, OIDC/SAML federated identity handshakes, and API interactions.
This design transitions the server's external ingress from the legacy `ingress` relation to the standard `traefik-route` relation interface, mimicking the proven architecture used in the `hydra-operator`.

## Goals / Non-Goals

**Goals:**
- Provide native high-availability HTTP/HTTPS ingress routing via Traefik.
- Explicitly define and route all mandatory L7 paths required for complete Authentik operations.
- Dynamically synchronize external URL configurations with other related charms when ingress endpoints change.
- Ensure thorough unit and integration test coverage for ingress routing and dynamic URL updates.

**Non-Goals:**
- Handling L4/TCP or LDAPS routing inside the server operator (managed strictly by the outpost operator).

## Decisions

### Decision 1: Adopt `traefik-route` over legacy `ingress`
- **Rationale**: The `traefik-route` interface allows the charm to supply a custom Traefik JSON configuration. This configuration defines routers and services in Traefik's native file-provider format, enabling precise L7 path matching and SSL termination domain declarations on a shared Traefik LoadBalancer service.

### Decision 2: Routing Paths and JSON Template Design
- **Paths to Expose**:
  - `/` (User Portal & Admin Console)
  - `/oauth2` (OAuth2/OIDC endpoints)
  - `/api` (Authentik Core API)
  - `/.well-known` (OIDC discovery/metadata)
  - `/flows` (Authentication and policy flow screens)
  - `/static` (Static assets)
  - `/media` (Custom branding media)
- **Configuration Template**:
  We will introduce `templates/traefik-route.json.j2`. It renders a dynamic JSON structure representing the Traefik HTTP routing configuration.
  ```json
  {
    "http": {
      "routers": {
        "juju-{{ identifier }}-router-root": {
          "entryPoints": ["web", "websecure"],
          "rule": "PathPrefix(`/`, `/oauth2`, `/api`, `/.well-known`, `/flows`, `/static`, `/media`)",
          "service": "juju-{{ identifier }}-service",
          "tls": {
            "domains": [{ "main": "{{ external_host }}" }]
          }
        }
      },
      "services": {
        "juju-{{ identifier }}-service": {
          "loadBalancer": {
            "servers": [{ "url": "http://{{ app }}.{{ model }}.svc.cluster.local:9000" }]
          }
        }
      }
    }
  }
  ```

### Decision 3: Integration with Charm Lifecycle & Relations
- **Mandatory Ingress & Base URL Sync**:
  The `traefik-route` relation is a mandatory integration. The charm will enter a blocked state (`BlockedStatus`) if the relation is missing, or if the public route is not secure (does not use HTTPS). It will be in a waiting state (`WaitingStatus`) if the relation is present but waiting for Traefik to become ready with an external host.
  When Traefik establishes the route and provides the `external_host` and `scheme` (e.g. `https://authentik.example.com`), the charm MUST:
  1. Update `AUTHENTIK_OPTS__BASE_URL` in `DEFAULT_SERVER_ENV` inside the Pebble environment.
  2. Re-render Pebble layer config and restart/replan the service.
  3. Propagate the updated base URL to the LDAP outpost via the `authentik-server-info` relation databag.
- **Handling Events**:
  We will observe `relation-joined`, `relation-changed`, and `relation-broken` on the `traefik-route` relation. Each event will trigger the standard holistic `_reconcile()` loop to update the config dynamically.

## Risks / Trade-offs

- **[Risk]**: Misconfigured Traefik rules could intercept unrelated traffic.
  - **Mitigation**: Use namespaced router/service names prefixed with `juju-{{ model }}-{{ app }}` to guarantee isolation.

## Verification Plan

### Automated Tests
- **Unit Tests**:
  - Mock `TraefikRouteRequirer` data (`external_host` and `scheme`).
  - Verify that `_reconcile()` correctly renders `templates/traefik-route.json.j2` and populates the relation databag.
  - Assert that `AUTHENTIK_OPTS__BASE_URL` is written to Pebble environment variables.
  - Assert that the updated external URL is synchronized to the `authentik-server-info` databag.
  - Test relation-broken event to ensure fallback to standard internal service URL.
- **Integration Tests**:
  - Deploy `authentik-server-operator` alongside `traefik-k8s`.
  - Establish `traefik-route` relation.
  - Query the Traefik external IP/host and verify successful L7 routing to Authentik endpoints.

### Manual Verification
- Run integration tests with the `--no-juju-teardown` flag to keep the active Juju model and the local Kubernetes environment running.
- Access the local cluster, query Traefik's service VIP, and hit the exposed HTTP paths to verify routing and portal page rendering.
