# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""OAuth2 relation reconciler for the Authentik server charm."""

import hashlib
import logging

import ops
from charms.hydra.v0.oauth import OAUTH_PROVIDER_JSON_SCHEMA, _dump_data

from authentik_api import AuthentikAPI
from constants import (
    AUTHORIZATION_FLOW_CACHE_PEER_KEY,
    INVALIDATION_FLOW_CACHE_PEER_KEY,
    OAUTH_CACHE_SCHEMA_VERSION,
    OAUTH_MANAGED_NAMESPACE,
    OAUTH_MODEL_UUID_HASH_LENGTH,
    OAUTH_RELATION_NAME,
    OAUTH_SYNC_CACHE_PEER_KEY,
)
from exceptions import AuthentikConflictError, AuthentikTransientError
from integrations import PeerData

logger = logging.getLogger(__name__)


class OauthReconciler:
    """Reconcile Juju OAuth relations with owned Authentik resources."""

    def __init__(self, charm, api: AuthentikAPI) -> None:
        """Initialize the reconciler.

        Args:
            charm: The calling Authentik server charm instance.
            api: The Authentik API client.
        """
        self._charm = charm
        self._api = api
        self._peer_data = PeerData(charm.model)
        self._property_mappings_cache: dict[str, list[str]] = {}
        model_uuid = str(charm.model.uuid)
        self._model_identity = hashlib.sha256(model_uuid.encode("utf-8")).hexdigest()[
            :OAUTH_MODEL_UUID_HASH_LENGTH
        ]

    def reconcile(self, active_relation_ids: set[int]) -> None:
        """Synchronize active relations and remove only cache-proven orphans."""
        if not self._charm.unit.is_leader():
            logger.debug("Skipping OAuth reconciliation, unit is not the leader")
            return

        if not active_relation_ids:
            self.garbage_collect(active_relation_ids)
            return

        authorization_flow = self._peer_data.get_string(AUTHORIZATION_FLOW_CACHE_PEER_KEY)
        if not authorization_flow:
            authorization_flow = self._api.get_authorization_flow_uuid()
            self._peer_data.set_string(AUTHORIZATION_FLOW_CACHE_PEER_KEY, authorization_flow)

        invalidation_flow = self._peer_data.get_string(INVALIDATION_FLOW_CACHE_PEER_KEY)
        if not invalidation_flow:
            invalidation_flow = self._api.get_invalidation_flow_uuid()
            self._peer_data.set_string(INVALIDATION_FLOW_CACHE_PEER_KEY, invalidation_flow)

        for relation_id in sorted(active_relation_ids):
            relation = self._charm.model.get_relation(OAUTH_RELATION_NAME, relation_id)
            if relation:
                self._sync_relation(relation, authorization_flow, invalidation_flow)

        self.garbage_collect(active_relation_ids)

    def _managed_identifier(self, relation_id: int) -> str:
        return f"{OAUTH_MANAGED_NAMESPACE}-{self._model_identity}-oauth-{relation_id}"

    def _legacy_slug(self, relation: "ops.Relation") -> str:
        return f"{self._charm._clean_slug(relation.app.name)}-{relation.id}"

    def _provider_name(self, relation: "ops.Relation") -> str:
        return f"{self._managed_identifier(relation.id)} ({relation.app.name})"

    def _save_cache(self, cache: dict) -> None:
        self._peer_data[OAUTH_SYNC_CACHE_PEER_KEY] = cache

    def _publish_provider_info(
        self, relation: "ops.Relation", slug: str, scopes: list[str]
    ) -> None:
        host = self._charm._authentik_host.rstrip("/")
        relation.data[self._charm.app].update(
            _dump_data(
                {
                    "issuer_url": f"{host}/application/o/{slug}/",
                    "authorization_endpoint": f"{host}/application/o/authorize/",
                    "token_endpoint": f"{host}/application/o/token/",
                    "introspection_endpoint": f"{host}/application/o/introspect/",
                    "userinfo_endpoint": f"{host}/application/o/userinfo/",
                    "jwks_endpoint": f"{host}/application/o/{slug}/jwks/",
                    "scope": " ".join(scopes),
                },
                OAUTH_PROVIDER_JSON_SCHEMA,
            )
        )

    def _sync_relation(
        self,
        relation: "ops.Relation",
        authorization_flow: str,
        invalidation_flow: str,
    ) -> None:
        if not relation.app:
            logger.info("Remote application is not ready for relation %s", relation.id)
            return

        scopes = sorted({
            scope.strip().lower()
            for scope in (
                relation.data[relation.app].get("scope") or "openid email profile"
            ).split()
            if scope.strip()
        })
        cache = self._peer_data[OAUTH_SYNC_CACHE_PEER_KEY]
        cached_entry = cache.get(str(relation.id))
        slug = (
            cached_entry.get("slug")
            if cached_entry and cached_entry.get("slug")
            else self._managed_identifier(relation.id)
        )
        self._publish_provider_info(relation, slug, scopes)

        redirect_uri = relation.data[relation.app].get("redirect_uri")
        if not redirect_uri:
            logger.info("Relation %s has no redirect_uri yet, waiting", relation.id)
            return

        scope_key = ",".join(scopes)
        config = f"{redirect_uri}:{authorization_flow}:{invalidation_flow}:{scope_key}"
        config_hash = hashlib.sha256(config.encode("utf-8")).hexdigest()
        if (
            cached_entry
            and cached_entry.get("schema_version") == OAUTH_CACHE_SCHEMA_VERSION
            and cached_entry.get("config_hash") == config_hash
            and cached_entry.get("provider_pk") is not None
            and cached_entry.get("slug")
        ):
            logger.info("Relation %s is already synchronized", relation.id)
            return

        client_id, client_secret, is_new = self._charm._get_or_generate_credentials(relation)
        property_mappings = self._property_mappings_cache.get(scope_key)
        if property_mappings is None:
            property_mappings = self._api.get_property_mappings(scopes)
            self._property_mappings_cache[scope_key] = property_mappings

        actual_slug, provider_pk = self._sync_authentik_objects(
            relation,
            cache,
            client_id,
            client_secret,
            redirect_uri,
            authorization_flow,
            invalidation_flow,
            property_mappings,
        )
        self._publish_provider_info(relation, actual_slug, scopes)

        if is_new:
            self._charm.oauth_provider.set_client_credentials_in_relation_data(
                relation.id, client_id, client_secret
            )

        cache[str(relation.id)] = {
            "schema_version": OAUTH_CACHE_SCHEMA_VERSION,
            "config_hash": config_hash,
            "provider_pk": provider_pk,
            "slug": actual_slug,
        }
        self._save_cache(cache)

    def _persist_partial_state(
        self, cache: dict, relation_id: int, slug: str, provider_pk: int
    ) -> None:
        cache[str(relation_id)] = {
            "schema_version": OAUTH_CACHE_SCHEMA_VERSION,
            "provider_pk": provider_pk,
            "slug": slug,
        }
        self._save_cache(cache)

    def _validate_application_provider(
        self, slug: str, application: dict, expected_names: set[str]
    ) -> int:
        provider_pk = application.get("provider")
        provider = (
            self._api.get_oauth_provider(int(provider_pk)) if provider_pk is not None else None
        )
        if provider is None or provider.get("name") not in expected_names:
            raise AuthentikConflictError(
                f"Application {slug!r} does not reference its expected OAuth provider"
            )
        return int(provider_pk)

    def _sync_authentik_objects(
        self,
        relation: "ops.Relation",
        cache: dict,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        authorization_flow: str,
        invalidation_flow: str,
        property_mappings: list[str],
    ) -> tuple[str, int]:
        """Discover, persist, and synchronize a relation's owned resources."""
        relation_key = str(relation.id)
        entry = cache.get(relation_key) or {}
        provider_name = self._provider_name(relation)
        managed_slug = self._managed_identifier(relation.id)
        slug = entry.get("slug") or managed_slug
        provider_pk = entry.get("provider_pk")
        application = None

        if provider_pk is not None and entry.get("slug"):
            provider_pk = int(provider_pk)
            application = self._api.get_application(slug)
            if application is not None and int(application.get("provider", -1)) != provider_pk:
                raise AuthentikConflictError(
                    f"Cached application {slug!r} references a different provider"
                )
        else:
            application = self._api.get_application(managed_slug)
            if application is not None:
                slug = managed_slug
                provider_pk = self._validate_application_provider(
                    slug, application, {provider_name}
                )
            else:
                legacy_slug = self._legacy_slug(relation)
                legacy_application = self._api.get_application(legacy_slug)
                if legacy_application is not None:
                    slug = legacy_slug
                    application = legacy_application
                    provider_pk = self._validate_application_provider(
                        slug,
                        application,
                        {provider_name, f"{relation.app.name} (Relation {relation.id})"},
                    )
                else:
                    provider = self._api.find_oauth_provider(provider_name)
                    if provider is not None:
                        provider_pk = int(provider["pk"])
                    else:
                        provider_pk = self._api.create_oauth_provider(
                            name=provider_name,
                            client_id=client_id,
                            client_secret=client_secret,
                            redirect_uris=redirect_uri,
                            authorization_flow=authorization_flow,
                            invalidation_flow=invalidation_flow,
                            property_mappings=property_mappings,
                        )
            self._persist_partial_state(cache, relation.id, slug, int(provider_pk))

        self._api.update_oauth_provider(
            provider_pk=int(provider_pk),
            name=provider_name,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uris=redirect_uri,
            authorization_flow=authorization_flow,
            invalidation_flow=invalidation_flow,
            property_mappings=property_mappings,
        )
        if application is None:
            self._api.create_application(
                name=provider_name, slug=slug, provider_pk=int(provider_pk)
            )
        else:
            self._api.update_application(
                slug=slug, name=provider_name, provider_pk=int(provider_pk)
            )
        return slug, int(provider_pk)

    def garbage_collect(self, active_relation_ids: set[int]) -> None:
        """Delete only orphan resources whose ownership is recorded in peer state."""
        cache = self._peer_data[OAUTH_SYNC_CACHE_PEER_KEY]
        for relation_key in list(cache):
            try:
                relation_id = int(relation_key)
            except ValueError:
                logger.warning("Retaining malformed OAuth cache entry %s", relation_key)
                continue
            if relation_id in active_relation_ids:
                continue

            entry = cache[relation_key]
            slug = entry.get("slug")
            if slug:
                if not self._api.delete_application(slug):
                    raise AuthentikTransientError(
                        f"Deletion of application {slug!r} was not confirmed"
                    )
                entry.pop("slug", None)
                entry.pop("config_hash", None)
                self._save_cache(cache)

            provider_pk = entry.get("provider_pk")
            if provider_pk is not None:
                if not self._api.delete_oauth_provider(int(provider_pk)):
                    raise AuthentikTransientError(
                        f"Deletion of provider {provider_pk!r} was not confirmed"
                    )
                entry.pop("provider_pk", None)
                self._save_cache(cache)

            cache.pop(relation_key)
            self._save_cache(cache)
