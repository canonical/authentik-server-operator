## Context

The Authentik Server Operator Juju charm needs SMTP configurations to deliver system emails (e.g. registration, recovery, MFA alerts). The Canonical SMTP Integrator provides standard `smtp` relation data. We need to implement support in the Authentik Server charm to parse this data and set environment variables.

## Goals / Non-Goals

**Goals:**
- Provide standard `smtp` relation support.
- Map the SMTP relation values to Authentik's `AUTHENTIK_EMAIL__*` workload environment variables dynamically.
- Automatically restart/replan the service on SMTP changes.

**Non-Goals:**
- Managing in-charm SMTP relaying or local MTA hosting.

## Decisions

### 1. Integration library selection: `charms.smtp_integrator.v0.smtp`
- **Choice**: Use the standard `SmtpRequires` requirer wrapper.
- **Rationale**: This is the officially supported SMTP relation wrapper in the Canonical operator landscape, which supports pydantic models and secrets naturally.

### 2. Environmental mapping: double-underscore namespaces
- **Choice**: Map fields into `AUTHENTIK_EMAIL__HOST`, `AUTHENTIK_EMAIL__PORT`, `AUTHENTIK_EMAIL__USERNAME`, `AUTHENTIK_EMAIL__PASSWORD`, `AUTHENTIK_EMAIL__USE_TLS`, `AUTHENTIK_EMAIL__USE_SSL`, and `AUTHENTIK_EMAIL__FROM` dynamically.
- **Rationale**: Double-underscores are the standard namespace separators used by Authentik to parse YAML-nested config fields directly from environment variables.

## Risks / Trade-offs

- **Risk**: Overlapping or conflicting values between TLS and SSL configurations.
- **Mitigation**: Standard mapping protocol: STARTTLS sets `USE_TLS=true` and `USE_SSL=false`. Implicit SSL/TLS sets `USE_SSL=true` and `USE_TLS=false`. Other values map both to `false`.
