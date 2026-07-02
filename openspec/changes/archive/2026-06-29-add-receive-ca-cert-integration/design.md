## Context

The Charmed Identity Platform requires secure communication between components. When secure endpoints use certificates signed by custom/private Certificate Authorities (CAs) instead of public authorities, the Authentik server operator must trust those custom certificates. To do this, the charm must integrate with a certificate provider via the `certificate_transfer` interface, reconcile the CA certificates inside the charm host, update the system trust store using `update-ca-certificates`, and synchronize the updated bundle into the workload container so that Authentik and its outposts can successfully complete TLS handshakes.

## Goals / Non-Goals

**Goals:**
- Implement the `receive-ca-cert` integration of interface `certificate_transfer` in `charmcraft.yaml`.
- Load, merge, and clean custom CA certificates from the relation databags.
- Programmatically update the local CA certificates of the charm host.
- Transfer the updated CA bundle into the Authentik workload container.
- Trigger a force restart of the Pebble workload service when the CA bundle changes, ensuring that the Go-based outposts/processes pick up the updated system trust.

**Non-Goals:**
- Support custom/private CAs on outbound TLS endpoints hosted by Authentik (this design is purely for trust of external servers by Authentik, not for Authentik's own server certs).
- Direct management or rotation of individual certificate pairs (recommends standard `tls-certificates` or `ingress` solutions).

## Decisions

### Decision 1: Shared storage paths for certificates
- **Option A (Chosen)**: Write the custom certificates to `/tmp/charm/charm-certificates.crt`, output the system certificates to `/tmp/ca-certificates.crt`, and push them to `/etc/ssl/certs/ca-certificates.crt` in the workload container. This mirrors the paths from `tenant-service-operator`, which is a tested and verified pattern in this platform.
- **Option B**: Write directly to `/usr/local/share/ca-certificates/` in the charm host. This requires root permissions inside the charm container, which might violate the non-root charm user policy.

### Decision 2: Centralized reconciliation and restart trigger
- **Option A (Chosen)**: Run `_ensure_tls()` as part of the centralized holistic reconciliation handler. Set `self._tls_cert_changed = True` when the certificates update, and trigger a restart during Pebble planning using `self._pebble.plan(..., force_restart=self._tls_cert_changed)`. This is highly robust and avoids missing updates.
- **Option B**: Restart the Pebble service in a separate relation event handler. This violates the "holistic handler" design pattern described in `AGENTS.md`.

## Risks / Trade-offs

- **[Risk]**: Invalid certificate syntax in the relation databag breaks the `update-ca-certificates` subprocess.
  - **Mitigation**: Catch `subprocess.CalledProcessError`, log the exception, and remove the broken file so the next reconciliation run retries cleanly.
- **[Risk]**: Running standard HTTP requests during the startup phase before the custom CA is processed fails.
  - **Mitigation**: Place `_ensure_tls` high up in the sequence of reconciliation tasks, just before the service plan is executed.
