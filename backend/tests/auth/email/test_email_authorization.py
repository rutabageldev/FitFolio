"""Authorization behavior for email verification endpoints."""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.security, pytest.mark.integration]


class TestEmailVerificationAuthorization:
    @pytest.mark.asyncio
    async def test_verify_email_no_csrf(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/email/verify", json={"token": "fake-token"}
        )
        assert response.status_code in [400, 403]

    @pytest.mark.asyncio
    async def test_resend_verification_no_csrf(self, client: AsyncClient):
        """Resend verification doesn't require CSRF (public)."""
        response = await client.post(
            "/api/v1/auth/email/resend-verification", json={"email": "test@example.com"}
        )
        assert response.status_code == 200
