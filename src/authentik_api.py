# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Authentik REST API Client."""

import logging

import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


class AuthentikAPI:
    """Client for interacting with the Authentik REST API."""

    def __init__(self, token: str, base_url: str = "http://localhost:9000") -> None:
        """Initialize the Authentik API Client.

        Args:
            token: The bearer token for authorization.
            base_url: The base URL of the Authentik API service.
        """
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def is_service_available(self) -> bool:
        """Check if the Authentik API service is available and reachable.

        Returns:
            True if the service is available, False otherwise.
        """
        try:
            url = f"{self.base_url}/api/v3/flows/flows/"
            response = requests.get(url, headers=self.headers, timeout=5)
            return response.status_code == 200
        except RequestException:
            return False

    def get_authorization_flow_uuid(self) -> str | None:
        """Retrieve the explicit consent authorization flow UUID.

        Returns:
            The flow UUID string if found, otherwise None.
        """
        try:
            url = (
                f"{self.base_url}/api/v3/flows/flows/?"
                "slug=default-provider-authorization-explicit-consent"
            )
            response = requests.get(url, headers=self.headers, timeout=5)
            response.raise_for_status()
            results = response.json().get("results", [])
            if results:
                return results[0]["pk"]

            # Fallback to listing flows to find any authorization or consent flow
            url = f"{self.base_url}/api/v3/flows/flows/?ordering=slug"
            response = requests.get(url, headers=self.headers, timeout=5)
            response.raise_for_status()
            results = response.json().get("results", [])
            for flow in results:
                slug = flow.get("slug", "")
                if "consent" in slug or "authorization" in slug:
                    return flow["pk"]

            if results:
                return results[0]["pk"]
        except Exception as e:
            logger.error("Failed to retrieve authorization flow: %s", e)
        return None

    def get_property_mappings(self, scopes: list[str]) -> list[str]:
        """Retrieve UUIDs of standard OIDC scope property mappings matching requested scopes.

        Args:
            scopes: List of requested scopes (e.g. ['openid', 'email']).

        Returns:
            List of matching property mapping UUID strings.
        """
        mappings = []
        try:
            url = f"{self.base_url}/api/v3/propertymappings/oauth2/"
            response = requests.get(url, headers=self.headers, timeout=5)
            response.raise_for_status()
            results = response.json().get("results", [])

            requested_scopes = [s.lower() for s in scopes]
            for mapping in results:
                name = mapping.get("name", "").lower()
                managed = mapping.get("managed", "") or ""
                managed = managed.lower()

                matched = False
                for scope in requested_scopes:
                    if (
                        f"scope-{scope}" in managed
                        or f"scope {scope}" in name
                        or f"scope_{scope}" in name
                        or scope == name
                    ):
                        matched = True
                        break

                if matched or not scopes:
                    mappings.append(mapping["pk"])

            # Fallback to all mappings if none specifically matched
            if not mappings and results:
                mappings = [m["pk"] for m in results]
        except Exception as e:
            logger.error("Failed to retrieve property mappings: %s", e)
        return mappings

    def get_application(self, slug: str) -> dict | None:
        """Get an application by slug.

        Args:
            slug: The application slug.

        Returns:
            The application details dictionary if found, otherwise None.
        """
        try:
            url = f"{self.base_url}/api/v3/core/applications/{slug}/"
            response = requests.get(url, headers=self.headers, timeout=5)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to get application %s: %s", slug, e)
        return None

    def list_applications(self) -> list[dict]:
        """List all applications.

        Returns:
            List of application details dictionaries.
        """
        try:
            url = f"{self.base_url}/api/v3/core/applications/?page_size=100"
            response = requests.get(url, headers=self.headers, timeout=5)
            response.raise_for_status()
            return response.json().get("results", [])
        except Exception as e:
            logger.error("Failed to list applications: %s", e)
        return []

    def create_oauth_provider(
        self,
        name: str,
        client_id: str,
        client_secret: str,
        redirect_uris: str,
        authorization_flow: str,
        property_mappings: list[str],
    ) -> int | None:
        """Create an OAuth2 provider.

        Args:
            name: The provider name.
            client_id: The OIDC client ID.
            client_secret: The OIDC client secret.
            redirect_uris: Newline separated redirect URIs.
            authorization_flow: The flow UUID.
            property_mappings: List of scope property mapping UUIDs.

        Returns:
            The PK ID of the created provider if successful, otherwise None.
        """
        try:
            url = f"{self.base_url}/api/v3/providers/oauth2/"
            payload = {
                "name": name,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uris": redirect_uris,
                "authorization_flow": authorization_flow,
                "property_mappings": property_mappings,
            }
            response = requests.post(url, json=payload, headers=self.headers, timeout=5)
            response.raise_for_status()
            return response.json().get("pk")
        except Exception as e:
            logger.error("Failed to create OAuth provider %s: %s", name, e)
        return None

    def update_oauth_provider(
        self,
        provider_pk: int,
        name: str,
        client_id: str,
        client_secret: str,
        redirect_uris: str,
        authorization_flow: str,
        property_mappings: list[str],
    ) -> bool:
        """Update an existing OAuth2 provider.

        Args:
            provider_pk: The provider primary key ID.
            name: The provider name.
            client_id: The OIDC client ID.
            client_secret: The OIDC client secret.
            redirect_uris: Newline separated redirect URIs.
            authorization_flow: The flow UUID.
            property_mappings: List of scope property mapping UUIDs.

        Returns:
            True if successful, False otherwise.
        """
        try:
            url = f"{self.base_url}/api/v3/providers/oauth2/{provider_pk}/"
            payload = {
                "name": name,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uris": redirect_uris,
                "authorization_flow": authorization_flow,
                "property_mappings": property_mappings,
            }
            response = requests.put(url, json=payload, headers=self.headers, timeout=5)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error("Failed to update OAuth provider %s: %s", provider_pk, e)
        return False

    def create_application(self, name: str, slug: str, provider_pk: int) -> bool:
        """Create an application linked to a provider.

        Args:
            name: The application name.
            slug: The application slug.
            provider_pk: The linked provider PK ID.

        Returns:
            True if successful, False otherwise.
        """
        try:
            url = f"{self.base_url}/api/v3/core/applications/"
            payload = {
                "name": name,
                "slug": slug,
                "provider": provider_pk,
            }
            response = requests.post(url, json=payload, headers=self.headers, timeout=5)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error("Failed to create application %s: %s", name, e)
        return False

    def update_application(self, slug: str, name: str, provider_pk: int) -> bool:
        """Update an existing application.

        Args:
            slug: The application slug.
            name: The application name.
            provider_pk: The linked provider PK ID.

        Returns:
            True if successful, False otherwise.
        """
        try:
            url = f"{self.base_url}/api/v3/core/applications/{slug}/"
            payload = {
                "name": name,
                "provider": provider_pk,
            }
            response = requests.put(url, json=payload, headers=self.headers, timeout=5)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error("Failed to update application %s: %s", slug, e)
        return False

    def delete_application(self, slug: str) -> bool:
        """Delete an application by slug.

        Args:
            slug: The application slug.

        Returns:
            True if successful or if application did not exist, False otherwise.
        """
        try:
            url = f"{self.base_url}/api/v3/core/applications/{slug}/"
            response = requests.delete(url, headers=self.headers, timeout=5)
            if response.status_code == 404:
                return True
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error("Failed to delete application %s: %s", slug, e)
        return False

    def delete_oauth_provider(self, provider_pk: int) -> bool:
        """Delete an OAuth2 provider.

        Args:
            provider_pk: The provider primary key ID.

        Returns:
            True if successful or if provider did not exist, False otherwise.
        """
        try:
            url = f"{self.base_url}/api/v3/providers/oauth2/{provider_pk}/"
            response = requests.delete(url, headers=self.headers, timeout=5)
            if response.status_code == 404:
                return True
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error("Failed to delete OAuth provider %s: %s", provider_pk, e)
        return False
