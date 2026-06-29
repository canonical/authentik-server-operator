## ADDED Requirements

### Requirement: Expose receive-ca-cert integration
The charm SHALL define a `receive-ca-cert` integration of interface `certificate_transfer` to import custom CA certificates.

#### Scenario: Charm configures receive-ca-cert relation
- **WHEN** the `receive-ca-cert` relation is established and updated with CA data
- **THEN** the charm fetches and merges the CA certificates from the relation databags

### Requirement: Propagate CA certificates to charm host
The charm SHALL update its local CA store with the merged CA certificates so that subprocesses or standard Python HTTP clients trust endpoints signed by the custom CA.

#### Scenario: Update-ca-certificates runs on the charm host
- **WHEN** the merged CA certificates bundle changes
- **THEN** the charm writes the certificates to the local charm certificates directory and executes `update-ca-certificates` successfully

### Requirement: Push CA certificates to workload container
The charm SHALL upload the merged CA certificates bundle into the workload container so that Authentik's processes trust endpoints signed by the custom CA.

#### Scenario: Pushing ca-certificates.crt to workload container
- **WHEN** the ca-certificates bundle on the charm host is updated
- **THEN** the charm pushes the merged CA certificates file to `/etc/ssl/certs/ca-certificates.crt` in the workload container and replans/restarts the Pebble service
