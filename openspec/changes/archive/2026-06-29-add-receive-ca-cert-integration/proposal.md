## Why

The Authentik Server operator needs to trust secure external endpoints (such as a database, directory service, or ingress proxy) that use certificates signed by a private or custom Certificate Authority (CA). Implementing the `receive-ca-cert` integration enables the operator to ingest, trust, and distribute these private CA certificates to both the charm host and the workload container, ensuring secure TLS handshakes.

## What Changes

- **New Integration**: Expose a `receive-ca-cert` integration of interface `certificate_transfer` to import custom CA certificates.
- **Charm Host Trust**: Run `update-ca-certificates` on the charm container so subprocesses or standard Python HTTP clients can trust endpoints signed by the custom CA.
- **Workload Container Trust**: Push the merged CA certificates bundle into the workload container so that Authentik's processes trust the custom CA.

## Non-goals

- Outbound certificate/key provision (this charm only consumes CA certificates, it does not sign or distribute its own certs).
- Direct certificate renewal or signing flow handling (relies entirely on the peer `certificate_transfer` provider).

## Capabilities

### New Capabilities

- `receive-ca-cert`: Import and trust custom CA certificates inside the charm host and Authentik workload container.

### Modified Capabilities

None.

## Impact

- **Affected source modules**:
  - `src/constants.py` (add relation name and certificate path constants)
  - `src/integrations.py` (implement `TLSCertificates` integration wrapper)
  - `src/services.py` (implement `update_ca_certs` in `WorkloadService`)
  - `src/charm.py` (orchestrate initialization, observers, `_ensure_tls()`, and force-restart on change)
- **Charm definition**: `charmcraft.yaml` requires `receive-ca-cert` interface.
- **External Dependencies**: Fetches the `charms.certificate_transfer_interface.v1.certificate_transfer` library.
