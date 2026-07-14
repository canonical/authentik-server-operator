# ADR 001: Standardize on LDAPS (636) and Traefik Route for External Directory Ingress

## Status
Accepted

## Context
During the network design and topology investigation for the Authentik Kubernetes charms, several critical constraints were identified regarding external access to the directory service (provided by `authentik-ldap-outpost`):

1. **The Traefik TCP Scaling Bug (Issue #406)**: Exposing LDAP (Port 389) or LDAPS (Port 636) via the standard `ingress_per_unit` Juju relation forces Traefik to spin up a separate Kubernetes `LoadBalancer` service per backend unit. This blocks on clusters with limited external IPs and produces individual endpoints (e.g. `unit-0.outpost:389`, `unit-1.outpost:389`) rather than a single unified High-Availability VIP.
2. **`ingress-configurator` + HAProxy VM Limitations**: While a machine-based HAProxy model solves VIP requirements, `ingress-configurator` does not support L4 TCP routing natively today. Using this as a fallback requires the outpost charm to deploy an internal `LoadBalancer` Service and the administrator to manually map its External IP to HAProxy backends, breaking automation.
3. **Gateway API + Cilium Blockers**: The long-term ideal of using standard Kubernetes Gateway API with Cilium (via `gateway-api-integrator`) is blocked because neither the integrator charm nor Canonical Kubernetes' Cilium currently support the standard `TCPRoute` or `TLSRoute` custom resources.
4. **`traefik-route` Entrypoint Capability**: We discovered that the `traefik-route` relation interface allows backend charms to define custom entrypoints and routing configurations on Traefik directly, offering a native path to bypass the multi-unit scaling bug and expose a single high-availability LDAPS endpoint.

## Decision
We have decided to standardize on the following network design:

1. **Standardize strictly on LDAPS (636)**: We will exclusively support implicit LDAPS (Port 636) for secure connections and drop support for opportunistic StartTLS (Port 389). This simplifies our topology, ensures a "fail-closed" secure posture, and permits clean TLS termination at the ingress level.
2. **Use `traefik-route` as Primary Ingress (Phase 1)**: We will integrate the outpost with Traefik using the `traefik-route` relation to declare custom entrypoints and expose Port 636 under a single shared VIP.
3. **Keep HAProxy VM as Fallback (Phase 2)**: If Phase 1 encounters unexpected Juju-level blockages, we will fall back to manually mapping HAProxy backends to a custom Kubernetes `LoadBalancer` Service created by the outpost charm.
4. **Migrate to Gateway API + Cilium (Phase 3)**: When `gateway-api-integrator` and Canonical Kubernetes support `TCPRoute`, we will migrate to this fully cloud-native eBPF-optimized pattern.

## Consequences
- **Zero-Certificate Outpost**: TLS is terminated at the Traefik/HAProxy ingress level. The `authentik-ldap-outpost` container remains completely lightweight and free of certificates or local trust store management.
- **Unified Directory URL**: Consumers (like SSSD or PAM) configure a single `ldaps://<vip>:636` endpoint that automatically load-balances across all backend outpost units.
- **Client Migration**: Applications utilizing the directory that previously relied on cleartext LDAP with StartTLS must update their configurations to standard LDAPS. All relation databags will provide the `ldaps://` URI.
