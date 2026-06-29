## Why

The Authentik Server Operator currently lacks an `oauth` provider relation. Adding this relation enables other charms (such as the `identity-platform-admin-ui-operator`) to automatically integrate and register OIDC/OAuth2 client applications with the Authentik Server.

## What Changes

- Introduce the `oauth` provider relation to the Authentik Server charm.
- Integrate the `charms.hydra.v0.oauth.OAuthProvider` library on the provider side.
- Automatically generate client credentials (`client_id`, `client_secret`) and store them securely using Juju secrets.
- Expose the necessary OIDC endpoints (`issuer_url`, `authorization_endpoint`, `token_endpoint`, etc.) over the relation.

## Capabilities

### New Capabilities
- `oauth-relation`: Exposes the `oauth` Juju integration interface on the Authentik Server charm to provide OIDC/OAuth2 authentication endpoints and register client applications.

### Modified Capabilities
None.

## Non-goals

- Implementing direct REST API calls from the charm operator to Authentik to dynamically create/delete applications (the operator exposes standard, stable OIDC endpoints based on the external host).
- Managing token customization or custom OAuth2 scopes beyond standard defaults.

## Impact

- **Affected modules**:
  - `charmcraft.yaml`: Define `oauth` under `provides`.
  - `src/constants.py`: Add `OAUTH_RELATION_NAME` constant.
  - `src/charm.py`: Add `OAuthProvider` instance, register observers, and extend `_holistic_handler` / `_ensure_oauth_relation`.
- **Dependencies**: Add `jsonschema` library dependency if not already fully configured.
