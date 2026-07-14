## 1. Declarations and Configuration

- [x] 1.1 Declare the `traefik-route` relation interface inside `charmcraft.yaml`
- [x] 1.2 Add port and relation name constants inside `src/constants.py`
- [x] 1.3 Create the Traefik route configuration template `templates/traefik-route.json.j2`

## 2. Ingress Integrations

- [x] 2.1 Implement the Traefik Route integration helper and data structures inside `src/integrations.py`
- [x] 2.2 Register and handle `traefik-route` relation events within `src/charm.py` and forward configurations during `_reconcile()`
- [x] 2.3 Update base URL configurations dynamically in `src/charm.py` and propagate them to `authentik-server-info`

## 3. Verification and Testing

- [x] 3.1 Implement unit tests inside `tests/unit/test_charm.py` verifying that `traefik-route` relation changes propagate to the Traefik databag, Pebble environment variables, and `authentik-server-info` relations
- [x] 3.2 Implement integration tests inside `tests/integration/test_charm.py` validating end-to-end routing with the `traefik-k8s` charm
