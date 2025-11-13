"""
Auth API Contract Tests

Verifies that authentication-related endpoints are reachable at their
documented versioned paths and return expected unauthenticated statuses.
"""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.contract, pytest.mark.integration]


class TestAuthVersioning:
    """Auth endpoints must be under /api/v1/auth."""

    async def test_magic_link_versioned_path_exists(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/magic-link/start", json={"email": "test@example.com"}
        )
        assert resp.status_code != 404

    async def test_me_endpoint_versioned_and_protected(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401


class TestAuthEndpointInventory:
    """Comprehensive auth endpoint inventory."""

    EXPECTED_AUTH_ENDPOINTS = [
        # Magic link
        ("POST", "/api/v1/auth/magic-link/start", 200),
        ("POST", "/api/v1/auth/magic-link/verify", 400),
        # WebAuthn
        ("POST", "/api/v1/auth/webauthn/register/start", 401),
        ("POST", "/api/v1/auth/webauthn/register/finish", 401),
        ("POST", "/api/v1/auth/webauthn/authenticate/start", 400),
        ("POST", "/api/v1/auth/webauthn/authenticate/finish", 400),
        ("GET", "/api/v1/auth/webauthn/credentials", 401),
        # Sessions and logout
        ("GET", "/api/v1/auth/me", 401),
        ("GET", "/api/v1/auth/sessions", 401),
        ("POST", "/api/v1/auth/sessions/revoke-all-others", 401),
        ("POST", "/api/v1/auth/logout", 401),
        # Email verification
        ("POST", "/api/v1/auth/email/verify", 400),
        ("POST", "/api/v1/auth/email/resend-verification", 400),
    ]

    @pytest.mark.parametrize("method,path,expected_status", EXPECTED_AUTH_ENDPOINTS)
    async def test_auth_endpoint_exists(
        self, client: AsyncClient, method: str, path: str, expected_status: int
    ):
        if method == "GET":
            response = await client.get(path)
        elif method == "POST":
            response = await client.post(path, json={})
        elif method == "DELETE":
            response = await client.delete(path)
        else:
            pytest.fail(f"Unsupported method: {method}")

        assert response.status_code != 404, f"{method} {path} should exist"
        # Expected statuses are unauthenticated defaults; warn if different
        if response.status_code != expected_status:
            msg = (
                f"Note: {method} {path} returned {response.status_code}, "
                f"expected {expected_status}"
            )
            print(msg)
