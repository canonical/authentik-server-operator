# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Authentik REST API Client."""

import logging
import time
from functools import cached_property
from typing import Iterator
from urllib.parse import parse_qs, urlparse

import requests
import tenacity
from requests import Response
from requests.exceptions import ConnectionError, RequestException, Timeout

from exceptions import (
    AuthentikAPIError,
    AuthentikAuthenticationError,
    AuthentikAuthorizationError,
    AuthentikConflictError,
    AuthentikNotFoundError,
    AuthentikRequestValidationError,
    AuthentikTransientError,
)

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 5
REQUEST_MAX_ATTEMPTS = 3
REQUEST_RETRY_BACKOFF_SECONDS = 0.25
REQUEST_RETRY_BACKOFF_MAX_SECONDS = 2
RETRYABLE_SERVER_STATUSES = frozenset({500, 502, 503, 504})
PAGINATION_PAGE_SIZE = 100
PAGINATION_MAX_PAGES = 1000


class AuthentikAPI:
    """Client for interacting with the Authentik REST API."""

    def __init__(self, token: str, base_url: str = "http://localhost:9000") -> None:
        """Initialize the Authentik API Client.

        Args:
            token: The bearer token for authorization.
            base_url: The base URL of the Authentik API service.
        """
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        self._scope_property_mappings: list[dict] | None = None

    def _request(self, method: str, url: str, *, retry: bool = True, **kwargs) -> Response:
        """Execute an HTTP request with bounded retries and raise a typed API error.

        Retries only transient failures (connection/timeout, HTTP 429, and 5xx).
        Non-idempotent callers pass ``retry=False`` and recover ambiguous outcomes by
        querying the resource's deterministic identity.
        """
        kwargs.setdefault("timeout", REQUEST_TIMEOUT_SECONDS)
        attempts = REQUEST_MAX_ATTEMPTS if retry else 1
        for attempt in tenacity.Retrying(
            stop=tenacity.stop_after_attempt(attempts),
            wait=tenacity.wait_exponential(
                multiplier=REQUEST_RETRY_BACKOFF_SECONDS, max=REQUEST_RETRY_BACKOFF_MAX_SECONDS
            ),
            retry=tenacity.retry_if_exception_type(AuthentikTransientError),
            reraise=True,
            sleep=time.sleep,
        ):
            with attempt:
                return self._do_request(method, url, **kwargs)
        raise AssertionError("request retry loop completed without a response")

    def _do_request(self, method: str, url: str, **kwargs) -> Response:
        """Execute one HTTP request, raising a typed error for the outcome.

        Connection failures, timeouts, HTTP 429, and retryable 5xx responses raise the
        retryable ``AuthentikTransientError``; other failures raise their terminal type.
        """
        try:
            response = self.session.request(method, url, **kwargs)
        except (ConnectionError, Timeout) as error:
            raise AuthentikTransientError(f"{method} {url} failed: {error}") from error
        except RequestException as error:
            raise AuthentikRequestValidationError(
                f"{method} {url} could not be sent: {error}"
            ) from error

        if response.status_code == 429 or response.status_code in RETRYABLE_SERVER_STATUSES:
            raise AuthentikTransientError(f"{method} {url} returned HTTP {response.status_code}")
        self._raise_for_terminal_status(response, method, url)
        return response

    @staticmethod
    def _raise_for_terminal_status(response: Response, method: str, url: str) -> None:
        """Raise the typed error matching a non-retryable HTTP status, if any."""
        terminal = {
            401: AuthentikAuthenticationError,
            403: AuthentikAuthorizationError,
            404: AuthentikNotFoundError,
            409: AuthentikConflictError,
        }
        error_cls = terminal.get(response.status_code)
        if error_cls is not None:
            raise error_cls(f"{method} {url} returned HTTP {response.status_code}")
        if response.status_code >= 400:
            raise AuthentikRequestValidationError(
                f"{method} {url} returned HTTP {response.status_code}: {response.text}"
            )

    def _get_paginated(self, url: str, params: dict | None = None) -> Iterator[dict]:
        """Fetch all results from a paginated API endpoint.

        Requests a bounded ``page_size`` and stops after ``PAGINATION_MAX_PAGES`` to
        guard against an unbounded or self-referential pagination loop.
        """
        current_params = (params or {}).copy()
        current_params.setdefault("page", 1)
        current_params.setdefault("page_size", PAGINATION_PAGE_SIZE)

        for _ in range(PAGINATION_MAX_PAGES):
            data = self._request("GET", url, params=current_params).json()
            yield from data.get("results", [])

            pagination = data.get("pagination")
            if pagination:
                next_page = pagination.get("next")
                if next_page is not None and next_page > 0:
                    current_params["page"] = next_page
                    continue
                return

            next_url = data.get("next")
            if isinstance(next_url, str):
                page_value = parse_qs(urlparse(next_url).query).get("page")
                if page_value:
                    current_params["page"] = int(page_value[0])
                    continue
            return

        raise AuthentikAPIError(
            f"Pagination for {url} exceeded the maximum of {PAGINATION_MAX_PAGES} pages"
        )

    @cached_property
    def is_service_available(self) -> bool:
        """Whether the service can answer an authenticated API request.

        Used as a readiness probe: during Authentik first-boot the API can reject
        the bootstrap credentials with 401/403 (or 404/transient) before the token
        is registered, so any typed API error means "not ready yet", not a crash.

        Cached per instance so repeated readiness checks within a single hook
        (one client per hook) do not re-issue the request.
        """
        url = f"{self.base_url}/api/v3/flows/instances/"
        try:
            self._request("GET", url, params={"page_size": 1})
        except AuthentikAPIError:
            return False
        return True

    def _get_flow_uuid(self, slug: str) -> str:
        url = f"{self.base_url}/api/v3/flows/instances/"
        flows = list(self._get_paginated(url, params={"slug": slug}))
        if not flows:
            raise AuthentikNotFoundError(f"Authentik flow {slug!r} was not found")
        return flows[0]["pk"]

    def get_authorization_flow_uuid(self) -> str:
        """Retrieve the explicit-consent authorization flow UUID."""
        return self._get_flow_uuid("default-provider-authorization-explicit-consent")

    def get_invalidation_flow_uuid(self) -> str:
        """Retrieve the default provider invalidation flow UUID."""
        return self._get_flow_uuid("default-provider-invalidation-flow")

    def get_property_mappings(self, scopes: list[str]) -> list[str]:
        """Resolve every requested OIDC scope by its explicit scope name.

        Raises:
            AuthentikRequestValidationError: If a scope is unsupported or mappings are invalid.
        """
        if self._scope_property_mappings is None:
            url = f"{self.base_url}/api/v3/propertymappings/provider/scope/"
            self._scope_property_mappings = list(self._get_paginated(url))

        mappings_by_scope: dict[str, str] = {}
        for mapping in self._scope_property_mappings:
            scope_name = mapping.get("scope_name")
            pk = mapping.get("pk")
            if isinstance(scope_name, str) and isinstance(pk, str):
                mappings_by_scope[scope_name.lower()] = pk

        requested_scopes = [scope.lower() for scope in scopes]
        missing_scopes = [scope for scope in requested_scopes if scope not in mappings_by_scope]
        if missing_scopes:
            raise AuthentikRequestValidationError(
                f"Unsupported OIDC scope(s): {', '.join(sorted(set(missing_scopes)))}"
            )
        return [mappings_by_scope[scope] for scope in requested_scopes]

    def get_application(self, slug: str) -> dict | None:
        """Get an application by its exact slug."""
        url = f"{self.base_url}/api/v3/core/applications/{slug}/"
        try:
            return self._request("GET", url).json()
        except AuthentikNotFoundError:
            return None

    def list_applications(self) -> Iterator[dict]:
        """List all applications."""
        url = f"{self.base_url}/api/v3/core/applications/"
        return self._get_paginated(url)

    def get_oauth_provider(self, provider_pk: int) -> dict | None:
        """Get an OAuth provider by primary key."""
        url = f"{self.base_url}/api/v3/providers/oauth2/{provider_pk}/"
        try:
            return self._request("GET", url).json()
        except AuthentikNotFoundError:
            return None

    def find_oauth_provider(self, name: str) -> dict | None:
        """Find an OAuth provider by exact deterministic name."""
        url = f"{self.base_url}/api/v3/providers/oauth2/"
        providers = [
            provider
            for provider in self._get_paginated(url, params={"name": name})
            if provider.get("name") == name
        ]
        if len(providers) > 1:
            raise AuthentikConflictError(f"Multiple OAuth providers have the exact name {name!r}")
        return providers[0] if providers else None

    def _format_redirect_uris(self, redirect_uris: str | list[str] | list[dict]) -> list[dict]:
        """Format redirect URIs as required by the Authentik REST API."""
        if isinstance(redirect_uris, list) and all(
            isinstance(item, dict) for item in redirect_uris
        ):
            return redirect_uris
        if isinstance(redirect_uris, str):
            uris = [
                uri.strip()
                for line in redirect_uris.splitlines()
                for uri in line.split(",")
                if uri.strip()
            ]
        elif isinstance(redirect_uris, list):
            uris = [str(uri).strip() for uri in redirect_uris if str(uri).strip()]
        else:
            uris = []
        return [{"matching_mode": "strict", "url": uri} for uri in uris]

    def _provider_payload(
        self,
        name: str,
        client_id: str,
        client_secret: str,
        redirect_uris: str,
        authorization_flow: str,
        invalidation_flow: str,
        property_mappings: list[str],
        grant_types: list[str] | None,
    ) -> dict:
        return {
            "name": name,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": self._format_redirect_uris(redirect_uris),
            "authorization_flow": authorization_flow,
            "invalidation_flow": invalidation_flow,
            "property_mappings": property_mappings,
            "grant_types": grant_types
            or ["authorization_code", "refresh_token", "client_credentials"],
        }

    def create_oauth_provider(
        self,
        name: str,
        client_id: str,
        client_secret: str,
        redirect_uris: str,
        authorization_flow: str,
        invalidation_flow: str,
        property_mappings: list[str],
        grant_types: list[str] | None = None,
    ) -> int:
        """Create a provider, recovering an ambiguous result by exact name."""
        url = f"{self.base_url}/api/v3/providers/oauth2/"
        payload = self._provider_payload(
            name,
            client_id,
            client_secret,
            redirect_uris,
            authorization_flow,
            invalidation_flow,
            property_mappings,
            grant_types,
        )
        try:
            response = self._request("POST", url, retry=False, json=payload)
        except (AuthentikTransientError, AuthentikConflictError):
            provider = self.find_oauth_provider(name)
            if provider is not None and provider.get("pk") is not None:
                return int(provider["pk"])
            raise
        provider_pk = response.json().get("pk")
        if provider_pk is None:
            raise AuthentikRequestValidationError(
                f"Create response for OAuth provider {name!r} did not contain a primary key"
            )
        return int(provider_pk)

    def update_oauth_provider(
        self,
        provider_pk: int,
        name: str,
        client_id: str,
        client_secret: str,
        redirect_uris: str,
        authorization_flow: str,
        invalidation_flow: str,
        property_mappings: list[str],
        grant_types: list[str] | None = None,
    ) -> bool:
        """Update an existing OAuth provider."""
        url = f"{self.base_url}/api/v3/providers/oauth2/{provider_pk}/"
        payload = self._provider_payload(
            name,
            client_id,
            client_secret,
            redirect_uris,
            authorization_flow,
            invalidation_flow,
            property_mappings,
            grant_types,
        )
        self._request("PUT", url, json=payload)
        return True

    def create_application(self, name: str, slug: str, provider_pk: int) -> bool:
        """Create an application, recovering an ambiguous result by exact slug."""
        url = f"{self.base_url}/api/v3/core/applications/"
        payload = {"name": name, "slug": slug, "provider": provider_pk}
        try:
            self._request("POST", url, retry=False, json=payload)
        except (AuthentikTransientError, AuthentikConflictError):
            application = self.get_application(slug)
            if application is not None and application.get("provider") == provider_pk:
                return True
            raise
        return True

    def update_application(self, slug: str, name: str, provider_pk: int) -> bool:
        """Update an existing application's name/provider via PATCH.

        A partial update is required: a full PUT must include every required field
        (notably ``slug``, which this caller does not resend), so Authentik rejects
        it with HTTP 400. PATCH only touches the fields sent here.
        """
        url = f"{self.base_url}/api/v3/core/applications/{slug}/"
        self._request("PATCH", url, json={"name": name, "provider": provider_pk})
        return True

    def delete_application(self, slug: str) -> None:
        """Delete an application, treating absence as success."""
        url = f"{self.base_url}/api/v3/core/applications/{slug}/"
        try:
            self._request("DELETE", url)
        except AuthentikNotFoundError:
            pass

    def delete_oauth_provider(self, provider_pk: int) -> None:
        """Delete an OAuth provider, treating absence as success."""
        url = f"{self.base_url}/api/v3/providers/oauth2/{provider_pk}/"
        try:
            self._request("DELETE", url)
        except AuthentikNotFoundError:
            pass
