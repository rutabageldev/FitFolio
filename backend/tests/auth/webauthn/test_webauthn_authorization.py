"""Authorization tests for WebAuthn endpoints."""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.security, pytest.mark.integration]


class TestWebAuthnRegistrationAuthorization:
    """Authorization for registration endpoints."""

    @pytest.mark.asyncio
    async def test_register_start_no_csrf_token(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/webauthn/register/start", json={"email": "test@example.com"}
        )
        assert response.status_code in [400, 403]

    @pytest.mark.asyncio
    async def test_register_finish_no_csrf_token(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/webauthn/register/finish",
            json={
                "email": "test@example.com",
                "credential": {"id": "test"},
                "challenge_id": "test",
            },
        )
        assert response.status_code in [400, 403]


class TestWebAuthnAuthenticationAuthorization:
    """Authorization for authentication endpoints."""

    @pytest.mark.asyncio
    async def test_authenticate_start_no_csrf_token(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/start",
            json={"email": "test@example.com"},
        )
        assert response.status_code in [400, 403]

    @pytest.mark.asyncio
    async def test_authenticate_finish_no_csrf_token(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/finish",
            json={
                "email": "test@example.com",
                "credential": {"id": "test"},
                "challenge_id": "test",
            },
        )
        assert response.status_code in [400, 403]


class TestCredentialManagementAuthorization:
    """Authorization for credential management endpoints."""

    @pytest.mark.asyncio
    async def test_list_credentials_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/webauthn/credentials")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_credential_unauthenticated(self, client: AsyncClient):
        response = await client.delete("/api/v1/auth/webauthn/credentials/fake-id")
        assert response.status_code in [401, 403, 404]
