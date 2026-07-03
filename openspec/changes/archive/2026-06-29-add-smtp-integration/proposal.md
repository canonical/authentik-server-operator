## Why

Authentik Server requires SMTP email configurations to support essential out-of-the-box flows such as password resets, user invitation signups, and transaction email notifications. Integrating with the Canonical SMTP Integrator charm allows operators to centrally manage and route email delivery for the Authentik service without hardcoding or manually managing credentials within the workload.

## What Changes

- Add the standard `smtp` relation utilizing the standard `smtp` Juju interface.
- Automatically fetch SMTP relay configuration (host, port, auth, TLS settings) and feed it into the Authentik workload's environment variables (`AUTHENTIK_EMAIL__*`).
- Restart/replan the Pebble service automatically upon SMTP relation data updates.

## Non-goals

- Implementing localized SMTP configuration or in-charm SMTP relaying services.
- Providing manual Authentik UI configuration options for mail transfer agents.

## Capabilities

### New Capabilities
- `smtp-integration`: Integrates the Authentik Server charm with the SMTP Integrator to dynamically populate mail server configurations for global transactions.

### Modified Capabilities
<!-- No modified capabilities -->

## Impact

- `charmcraft.yaml`: Define the `smtp` relation and interface.
- `src/constants.py`: Define SMTP relation and interface constants.
- `src/integrations.py`: Implement type-safe parsing and environment conversion for SMTP credentials.
- `src/charm.py`: Initialize the SMTP requirer and integrate it into holistic reconciliation.
- `src/services.py`: Merge SMTP environment settings during Pebble layer rendering.
