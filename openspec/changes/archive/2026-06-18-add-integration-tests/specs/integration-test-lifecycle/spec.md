## ADDED Requirements

### Requirement: Integration test suite uses pytest-jubilant
The integration tests SHALL use `pytest-jubilant>=2,<3` for model lifecycle management. The `juju` fixture provided by the plugin SHALL be used instead of a hand-rolled model factory. Setup tests SHALL be marked with `@pytest.mark.juju_setup` and teardown tests with `@pytest.mark.juju_teardown`.

#### Scenario: Model is created and destroyed automatically
- **WHEN** the integration test module runs
- **THEN** pytest-jubilant creates a temporary Juju model before tests and destroys it after the module completes

#### Scenario: Setup tests can be skipped with --no-juju-setup
- **WHEN** `pytest` is invoked with `--no-juju-setup --juju-model <name>`
- **THEN** tests marked `juju_setup` are skipped and the existing model is reused

#### Scenario: Teardown tests can be skipped with --no-juju-teardown
- **WHEN** `pytest` is invoked with `--no-juju-teardown`
- **THEN** tests marked `juju_teardown` are skipped and the model is preserved

### Requirement: Deploy stage with PostgreSQL and authentik-worker dependencies
The setup test SHALL deploy `postgresql-k8s` from the `14/stable` channel, `authentik-worker` from the `latest/edge` channel, and the charm-under-test with its OCI image resource. PostgreSQL SHALL be integrated via the `pg-database` relation and authentik-worker via the `authentik-cluster` relation. The test SHALL wait for all three applications to reach `ActiveStatus`.

#### Scenario: Charm deploys and reaches ActiveStatus with PostgreSQL and worker
- **WHEN** the setup test deploys PostgreSQL, authentik-worker, and authentik-server and integrates them
- **THEN** all three applications reach `ActiveStatus` within 15 minutes

### Requirement: Health check validates workload endpoint
The integration tests SHALL verify the workload health endpoint is accessible by sending an HTTP GET request to `http://{unit_address}:9000/-/health/live/` and asserting a successful response.

#### Scenario: Health endpoint returns success after deployment
- **WHEN** the charm is deployed and active
- **THEN** an HTTP GET to `/-/health/live/` on port 9000 returns a successful status code

### Requirement: Scale up test validates HA
The integration tests SHALL scale the authentik-server application to 2 units and wait for all units to reach `ActiveStatus`.

#### Scenario: Application scales to 2 units successfully
- **WHEN** the application is scaled to 2 units
- **THEN** both units reach `ActiveStatus` within 5 minutes

### Requirement: Integration removal and recreation test
The integration tests SHALL temporarily remove each required integration (`pg-database` and `authentik-cluster`) and verify the charm transitions to `BlockedStatus`, then restore the integration and verify the charm returns to `ActiveStatus`.

#### Scenario: Removing pg-database causes BlockedStatus
- **WHEN** the `pg-database` integration is removed
- **THEN** authentik-server reaches `BlockedStatus` within 10 minutes

#### Scenario: Re-adding pg-database restores ActiveStatus
- **WHEN** the `pg-database` integration is restored
- **THEN** authentik-server and PostgreSQL both reach `ActiveStatus` within 10 minutes

#### Scenario: Removing authentik-cluster causes BlockedStatus
- **WHEN** the `authentik-cluster` integration is removed
- **THEN** authentik-server reaches `BlockedStatus` within 10 minutes

#### Scenario: Re-adding authentik-cluster restores ActiveStatus
- **WHEN** the `authentik-cluster` integration is restored
- **THEN** authentik-server and authentik-worker both reach `ActiveStatus` within 10 minutes

### Requirement: Scale down test validates cluster stability
The integration tests SHALL scale the application back to 1 unit and verify it reaches `ActiveStatus`.

#### Scenario: Application scales down to 1 unit successfully
- **WHEN** the application is scaled down to 1 unit
- **THEN** the remaining unit reaches `ActiveStatus` within 5 minutes

### Requirement: Removal test cleans up the application
The teardown test SHALL remove the authentik-server application and verify it is no longer present in the model.

#### Scenario: Application is removed from the model
- **WHEN** `juju remove-application` is called on authentik-server
- **THEN** the application is no longer listed in the model status

### Requirement: Utility module provides status predicates and helpers
The `tests/integration/utils.py` module SHALL provide status predicate functions (`all_active`, `is_blocked`, `unit_number`, `and_`), a `remove_integration` context manager that temporarily removes and restores a Juju integration with retry logic, and a `get_unit_address` helper.

#### Scenario: remove_integration temporarily removes and restores an integration
- **WHEN** `remove_integration` is used as a context manager
- **THEN** the integration is removed on entry and restored (with retry) on exit

#### Scenario: Status predicates work with jubilant.wait
- **WHEN** a status predicate like `all_active("app")` is passed to `juju.wait(ready=...)`
- **THEN** it correctly evaluates the Juju status object
