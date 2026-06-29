## Context

The Authentik Server Operator Juju charm needs to handle integration requests via the `oauth` relation. The current implementation does not actually call the Authentik REST API to provision/modify/delete the OIDC providers and client applications, nor does it clean them up on relation removal. Furthermore, custom Juju events (like `client_created`) are unreliable because their event queue state is stored in the pod container's local `emptyDir` SQLite database, which is completely lost if the container/pod is killed or restarted.

## Goals / Non-Goals

**Goals:**
- Eliminate reliance on custom Juju events by migrating to active, state-based reconciliation within the holistic `_ensure_oauth_relation` handler.
- Integrate with the Authentik REST API (`/api/v3`) using `requests` to create, update, and delete OIDC Providers and Applications.
- Support multi-tenancy by using unique, sanitized slugs `{remote_app_name}-{relation_id}` for Authentik applications and providers.
- Implement robust deletion/cleanup of Authentik providers and applications when an `oauth` relation is removed.
- Handle API connectivity errors gracefully to prevent Pebble planning deadlocks.

**Non-Goals:**
- Supporting general-purpose non-OIDC provider configurations.
- Changing Juju's underlying event or library storage mechanisms.

## Decisions

### 1. Active State-Based Reconciliation vs. Custom Juju Events
- **Decision**: Remove observers for custom events like `oauth_provider.on.client_created` and `oauth_provider.on.client_changed`. Instead, standard Juju events (`relation_created`, `relation_changed`, `relation_broken`) trigger the holistic handler `_on_holistic_handler`, which delegates to `_ensure_oauth_relation`.
- **Rationale**: State-based reconciliation is robust against pod restarts and transient failures, whereas custom Juju events can be permanently lost if a pod restarts during their queuing.

### 2. Formatted Slug for Multi-Tenancy
- **Decision**: Define and use application slugs formatted as `{clean_remote_app_name}-{relation_id}`.
- **Rationale**: This guarantees uniqueness across relations (even with the same remote charm name) and allows active tracking and cleanup of Juju-managed clients.

### 3. Graceful API Failures
- **Decision**: Wrap all Authentik REST API calls in try-except blocks and check connectivity first. If the API is unreachable (e.g. during early boot), log a debug/info message and return `True` gracefully without raising a `CharmError` or blocking other services.
- **Rationale**: Prevents a circular dependency/deadlock where Pebble cannot plan/start Authentik because the API is not yet running, but the API cannot start because Pebble planning is blocked.

## Risks / Trade-offs

- **[Risk]**: Authentik API is temporarily down or slow.
  - **Mitigation**: Standard HTTP timeouts (5 seconds) and graceful handling of ConnectionError / Timeout, allowing subsequent reconciliation runs to retry seamlessly.
