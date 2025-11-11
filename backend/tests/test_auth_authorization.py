"""Authorization tests for auth endpoints.

Tests unauthenticated access and inactive user handling across all endpoints.
"""

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.db.models.auth import User


@pytest_asyncio.fixture
async def csrf_token(client: AsyncClient):
    """Get CSRF token for requests."""
    response = await client.get("/healthz")
    return response.cookies["csrf_token"]


@pytest_asyncio.fixture
async def inactive_user(db_session):
    """Create an inactive user for testing."""
    now = datetime.now(UTC)
    user = User(
        email="inactive@test.com",
        is_active=False,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestWebAuthnRegistrationAuthorization:
    """Test authorization for WebAuthn registration endpoints."""

    @pytest.mark.asyncio
    async def test_register_start_no_csrf_token(self, client: AsyncClient):
        """Should reject request without CSRF token."""
        response = await client.post(
            "/api/v1/auth/webauthn/register/start",
            json={"email": "test@example.com"},
        )

        # CSRF middleware should reject this
        assert response.status_code in [400, 403]

    @pytest.mark.asyncio
    async def test_register_finish_no_csrf_token(self, client: AsyncClient):
        """Should reject request without CSRF token."""
        response = await client.post(
            "/api/v1/auth/webauthn/register/finish",
            json={
                "email": "test@example.com",
                "credential": {"id": "test"},
                "challenge_id": "test",
            },
        )

        # CSRF middleware should reject this
        assert response.status_code in [400, 403]


class TestWebAuthnAuthenticationAuthorization:
    """Test authorization for WebAuthn authentication endpoints."""

    @pytest.mark.asyncio
    async def test_authenticate_start_no_csrf_token(self, client: AsyncClient):
        """Should reject request without CSRF token."""
        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/start",
            json={"email": "test@example.com"},
        )

        # CSRF middleware should reject this
        assert response.status_code in [400, 403]

    @pytest.mark.asyncio
    async def test_authenticate_finish_no_csrf_token(self, client: AsyncClient):
        """Should reject request without CSRF token."""
        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/finish",
            json={
                "email": "test@example.com",
                "credential": {"id": "test"},
                "challenge_id": "test",
            },
        )

        # CSRF middleware should reject this
        assert response.status_code in [400, 403]


class TestCredentialManagementAuthorization:
    """Test authorization for credential management endpoints."""

    @pytest.mark.asyncio
    async def test_list_credentials_unauthenticated(
        self, client: AsyncClient, csrf_token
    ):
        """Should reject unauthenticated request."""
        response = await client.get(
            "/api/v1/auth/webauthn/credentials",
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_credential_unauthenticated(
        self, client: AsyncClient, csrf_token
    ):
        """Should reject unauthenticated request."""
        response = await client.delete(
            "/api/v1/auth/webauthn/credentials/fake-id",
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Returns 404 if unauthenticated (doesn't reveal if credential exists)
        assert response.status_code in [401, 404]


class TestSessionManagementAuthorization:
    """Test authorization for session management endpoints."""

    @pytest.mark.asyncio
    async def test_list_sessions_unauthenticated(self, client: AsyncClient, csrf_token):
        """Should reject unauthenticated request."""
        response = await client.get(
            "/api/v1/auth/sessions",
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_revoke_session_unauthenticated(
        self, client: AsyncClient, csrf_token
    ):
        """Should reject unauthenticated request."""
        import uuid

        session_id = str(uuid.uuid4())
        response = await client.delete(
            f"/api/v1/auth/sessions/{session_id}",
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_revoke_all_other_sessions_unauthenticated(
        self, client: AsyncClient, csrf_token
    ):
        """Should reject unauthenticated request."""
        response = await client.delete(
            "/api/v1/auth/sessions/others",
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 401


class TestUserEndpointAuthorization:
    """Test authorization for user endpoints."""

    @pytest.mark.asyncio
    async def test_me_endpoint_unauthenticated(self, client: AsyncClient, csrf_token):
        """Should reject unauthenticated request."""
        response = await client.get(
            "/api/v1/auth/me",
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 401


class TestMagicLinkAuthorization:
    """Test authorization for magic link endpoints."""

    @pytest.mark.asyncio
    async def test_magic_link_start_no_csrf(self, client: AsyncClient):
        """Magic link start doesn't require CSRF (public endpoint)."""
        response = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": "test@example.com"},
        )

        # This is a public endpoint, should work without CSRF
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_magic_link_verify_no_csrf(self, client: AsyncClient):
        """Should reject request without CSRF token."""
        response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": "fake-token"},
        )

        # CSRF middleware should reject this
        assert response.status_code in [400, 403]


class TestEmailVerificationAuthorization:
    """Test authorization for email verification endpoints."""

    @pytest.mark.asyncio
    async def test_verify_email_no_csrf(self, client: AsyncClient):
        """Should reject request without CSRF token."""
        response = await client.post(
            "/api/v1/auth/email/verify",
            json={"token": "fake-token"},
        )

        # CSRF middleware should reject this
        assert response.status_code in [400, 403]

    @pytest.mark.asyncio
    async def test_resend_verification_no_csrf(self, client: AsyncClient):
        """Resend verification doesn't require CSRF (public endpoint)."""
        response = await client.post(
            "/api/v1/auth/email/resend-verification",
            json={"email": "test@example.com"},
        )

        # This is a public endpoint, should work without CSRF
        assert response.status_code == 200
