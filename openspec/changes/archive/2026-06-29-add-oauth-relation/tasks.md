## 1. Setup and Metadata

- [x] 1.1 Expose the `oauth` interface in `charmcraft.yaml` under `provides` sections.

## 2. Constants and Library Integration

- [x] 2.1 Add the `oauth` relation name constant to `src/constants.py`.
- [x] 2.2 Verify and import `OAuthProvider` and related classes in `src/charm.py`.

## 3. Charm Event Handling and Reconciliation

- [x] 3.1 Register observers for `oauth_provider.on.client_created` and `oauth_provider.on.client_changed` in `src/charm.py` initialization.
- [x] 3.2 Implement `_on_oauth_client_created` and `_on_oauth_client_changed` event handlers in `src/charm.py`.
- [x] 3.3 Implement `_update_oauth_provider_info` to write OIDC endpoints to the relation data in `src/charm.py`.
- [x] 3.4 Implement `_ensure_oauth_relation` and register it in the centralized `_holistic_handler` reconciliation pipeline in `src/charm.py`.

## 4. Testing and Formatting

- [x] 4.1 Create a new unit test suite in `tests/unit/test_oauth.py` to verify the `oauth` relation lifecycle, credential generation, and holistic endpoint updates.
- [x] 4.2 Run formatting and linting via `tox -e fmt` and `tox -e lint` to ensure code quality and standard compliance.
