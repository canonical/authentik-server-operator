## Context

Deploying Authentik behind an external database transaction pooling manager (like PgBouncer or Pgpool) requires disabling server-side cursors to avoid queries breaking across connections. To maintain connection robustness, we also need health-checks and maximum age limits for database connections. Authentik exposes these django configurations via specific environment variables:
- `AUTHENTIK_POSTGRESQL__DISABLE_SERVER_SIDE_CURSORS`
- `AUTHENTIK_POSTGRESQL__CONN_HEALTH_CHECKS`
- `AUTHENTIK_POSTGRESQL__CONN_MAX_AGE`

Exposing these options at the Juju charm level gives users fine-grained control over database connection tuning.

## Goals / Non-Goals

**Goals:**
- Provide clear Juju configuration settings for PostgreSQL transaction pooling and connection options.
- Support correct translation of Juju configurations (which may be boolean or integers) into environment variables conforming to Authentik environment variable expectations.
- Ensure correct default environment variables are registered in `src/env_vars.py`.

**Non-Goals:**
- Handling database transaction pooling inside the Authentik Server Juju charm itself (this is managed by external components or PgBouncer).
- Modifying default Juju postgresql client relation integrations.

## Decisions

### Decision 1: Boolean Stringification
- **Choice**: Convert Juju boolean configs `postgresql_disable_server_side_cursors` and `postgresql_conn_health_checks` using `str(...).lower()` to produce `"true"` or `"false"`.
- **Rationale**: Python Django/Authentik environment config parsing expects lowercase strings `"true"` or `"false"` to correctly interpret booleans. Directly converting Python's `True`/`False` produces `"True"`/`"False"`, which might not be parsed correctly depending on the exact backend library.

### Decision 2: Integer Stringification
- **Choice**: Map `postgresql_conn_max_age` with `str(self._config.get("postgresql_conn_max_age", 0))`.
- **Rationale**: Since the env vars returned by `EnvVarConvertible` must be string values, converting the Juju integer configuration directly to a string is straightforward and safe.

## Risks / Trade-offs

- **[Risk]** User sets non-integer values for connection max age.
  - **[Mitigation]** The configuration type is declared as `int` in `charmcraft.yaml`. Juju automatically validates and rejects non-integer configuration values at CLI/API level.
- **[Risk]** Case sensitivity in boolean environment values.
  - **[Mitigation]** Standardize on `.lower()` conversion.
