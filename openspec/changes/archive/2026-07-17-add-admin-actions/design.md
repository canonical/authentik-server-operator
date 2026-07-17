## Context

Administrators currently have no out-of-band mechanism via Juju to recover their Authentik administrative passwords if database records get out of sync with the bootstrap credentials stored in Juju peer secrets. We need to introduce two actions: `get-bootstrap-admin-credentials` (to retrieve bootstrap keys with an explicit warning about stale states) and `create-recovery-link` (to generate a secure, native, single-use, time-bound recovery link in the browser).

## Goals / Non-Goals

**Goals:**
* Define the action schema for `get-bootstrap-admin-credentials` and `create-recovery-link` in `charmcraft.yaml`.
* Implement the underlying CLI and service handlers cleanly according to the repository's physical separation design pattern.
* Safely parse the recovery token and construct the external URL using standard-compliant `urllib.parse.urljoin`.
* Provide integration test coverage executed specifically after the application scaling phase to verify these actions on active units.

**Non-Goals:**
* Attempting to automatically update Juju secrets when users modify passwords inside the Authentik UI.
* Touching database state directly via custom Python scripts or direct SQL queries.

## Decisions

### 1. Execute Authentik's Native Recovery Tool
* **Decision**: We will execute the native command `/lifecycle/ak create_recovery_key <duration> <username>` inside the workload container via Pebble.
* **Rationale**: Bypasses custom DB scripts or ORM hacks, ensuring full security, stability, and compatibility with future Authentik versions.

### 2. URL Concatenation via `urllib.parse.urljoin`
* **Decision**: Concat `self._authentik_host` and the parsed token path using `urllib.parse.urljoin` instead of string interpolation or `pathlib.Path`.
* **Rationale**: Eliminates risks of missing or duplicate slashes or platform-specific directory delimiters.

### 3. Add Warnings to `get-bootstrap-admin-credentials`
* **Decision**: Return a `warning` key in the action result dictionary and specify a warning in `charmcraft.yaml`.
* **Rationale**: Explicitly alerts operators that the returned password is a bootstrap credential and may be stale if the password was changed via the UI or recovery flow.

### 4. Integration Test Sequencing
* **Decision**: Add integration tests verifying both actions in `tests/integration/test_charm.py` specifically *after* the application scaling phase.
* **Rationale**: Ensures the actions run correctly on a clustered multi-unit deployment where leader and non-leader state checks can be validated.

## Risks / Trade-offs

* **[Risk]** The native `create_recovery_key` stdout format changes in future Authentik upstream releases.
  * **Mitigation**: Use a robust regular expression match `r"/recovery/use-token/[^/]+/??"` to extract only the path segment rather than parsing raw stdout line-by-line.
