"""Authorization tests specific to magic link endpoints."""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.security, pytest.mark.integration]


class TestMagicLinkAuthorization:
    """Test authorization for magic link endpoints."""

    @pytest.mark.asyncio
    async def test_magic_link_start_no_csrf(self, client: AsyncClient):
        """Magic link start doesn't require CSRF (public endpoint)."""
        response = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": "test@example.com"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_magic_link_verify_no_csrf(self, client: AsyncClient):
        """Should reject request without CSRF token."""
        response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": "fake-token"},
        )
        assert response.status_code in [400, 403]
