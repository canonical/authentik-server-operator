# smtp-integration Specification

## Purpose

The Authentik Server requires SMTP email configurations to support critical identity and user management flows such as password resets, user invitation signups, multi-factor authentication setup, and transactional notifications. Integrating with the Canonical SMTP Integrator charm allows operators to centrally manage, secure, and route email delivery for the Authentik workload without manually configuring credentials.
## Requirements
### Requirement: SMTP relation integration
The Authentik Server Operator SHALL support integrating with an SMTP Integrator charm via the `smtp` relation interface.

#### Scenario: Successful integration setup
- **WHEN** the `smtp` relation is established with the SMTP Integrator charm and valid relation data is populated
- **THEN** the charm SHALL extract the SMTP relay credentials and write them to the workload environment variables `AUTHENTIK_EMAIL__*` in the Pebble layer

