## ADDED Requirements

### Requirement: SMTP relation integration
The Authentik Server Operator SHALL support integrating with an SMTP Integrator charm via the `smtp` relation interface.

#### Scenario: Successful integration setup
- **WHEN** the `smtp` relation is established with the SMTP Integrator charm and valid relation data is populated
- **THEN** the charm SHALL extract the SMTP relay credentials and write them to the workload environment variables `AUTHENTIK_EMAIL__*` in the Pebble layer
