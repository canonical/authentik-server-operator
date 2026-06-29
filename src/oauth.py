# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""OAuth2 relation reconciler for the Authentik server charm."""

import hashlib
import logging
import re

import ops
from charms.hydra.v0.oauth import OAUTH_PROVIDER_JSON_SCHEMA, _dump_data

from authentik_api import AuthentikAPI
from constants import (
    AUTHORIZATION_FLOW_CACHE_PEER_KEY,
    OAUTH_RELATION_NAME,
    OAUTH_SYNC_CACHE_PEER_KEY,
)
from integrations import PeerData

logger = logging.getLogger(__name__)


class OauthReconciler:
    """Orchestrates and reconciles Juju OAuth relations with the Authentik API.

    Design & Storage Tradeoffs:
        The status and credentials of all synced OAuth relations are cached under a single
        key (`OAUTH_SYNC_CACHE_PEER_KEY`) in the peer relation's application databag.
        Grouping all relation entries into a single dictionary is efficient for typical
        deployments (< 50 active relations), avoiding peer databag clutter.

        Limits & Tradeoffs to keep in mind:
        - **Juju Databag Size (64KB boundary):** Serialization/deserialization size limit
          is historically 64KB per databag value. Each entry is ~120 bytes, meaning we
          can safely handle up to ~500 relations under this single key.
        - **Serialization Cost:** Modifying any single entry requires serializing/deserializing
          the entire cached dictionary.
        - **Race Conditions:** Safe from cross-unit race conditions because only the leader
          unit updates this databag, and Juju serializes hook runs on a single unit.

        If a deployment is expected to scale to hundreds of concurrent OAuth integrations,
        this single-key design should be refactored to use individual relation-indexed
        keys (e.g., `oauth_sync_cache_{relation_id}`).
    """

    def __init__(self, charm, api: AuthentikAPI) -> None:
        """Initialize the reconciler.

        Args:
            charm: The calling Authentik server charm instance.
            api: The AuthentikAPI client instance.
        """
        self._charm = charm
        self._api = api
        self._peer_data = PeerData(charm.model)
        self._property_mappings_cache: dict[str, list[str]] = {}

    def reconcile(self, active_relation_ids: set[int]) -> None:
        """Reconcile active OAuth relations and garbage collect orphan objects.

        Args:
            active_relation_ids: Set of active OAuth relation IDs.
        """
        if not self._charm.unit.is_leader():
            logger.debug("Skipping OAuth reconciliation, unit is not the leader")
            return

        # Retrieve authorization flow dynamically
        authorization_flow = self._peer_data.get_string(AUTHORIZATION_FLOW_CACHE_PEER_KEY)
        if not authorization_flow:
            authorization_flow = self._api.get_authorization_flow_uuid()
            if authorization_flow:
                self._peer_data.set_string(AUTHORIZATION_FLOW_CACHE_PEER_KEY, authorization_flow)
            else:
                logger.error("Failed to retrieve explicit consent authorization flow UUID")
                return

        # Sync active relations
        for relation_id in active_relation_ids:
            relation = self._charm.model.get_relation(OAUTH_RELATION_NAME, relation_id)
            if relation:
                self._sync_relation(relation, authorization_flow)

        # Garbage collect / delete orphans (Authentik providers/applications whose Juju relations are gone)
        self.garbage_collect(active_relation_ids)

    def _sync_relation(
        self,
        relation: "ops.Relation",
        authorization_flow: str,
    ) -> None:
        """Sync a single Juju oauth relation with the Authentik REST API.

        Args:
            relation: The Juju relation object.
            authorization_flow: The consent flow UUID.
        """
        if not relation.app:
            logger.info("Remote application is not ready for relation %s", relation.id)
            return

        # Extract dynamic scopes from relation data, falling back to "openid email profile phone"
        scope_str = relation.data[relation.app].get("scope") or "openid email profile phone"
        scopes = sorted({s.strip().lower() for s in scope_str.split() if s.strip()})

        # Determine OIDC client slug and populate standard provider endpoints immediately
        clean_app_name = self._charm._clean_slug(relation.app.name)
        slug = f"{clean_app_name}-{relation.id}"

        host = self._charm._authentik_host.rstrip("/")
        provider_info = {
            "issuer_url": f"{host}/application/o/{slug}/",
            "authorization_endpoint": f"{host}/application/o/authorize/",
            "token_endpoint": f"{host}/application/o/token/",
            "introspection_endpoint": f"{host}/application/o/introspect/",
            "userinfo_endpoint": f"{host}/application/o/userinfo/",
            "jwks_endpoint": f"{host}/application/o/{slug}/jwks/",
            "scope": " ".join(scopes),
        }
        relation.data[self._charm.app].update(
            _dump_data(provider_info, OAUTH_PROVIDER_JSON_SCHEMA)
        )

        requirer_data = relation.data[relation.app]
        redirect_uri = requirer_data.get("redirect_uri")
        if not redirect_uri:
            logger.info("Relation %s has no redirect_uri yet, waiting...", relation.id)
            return

        scope_key = ",".join(scopes)

        # Hash configurations to minimize cache bloat and avoid storing plaintext credentials in the peer databag.
        # We only hash the primary dynamic inputs (redirect_uri, authorization_flow, scope_key).
        # Since client credentials are immutable once generated for a relation, they do not need to be hashed.
        # This allows us to bypass Juju secret lookups entirely on the happy path.
        config_str = f"{redirect_uri}:{authorization_flow}:{scope_key}"
        config_hash = hashlib.sha256(config_str.encode("utf-8")).hexdigest()

        # Check if the cache already indicates this relation is synced
        oauth_sync_cache = self._peer_data[OAUTH_SYNC_CACHE_PEER_KEY]
        cached_entry = oauth_sync_cache.get(str(relation.id))

        if (
            cached_entry
            and cached_entry.get("config_hash") == config_hash
            and cached_entry.get("provider_pk") is not None
            and cached_entry.get("slug") == slug
        ):
            logger.info("Relation %s is already in sync with Authentik (cached)", relation.id)
            return

        # Cache mismatch or missing. Retrieve or generate credentials and fetch property mappings on-demand.
        client_id, client_secret = self._charm._get_or_generate_credentials(relation)

        property_mappings = self._property_mappings_cache.get(scope_key)
        if property_mappings is None:
            property_mappings = self._api.get_property_mappings(scopes)
            self._property_mappings_cache[scope_key] = property_mappings

        # Sync with Authentik API.
        actual_slug, provider_pk = self._sync_authentik_objects(
            relation=relation,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            authorization_flow=authorization_flow,
            property_mappings=property_mappings,
        )
        if not actual_slug or provider_pk is None:
            return

        # Update the sync cache
        oauth_sync_cache[str(relation.id)] = {
            "config_hash": config_hash,
            "provider_pk": provider_pk,
            "slug": actual_slug,
        }
        self._peer_data[OAUTH_SYNC_CACHE_PEER_KEY] = oauth_sync_cache

    def _sync_authentik_objects(
        self,
        relation: "ops.Relation",
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        authorization_flow: str,
        property_mappings: list[str],
    ) -> tuple[str | None, int | None]:
        """Create or update provider and application in Authentik.

        Args:
            relation: The Juju relation.
            client_id: The OIDC client ID.
            client_secret: The OIDC client secret.
            redirect_uri: The redirect URI.
            authorization_flow: Flow UUID.
            property_mappings: Property mappings list.

        Returns:
            A tuple of (application slug, provider primary key) if successful, otherwise (None, None).
        """
        clean_app_name = self._charm._clean_slug(relation.app.name)
        slug = f"{clean_app_name}-{relation.id}"
        name = f"{relation.app.name} (Relation {relation.id})"

        app_data = self._api.get_application(slug)
        if not app_data:
            provider_pk = self._api.create_oauth_provider(
                name=name,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uris=redirect_uri,
                authorization_flow=authorization_flow,
                property_mappings=property_mappings,
            )
            if provider_pk is None:
                logger.error("Failed to create OAuth provider %s", name)
                return None, None

            if not self._api.create_application(name=name, slug=slug, provider_pk=provider_pk):
                logger.error("Failed to create application %s with provider %s", name, provider_pk)
                return None, None

            logger.info("Successfully created application %s and OAuth provider", name)
        else:
            provider_pk = app_data.get("provider")
            if provider_pk:
                self._api.update_oauth_provider(
                    provider_pk=provider_pk,
                    name=name,
                    client_id=client_id,
                    client_secret=client_secret,
                    redirect_uris=redirect_uri,
                    authorization_flow=authorization_flow,
                    property_mappings=property_mappings,
                )
            self._api.update_application(slug=slug, name=name, provider_pk=provider_pk)
            logger.info("Successfully updated application %s and OAuth provider", name)

        return slug, provider_pk

    def garbage_collect(self, active_relation_ids: set[int]) -> None:
        """Garbage-collect orphan Authentik applications and providers.

        Args:
            active_relation_ids: Set of active relation IDs to keep.
        """
        oauth_sync_cache = self._peer_data[OAUTH_SYNC_CACHE_PEER_KEY]

        # If cache is empty, we perform a one-time migration/sync by listing applications from Authentik API.
        if not oauth_sync_cache:
            self._gc_uncached_orphans(active_relation_ids, oauth_sync_cache)
        else:
            self._gc_cached_orphans(active_relation_ids, oauth_sync_cache)

    def _gc_uncached_orphans(self, active_relation_ids: set[int], oauth_sync_cache: dict) -> None:
        """Perform one-time list-based garbage collection when sync cache is empty.

        Args:
            active_relation_ids: Set of active relation IDs to keep.
            oauth_sync_cache: The OIDC client credentials sync cache.
        """
        logger.info(
            "Sync cache is empty, listing applications to find and garbage collect orphans..."
        )
        try:
            all_apps = self._api.list_applications()
            for app in all_apps:
                app_slug = app.get("slug", "")
                match = re.match(r"^(.*)-(\d+)$", app_slug)
                if not match:
                    continue

                slug_relation_id = int(match.group(2))
                provider_pk = app.get("provider")
                if slug_relation_id not in active_relation_ids:
                    logger.info(
                        "Deleting uncached orphan Authentik application and provider for relation %s",
                        slug_relation_id,
                    )
                    if provider_pk:
                        try:
                            self._api.delete_oauth_provider(provider_pk)
                        except Exception as e:
                            logger.error("Failed to delete provider %s: %s", provider_pk, e)
                    try:
                        self._api.delete_application(app_slug)
                    except Exception as e:
                        logger.error("Failed to delete application %s: %s", app_slug, e)
                else:
                    oauth_sync_cache[str(slug_relation_id)] = {
                        "slug": app_slug,
                        "provider_pk": provider_pk,
                    }
        except Exception as e:
            logger.error("Failed to list and garbage collect uncached applications: %s", e)
            return

        if oauth_sync_cache:
            self._peer_data[OAUTH_SYNC_CACHE_PEER_KEY] = oauth_sync_cache

    def _gc_cached_orphans(self, active_relation_ids: set[int], oauth_sync_cache: dict) -> None:
        """Garbage-collect cached orphan applications using the sync cache.

        Args:
            active_relation_ids: Set of active relation IDs to keep.
            oauth_sync_cache: The OIDC client credentials sync cache.
        """
        cache_keys_to_delete = []
        for cached_rel_id_str, cached_entry in list(oauth_sync_cache.items()):
            cached_rel_id = int(cached_rel_id_str)
            if cached_rel_id in active_relation_ids:
                continue

            logger.info(
                "Deleting cached orphan Authentik application and provider for relation %s",
                cached_rel_id,
            )
            slug = cached_entry.get("slug")
            provider_pk = cached_entry.get("provider_pk")
            if provider_pk:
                try:
                    self._api.delete_oauth_provider(provider_pk)
                except Exception as e:
                    logger.error("Failed to delete provider %s: %s", provider_pk, e)
            if slug:
                try:
                    self._api.delete_application(slug)
                except Exception as e:
                    logger.error("Failed to delete application %s: %s", slug, e)
            cache_keys_to_delete.append(cached_rel_id_str)

        if cache_keys_to_delete:
            for k in cache_keys_to_delete:
                oauth_sync_cache.pop(k, None)
            self._peer_data[OAUTH_SYNC_CACHE_PEER_KEY] = oauth_sync_cache
