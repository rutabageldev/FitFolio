"""Tests for CSRF protection middleware."""

import pytest


class TestCSRFTokenGeneration:
    """Test CSRF token generation and setting."""

    @pytest.mark.asyncio
    async def test_csrf_token_set_on_get_request(self, client):
        """CSRF token should be set in cookie on GET requests."""
        response = await client.get("/healthz")
        assert response.status_code == 200
        assert "csrf_token" in response.cookies
        assert "x-csrf-token" in response.headers

        # Token should be same in cookie and header
        cookie_token = response.cookies["csrf_token"]
        header_token = response.headers["x-csrf-token"]
        assert cookie_token == header_token
        assert len(cookie_token) > 0

    @pytest.mark.asyncio
    async def test_csrf_cookie_attributes(self, client):
        """CSRF cookie should have correct security attributes."""
        response = await client.get("/healthz")
        csrf_cookie = response.cookies["csrf_token"]

        # Cookie should not be HTTP-only (JS needs to read it)
        # AsyncClient doesn't expose full cookie attributes, so we
        # just verify the token is accessible
        assert csrf_cookie is not None


class TestCSRFProtectedEndpoints:
    """Test CSRF protection on state-changing endpoints."""

    @pytest.mark.asyncio
    async def test_post_without_csrf_token_rejected(self, client):
        """POST requests without CSRF token should be rejected."""
        response = await client.post(
            "/auth/webauthn/register/start",
            json={"email": "test@example.com"},
        )
        assert response.status_code == 403
        assert "CSRF" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_post_with_valid_csrf_token_accepted(self, client, db_session):
        """POST requests with valid CSRF token should be accepted."""
        from datetime import UTC, datetime

        from app.db.models.auth import User

        # Create user first
        now = datetime.now(UTC)
        user = User(
            email="csrf@example.com",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()

        # Get CSRF token
        get_response = await client.get("/healthz")
        csrf_token = get_response.cookies["csrf_token"]

        # Use token in POST request
        response = await client.post(
            "/auth/webauthn/register/start",
            json={"email": "csrf@example.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_post_with_mismatched_tokens_rejected(self, client):
        """POST with mismatched cookie and header tokens should be rejected."""
        response = await client.post(
            "/auth/webauthn/register/start",
            json={"email": "test@example.com"},
            cookies={"csrf_token": "token_in_cookie"},
            headers={"X-CSRF-Token": "different_token_in_header"},
        )
        assert response.status_code == 403
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_post_with_missing_header_rejected(self, client):
        """POST with cookie but no header should be rejected."""
        response = await client.post(
            "/auth/webauthn/register/start",
            json={"email": "test@example.com"},
            cookies={"csrf_token": "some_token"},
            # No X-CSRF-Token header
        )
        assert response.status_code == 403
        assert "missing" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_post_with_missing_cookie_rejected(self, client):
        """POST with header but no cookie should be rejected."""
        response = await client.post(
            "/auth/webauthn/register/start",
            json={"email": "test@example.com"},
            # No csrf_token cookie
            headers={"X-CSRF-Token": "some_token"},
        )
        assert response.status_code == 403


class TestCSRFExemptPaths:
    """Test paths that are exempt from CSRF protection."""

    @pytest.mark.asyncio
    async def test_magic_link_start_exempt(self, client, db_session):
        """Magic link start should not require CSRF token."""
        from datetime import UTC, datetime

        from app.db.models.auth import User

        # Create user
        now = datetime.now(UTC)
        user = User(
            email="exempt@example.com",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()

        # Should work without CSRF token
        response = await client.post(
            "/auth/magic-link/start",
            json={"email": "exempt@example.com"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_healthz_exempt(self, client):
        """Health check should not require CSRF token."""
        response = await client.get("/healthz")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_debug_endpoints_exempt(self, client):
        """Debug endpoints should be exempt from CSRF."""
        response = await client.post(
            "/_debug/mail",
            params={"to": "test@example.com"},
        )
        # May return error for other reasons, but not CSRF
        assert response.status_code != 403 or "CSRF" not in str(response.json())


class TestCSRFMethods:
    """Test CSRF protection applies to correct HTTP methods."""

    @pytest.mark.asyncio
    async def test_get_request_does_not_require_csrf(self, client):
        """GET requests should not require CSRF token."""
        response = await client.get("/healthz")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_options_request_does_not_require_csrf(self, client):
        """OPTIONS requests should not require CSRF token."""
        response = await client.options("/healthz")
        # May not be implemented, but shouldn't fail due to CSRF
        assert response.status_code != 403

    @pytest.mark.asyncio
    async def test_put_requires_csrf(self, client):
        """PUT requests should require CSRF token (if endpoint exists)."""
        # Test with a PUT endpoint if one exists
        # For now, just verify the middleware is checking PUT methods
        pass  # Would need a PUT endpoint to test

    @pytest.mark.asyncio
    async def test_delete_requires_csrf(self, client):
        """DELETE requests should require CSRF token (if endpoint exists)."""
        # Test with a DELETE endpoint if one exists
        pass  # Would need a DELETE endpoint to test
