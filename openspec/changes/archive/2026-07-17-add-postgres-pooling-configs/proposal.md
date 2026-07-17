## Why

Deploying Authentik in environments utilizing external database transaction pooling (like PgBouncer or Pgpool) requires proper database connection configuration. Under such setups, server-side cursors can break across connections. In addition, dead or stale sockets must be proactively detected and discarded, and connection lifetime must be limited or recycled immediately to prevent connection issues.

## What Changes

- Add `postgresql_disable_server_side_cursors`, `postgresql_conn_health_checks`, and `postgresql_conn_max_age` configuration options to the `config.options` block of `charmcraft.yaml`.
- Register standard Authentik environment variable defaults in `src/env_vars.py`.
- Map the new charm configurations to their corresponding workload environment variables in `src/configs.py`.
- Update the unit tests to verify correct environment variable generation.

## Non-Goals

- Implementing any backend logic in the charm itself for database connection pooling.
- Modifying how the PostgreSQL client relation works or changing the `postgresql` charm behavior.

## Capabilities

### New Capabilities
- `postgres-pooling-tuning`: Introduction of database transaction pooling and health-checking configurations to optimize external PostgreSQL connections.

### Modified Capabilities

## Impact

- `charmcraft.yaml`: Exposes the three new configuration options to Juju users.
- `src/env_vars.py`: Defines the environment variables with standard default values in `DEFAULT_SERVER_ENV`.
- `src/configs.py`: Converts charm configurations into active environment variables.
