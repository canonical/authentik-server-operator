## ADDED Requirements

### Requirement: Typed Authentik API failures

The Authentik API client SHALL distinguish not-found, authentication, authorization, conflict, transient transport/server, and permanent request-validation failures.

#### Scenario: Authentication failure
- **WHEN** Authentik responds with HTTP 401
- **THEN** the client SHALL raise an authentication error without retrying

#### Scenario: Authorization failure
- **WHEN** Authentik responds with HTTP 403
- **THEN** the client SHALL raise an authorization error without retrying

#### Scenario: Missing resource
- **WHEN** an object lookup or deletion responds with HTTP 404
- **THEN** the client SHALL report the object as absent without classifying it as transient

### Requirement: Bounded transient retries

The Authentik API client SHALL retry only connection failures, HTTP 429 responses, and retryable 5xx responses within a bounded hook-time budget.

#### Scenario: Transient request recovers
- **WHEN** a retryable request fails transiently and succeeds within the retry budget
- **THEN** the client SHALL return the successful response

#### Scenario: Retry budget is exhausted
- **WHEN** retryable failures continue beyond the configured budget
- **THEN** the client SHALL raise a transient API error to the reconciliation boundary

#### Scenario: Permanent validation error
- **WHEN** Authentik responds with a non-retryable 4xx validation error
- **THEN** the client SHALL raise a permanent request error without retrying

### Requirement: Ambiguous creates are recovered by identity

The client and reconciler SHALL NOT blindly repeat a non-idempotent create request after an ambiguous response and SHALL first query Authentik by the object's deterministic managed identity.

#### Scenario: POST commits but its response is lost
- **WHEN** Authentik creates a provider but the client receives a timeout before the response
- **THEN** the next reconciliation SHALL discover and reuse that provider instead of creating a duplicate

### Requirement: Readiness probe tolerates first-boot API errors

`is_service_available()` SHALL report not-ready for ANY Authentik API error, including 401/403 raised while Authentik finishes first-boot bootstrap, not only transient transport errors. OAuth reconciliation SHALL check readiness before issuing Authentik API calls so an unready API defers reconciliation instead of crashing the hook.

#### Scenario: First-boot authorization error
- **WHEN** the readiness probe receives HTTP 403 while Authentik is still initializing
- **THEN** it SHALL report not-ready and reconciliation SHALL defer without raising

#### Scenario: OAuth defers when the API is not ready
- **WHEN** the workload service is running but the Authentik API is not yet ready
- **THEN** OAuth reconciliation SHALL skip its API calls and return without error
