# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the Authentik API client."""

from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from requests import Response
from requests.exceptions import ConnectionError

from authentik_api import (
    PAGINATION_MAX_PAGES,
    PAGINATION_PAGE_SIZE,
    ApiAvailability,
    AuthentikAPI,
)
from exceptions import (
    AuthentikAPIError,
    AuthentikAuthenticationError,
    AuthentikAuthorizationError,
    AuthentikConflictError,
    AuthentikNotFoundError,
    AuthentikRequestValidationError,
    AuthentikTransientError,
)


def response(status: int, payload: str = "{}") -> Response:
    """Build a requests response for client tests."""
    result = Response()
    result.status_code = status
    result._content = payload.encode()
    result.url = "http://authentik.test/api"
    return result


@pytest.mark.parametrize(
    "status,error",
    [
        (400, AuthentikRequestValidationError),
        (401, AuthentikAuthenticationError),
        (403, AuthentikAuthorizationError),
        (404, AuthentikNotFoundError),
        (409, AuthentikConflictError),
    ],
)
def test_request_classifies_permanent_failures_without_retry(status: int, error: type) -> None:
    api = AuthentikAPI("token")
    api.session.request = MagicMock(return_value=response(status))

    with pytest.raises(error):
        api._request("GET", "http://authentik.test/resource")

    api.session.request.assert_called_once()


def test_request_retries_connection_failures_with_bounded_backoff(mocker: MockerFixture) -> None:
    sleep = mocker.patch("authentik_api.time.sleep")
    api = AuthentikAPI("token")
    api.session.request = MagicMock(
        side_effect=[ConnectionError("down"), ConnectionError("down"), response(200)]
    )

    assert api._request("GET", "http://authentik.test/resource").status_code == 200
    assert api.session.request.call_count == 3
    assert [call.args[0] for call in sleep.call_args_list] == [0.25, 0.5]


def test_request_raises_transient_error_after_retry_budget(mocker: MockerFixture) -> None:
    mocker.patch("authentik_api.time.sleep")
    api = AuthentikAPI("token")
    api.session.request = MagicMock(return_value=response(503))

    with pytest.raises(AuthentikTransientError):
        api._request("DELETE", "http://authentik.test/resource")

    assert api.session.request.call_count == 3


def test_ambiguous_provider_create_recovers_by_exact_name_without_second_post() -> None:
    api = AuthentikAPI("token")
    api.session.request = MagicMock(
        side_effect=[
            response(503),
            response(200, '{"results": [{"pk": 42, "name": "managed-provider"}]}'),
        ]
    )

    provider_pk = api.create_oauth_provider(
        name="managed-provider",
        client_id="client",
        client_secret="secret",
        redirect_uris="https://example.test/callback",
        authorization_flow="authorization",
        invalidation_flow="invalidation",
        property_mappings=["openid-pk"],
    )

    assert provider_pk == 42
    assert [call.args[0] for call in api.session.request.call_args_list] == ["POST", "GET"]
    assert api.session.request.call_args_list[1].kwargs["params"]["name"] == "managed-provider"


def test_ambiguous_application_create_recovers_by_slug_without_second_post() -> None:
    api = AuthentikAPI("token")
    api.session.request = MagicMock(
        side_effect=[
            response(503),
            response(200, '{"slug": "managed-app", "provider": 42}'),
        ]
    )

    assert api.create_application("Managed app", "managed-app", 42)
    assert [call.args[0] for call in api.session.request.call_args_list] == ["POST", "GET"]


def test_property_mappings_use_exact_explicit_scope_names() -> None:
    api = AuthentikAPI("token")
    api._scope_property_mappings = [
        {"pk": "openid-pk", "scope_name": "openid", "name": "OpenID Scope"},
        {"pk": "email-pk", "scope_name": "email", "name": "Email Scope"},
        {"pk": "admin-pk", "scope_name": "admin", "name": "scope email admin"},
    ]

    assert api.get_property_mappings(["email", "openid"]) == ["email-pk", "openid-pk"]


def test_property_mappings_reject_unsupported_scope_without_fallback() -> None:
    api = AuthentikAPI("token")
    api._scope_property_mappings = [
        {"pk": "openid-pk", "scope_name": "openid"},
        {"pk": "email-pk", "scope_name": "email"},
    ]

    with pytest.raises(AuthentikRequestValidationError, match="groups"):
        api.get_property_mappings(["openid", "groups"])


@pytest.mark.parametrize("status", [401, 403, 404, 500, 503])
def test_is_service_available_false_on_any_api_error(status: int) -> None:
    api = AuthentikAPI("token")
    api.session.request = MagicMock(return_value=response(status))

    assert api.is_service_available is False


def test_is_service_available_true_when_reachable() -> None:
    api = AuthentikAPI("token")
    api.session.request = MagicMock(return_value=response(200, '{"results": []}'))

    assert api.is_service_available is True


@pytest.mark.parametrize(
    "status,expected",
    [
        (200, ApiAvailability.AVAILABLE),
        (401, ApiAvailability.TOKEN_REJECTED),
        (403, ApiAvailability.TOKEN_REJECTED),
        (404, ApiAvailability.UNAVAILABLE),
        (500, ApiAvailability.UNAVAILABLE),
        (503, ApiAvailability.UNAVAILABLE),
    ],
)
def test_availability_separates_rejected_token_from_unavailable_service(
    status: int, expected: ApiAvailability
) -> None:
    """A rejected token is terminal; anything else is worth retrying."""
    api = AuthentikAPI("token")
    api.session.request = MagicMock(return_value=response(status, '{"results": []}'))

    assert api.availability is expected


def test_availability_reports_unavailable_when_unreachable() -> None:
    api = AuthentikAPI("token")
    api.session.request = MagicMock(side_effect=ConnectionError("refused"))

    assert api.availability is ApiAvailability.UNAVAILABLE


def test_update_application_uses_patch_to_preserve_unmanaged_fields() -> None:
    api = AuthentikAPI("token")
    api.session.request = MagicMock(return_value=response(200))

    api.update_application(slug="my-app", name="My App", provider_pk=5)

    method, url = api.session.request.call_args.args
    assert method == "PATCH"
    assert url.endswith("/api/v3/core/applications/my-app/")
    assert api.session.request.call_args.kwargs["json"] == {"name": "My App", "provider": 5}


def test_is_service_available_probe_limits_page_size() -> None:
    api = AuthentikAPI("token")
    api.session.request = MagicMock(return_value=response(200, '{"results": []}'))

    assert api.is_service_available is True
    assert api.session.request.call_args.kwargs["params"] == {"page_size": 1}


def test_delete_application_treats_missing_as_success() -> None:
    api = AuthentikAPI("token")
    api.session.request = MagicMock(return_value=response(404))

    assert api.delete_application("gone") is None
    api.session.request.assert_called_once()


def test_delete_oauth_provider_treats_missing_as_success() -> None:
    api = AuthentikAPI("token")
    api.session.request = MagicMock(return_value=response(404))

    assert api.delete_oauth_provider(42) is None


def test_get_paginated_sends_bounded_page_size() -> None:
    api = AuthentikAPI("token")
    api.session.request = MagicMock(
        return_value=response(200, '{"results": [{"pk": 1}], "pagination": {"next": 0}}')
    )

    results = list(api._get_paginated("http://authentik.test/api/"))

    assert results == [{"pk": 1}]
    assert api.session.request.call_args.kwargs["params"]["page_size"] == PAGINATION_PAGE_SIZE


def test_get_paginated_stops_at_max_pages() -> None:
    api = AuthentikAPI("token")
    # Every page points at another page, so only the cap terminates the loop.
    api.session.request = MagicMock(
        return_value=response(200, '{"results": [{"pk": 1}], "pagination": {"next": 2}}')
    )

    with pytest.raises(AuthentikAPIError, match="exceeded the maximum"):
        list(api._get_paginated("http://authentik.test/api/"))

    assert api.session.request.call_count == PAGINATION_MAX_PAGES


def test_is_service_available_caches_successful_probe() -> None:
    api = AuthentikAPI("token")
    api.session.request = MagicMock(return_value=response(200))

    assert api.is_service_available is True
    assert api.is_service_available is True

    api.session.request.assert_called_once()
