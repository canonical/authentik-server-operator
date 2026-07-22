## Context

The leader reconciles Juju `oauth` relations against external Authentik provider and application objects. Authentik mutations are not part of the Juju hook transaction: a successful POST, PATCH, or DELETE remains committed when a later request or hook fails. The current cache stores only completed state, broad cache-recovery scans infer ownership from any numeric slug suffix, and API methods collapse transport, authorization, validation, and not-found failures into sentinel values.

## Goals / Non-Goals

**Goals:**
- Prove ownership before mutating or deleting Authentik objects.
- Resume safely after every partial or ambiguous external mutation.
- Cache only fully synchronized configurations and retain failed cleanup work.
- Distinguish retryable API failures from permanent and authorization failures.
- Select only explicitly requested OIDC scope mappings.

**Non-Goals:**
- Replacing bootstrap credentials.
- Changing internal HTTP transport.
- Automatically deleting legacy resources with no surviving ownership evidence.
- Persisting transient unit status.

## Decisions

### Managed identity and legacy adoption

New application slugs use `juju-<model-uuid-hash>-oauth-<relation-id>`. Provider names use the same managed identifier plus a human-readable remote application name. The model UUID hash is stable across model renames and distinguishes separate deployments.

Existing peer-cache entries remain authoritative. When an active relation has no cache, reconciliation may adopt only the exact legacy slug derived from that active relation and only after validating its provider. Cache-empty recovery never deletes applications discovered by a regex. Unproven legacy orphans are left for explicit operator cleanup.

### Resumable reconciliation instead of compensating rollback

A cache entry may contain `provider_pk` and `slug` without `config_hash`; this represents incomplete work, not synchronized state. After provider creation, its PK is persisted before application creation. Reconciliation then discovers or creates the application and performs required updates. The configuration hash is written last.

If a create request has an ambiguous result, reconciliation queries by the deterministic managed identity before issuing another POST. No successful create is automatically deleted merely because a later step failed.

### Deletion is retained until absence is proven

Application and provider deletion are independently idempotent. A cache entry is removed only when both operations return success or not-found. Transient, authentication, authorization, and validation errors retain the entry for a later hook.

### Typed HTTP failures and bounded retry

The API client raises distinct not-found, authentication, authorization, conflict, transient, and request-validation errors. Connection failures, HTTP 429, and retryable 5xx responses use bounded exponential retry. HTTP 400, 401, 403, and ordinary 404 responses do not retry. POST is not blindly retried; ambiguous creates recover through deterministic lookup.

Before the Authentik service is ready, OAuth reconciliation is skipped so Pebble startup is not circular. Once the service is running, an exhausted API error propagates to fail the hook and remains visible without a separate persisted status field.

### Exact scope mapping

Scope mappings are indexed by the API's explicit scope field. Every requested scope is resolved exactly. Unsupported scopes produce a typed reconciliation failure; the client never substitutes all available mappings.

## Risks / Trade-offs

- **Legacy unowned resources remain:** Safety takes precedence over automatic cleanup. Operators may need a documented one-time cleanup.
- **Peer writes and API writes are still not atomic:** Deterministic lookup and partial cache entries make each boundary resumable.
- **Model UUID changes create a new namespace:** Model migration must preserve peer state or require explicit resource adoption.
- **Retry increases hook duration:** The retry budget remains deliberately short and excludes permanent failures.
