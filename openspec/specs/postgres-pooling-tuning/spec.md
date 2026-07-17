# postgres-pooling-tuning Specification

## Purpose
TBD - created by archiving change add-postgres-pooling-configs. Update Purpose after archive.
## Requirements
### Requirement: Expose PostgreSQL pooling and health check configurations
The charm SHALL expose `postgresql_disable_server_side_cursors` (boolean), `postgresql_conn_health_checks` (boolean), and `postgresql_conn_max_age` (integer) configurations in `charmcraft.yaml`.

#### Scenario: Verify config schema and defaults
- **WHEN** the charm metadata is parsed
- **THEN** the options exist with defaults `false`, `false`, and `0` respectively.

### Requirement: Register default environment variables in env_vars.py
The system SHALL register default values for `AUTHENTIK_POSTGRESQL__DISABLE_SERVER_SIDE_CURSORS`, `AUTHENTIK_POSTGRESQL__CONN_HEALTH_CHECKS`, and `AUTHENTIK_POSTGRESQL__CONN_MAX_AGE` in `DEFAULT_SERVER_ENV` in `src/env_vars.py`.

#### Scenario: Verify registration in default server environment
- **WHEN** `DEFAULT_SERVER_ENV` is retrieved
- **THEN** the new environment keys map to string defaults `"false"`, `"false"`, and `"0"`.

### Requirement: Map charm configuration to environment variables
The system SHALL read the new configuration options and translate them to their corresponding environment variables in `CharmConfig.to_env_vars()` in `src/configs.py`.

#### Scenario: Verify environment variable generation
- **WHEN** `to_env_vars()` is executed
- **THEN** the boolean configs are mapped to stringified lowercase values and integer configs are converted to strings.

