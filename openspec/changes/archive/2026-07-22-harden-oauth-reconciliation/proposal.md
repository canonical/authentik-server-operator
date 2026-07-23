## Why

OAuth reconciliation currently infers ownership from any application slug ending in a number, records failed updates as synchronized, and drops deletion tracking after failed API calls. Because Authentik API mutations are external and non-transactional, hook failures can otherwise leave duplicate, orphaned, or incorrectly deleted resources.

## What Changes

- Give new charm-managed OAuth applications and providers an unambiguous namespace derived from the server model UUID and Juju relation ID.
- Migrate active legacy resources only when ownership is proven by the peer cache or an exact active-relation lookup; remove broad deletion based on a numeric suffix.
- Make provider/application creation, update, and deletion resumable across partial failures and ambiguous HTTP responses.
- Record a configuration hash only after every required mutation succeeds, and retain deletion tracking until every object is absent.
- Replace sentinel API return values with typed errors and bounded retries for connection failures, HTTP 429, and retryable 5xx responses.
- Match OIDC property mappings by their explicit scope field and remove the fallback that grants every mapping.
- Extend focused unit tests in `tests/unit/test_oauth.py` and API-client tests for ownership, retry, migration, and partial-failure behavior.

## Capabilities

### New Capabilities
- `authentik-api-resilience`: Typed Authentik API failures, bounded retries, and idempotent handling of ambiguous mutations.

### Modified Capabilities
- `oauth-relation`: Ownership-safe, resumable OAuth resource reconciliation and exact OIDC scope mapping.

## Non-goals

- Replacing the bootstrap API credential; that is handled by a separate cross-repository change.
- Changing internal HTTP transport or `AUTHENTIK_INSECURE` behavior.
- Recovering or deleting legacy orphan applications whose ownership cannot be proven.
- Persisting transient Juju unit status for API failures.

## Impact

- `src/authentik_api.py`: typed HTTP client behavior, exact scope lookup, and deterministic resource queries.
- `src/oauth.py`: ownership migration and resumable reconciliation.
- `src/charm.py`: startup-aware error propagation.
- `src/constants.py`: managed-resource namespace/cache schema constants.
- `tests/unit/`: observable reconciliation and error contracts.
