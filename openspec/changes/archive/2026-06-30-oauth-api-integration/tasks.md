## 1. Authentik API Client

- [x] 1.1 Create the Authentik API Client in [authentik_api.py](file:///home/nikos.sklikas@canonical.com/projects/authentik-charms/authentik-server-operator-oauth/src/authentik_api.py) to manage GET, POST, PUT, DELETE operations on providers and applications

## 2. Charm Refactoring & Active Reconciliation

- [x] 2.1 Refactor OAUTH_RELATION observers in [charm.py](file:///home/nikos.sklikas@canonical.com/projects/authentik-charms/authentik-server-operator-oauth/src/charm.py) to observe relation_created, relation_changed, and relation_broken, removing the custom client_created and client_changed observers
- [x] 2.2 Re-implement `_ensure_oauth_relation` and `_update_oauth_provider_info` in [charm.py](file:///home/nikos.sklikas@canonical.com/projects/authentik-charms/authentik-server-operator-oauth/src/charm.py) to perform active state-based reconciliation and client provisioning/updates via Authentik API
- [x] 2.3 Add client cleanup/deletion logic for broken/removed relations in [charm.py](file:///home/nikos.sklikas@canonical.com/projects/authentik-charms/authentik-server-operator-oauth/src/charm.py)

## 3. Testing and Verification

- [x] 3.1 Update unit tests in [test_oauth.py](file:///home/nikos.sklikas@canonical.com/projects/authentik-charms/authentik-server-operator-oauth/tests/unit/test_oauth.py) to mock Authentik REST API requests and assert correct creation, updates, and deletion behavior
- [x] 3.2 Run format and lint checks (`tox -e fmt && tox -e lint && tox -e unit`)
