## 1. API Error Model

- [x] 1.1 Add typed Authentik API exceptions for not-found, authentication, authorization, conflict, transient, and request-validation failures in `src/exceptions.py`
- [x] 1.2 Refactor request execution in `src/authentik_api.py` to classify HTTP failures and apply bounded retries only to connection, 429, and retryable 5xx failures
- [x] 1.3 Add deterministic provider/application lookup helpers and ambiguous-create recovery in `src/authentik_api.py`
- [x] 1.4 Replace heuristic scope matching with exact explicit-scope lookup and remove all-mappings fallback in `src/authentik_api.py`

## 2. Ownership and Reconciliation

- [x] 2.1 Add managed OAuth namespace and cache-schema constants in `src/constants.py`
- [x] 2.2 Implement model-UUID-based managed resource identities and exact active legacy adoption in `src/oauth.py`
- [x] 2.3 Persist partial provider state and write `config_hash` only after all provider/application operations succeed in `src/oauth.py`
- [x] 2.4 Replace numeric-suffix global garbage collection with ownership-proven cleanup in `src/oauth.py`
- [x] 2.5 Retain cleanup cache entries until application and provider deletion each succeeds or reports not-found in `src/oauth.py`
- [x] 2.6 Gate startup API access on workload readiness and propagate exhausted typed failures from `src/charm.py`

## 3. Unit Tests

- [x] 3.1 Add API classification, bounded retry, ambiguous-create, and exact-scope tests in `tests/unit/test_authentik_api.py`
- [x] 3.2 Add managed ownership, active legacy adoption, partial creation/update, and retryable cleanup tests in `tests/unit/test_oauth.py`
- [x] 3.3 Update focused charm tests in `tests/unit/test_charm.py` for startup gating and typed failure propagation

## 4. Verification

- [x] 4.1 Run focused API, OAuth reconciler, and charm unit tests
- [x] 4.2 Run repository formatting, lint, and full unit environments after all implementation work is merged
