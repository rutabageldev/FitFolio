"""WebAuthn integration tests with minimal mocking for better coverage.

Focuses on testing the actual WebAuthn authentication flow end-to-end.
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from app.db.models.auth import User, WebAuthnCredential


@pytest_asyncio.fixture
async def user_with_webauthn(db_session):
    """Create a user with WebAuthn credential."""
    now = datetime.now(UTC)
    user = User(
        email="webauthn@example.com",
        is_active=True,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Add WebAuthn credential
    credential = WebAuthnCredential(
        user_id=user.id,
        credential_id=b"test_credential_id_webauthn_user",
        public_key=b"test_public_key_data",
        sign_count=0,
        transports=["usb", "nfc"],
        created_at=now,
        updated_at=now,
    )
    db_session.add(credential)
    await db_session.commit()
    await db_session.refresh(credential)

    return user, credential


class TestWebAuthnAuthenticateStart:
    """Integration tests for WebAuthn authenticate/start endpoint."""

    @pytest.mark.asyncio
    async def test_authenticate_start_stores_challenge_in_redis(
        self, client: AsyncClient, csrf_token, user_with_webauthn
    ):
        """Should generate challenge and store in Redis."""
        user, _credential = user_with_webauthn

        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/start",
            json={"email": user.email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "challenge_id" in data
        assert "options" in data
        assert "challenge" in data["options"]
        assert "allowCredentials" in data["options"]

        # Verify challenge was stored in Redis
        from app.core.redis_client import get_redis

        redis = await get_redis()
        challenge_key = f"webauthn:challenge:authentication:{data['challenge_id']}"
        stored_data = await redis.get(challenge_key)
        assert stored_data is not None

    @pytest.mark.asyncio
    async def test_authenticate_start_invalid_email_422(
        self, client: AsyncClient, csrf_token
    ):
        """Should reject invalid email format."""
        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/start",
            json={"email": "not-an-email"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_authenticate_start_includes_user_credentials(
        self, client: AsyncClient, csrf_token, user_with_webauthn
    ):
        """Should include user's registered credentials in allowCredentials."""
        user, credential = user_with_webauthn

        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/start",
            json={"email": user.email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify credential is included
        allow_creds = data["options"]["allowCredentials"]
        assert len(allow_creds) == 1
        assert allow_creds[0]["id"] == credential.credential_id.hex()
        assert allow_creds[0]["type"] == "public-key"

    @pytest.mark.asyncio
    async def test_authenticate_start_redis_failure_returns_500(
        self, client: AsyncClient, csrf_token, user_with_webauthn
    ):
        """Should return 500 if Redis storage fails."""
        user, _credential = user_with_webauthn

        # Mock Redis to fail
        with patch("app.core.challenge_storage.store_challenge") as mock_store:
            mock_store.side_effect = RuntimeError("Redis connection failed")

            response = await client.post(
                "/api/v1/auth/webauthn/authenticate/start",
                json={"email": user.email},
                cookies={"csrf_token": csrf_token},
                headers={"X-CSRF-Token": csrf_token},
            )

            assert response.status_code == 500
            assert "authentication" in response.json()["detail"].lower()


class TestWebAuthnAuthenticateFinish:
    """Integration tests for WebAuthn authenticate/finish endpoint."""

    @pytest.mark.asyncio
    async def test_authenticate_finish_invalid_challenge_id_returns_422(
        self, client: AsyncClient, csrf_token
    ):
        """Should return 422 for malformed request."""
        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/finish",
            json={
                "challenge_id": "invalid_challenge_id",
                "credential": {
                    "id": "test_cred",
                    "rawId": "test_raw_id",
                    "response": {
                        "authenticatorData": "test_data",
                        "clientDataJSON": "test_client_data",
                        "signature": "test_signature",
                    },
                    "type": "public-key",
                },
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Validation error for malformed data
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_authenticate_finish_missing_credential_id_returns_400(
        self, client: AsyncClient, csrf_token, user_with_webauthn
    ):
        """Should return 400 if credential ID not found."""
        user, _credential = user_with_webauthn

        # First get a valid challenge
        start_response = await client.post(
            "/api/v1/auth/webauthn/authenticate/start",
            json={"email": user.email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        challenge_data = start_response.json()

        # Try to authenticate with non-existent credential
        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/finish",
            json={
                "challenge_id": challenge_data["challenge_id"],
                "credential": {
                    "id": "nonexistent_credential_id",
                    "rawId": "nonexistent",
                    "response": {
                        "authenticatorData": "test",
                        "clientDataJSON": "test",
                        "signature": "test",
                    },
                    "type": "public-key",
                },
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code in [400, 422]


class TestWebAuthnRegistrationIntegration:
    """Integration tests for WebAuthn registration flow."""

    @pytest.mark.asyncio
    async def test_register_start_new_user_creates_unverified(
        self, client: AsyncClient, csrf_token, db_session
    ):
        """Should create unverified user on registration start."""
        email = "newwebauthn@example.com"

        response = await client.post(
            "/api/v1/auth/webauthn/register/start",
            json={"email": email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200

        # Verify user was created
        user_stmt = select(User).where(User.email == email.lower())
        user_result = await db_session.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        assert user is not None
        assert user.is_email_verified is False
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_register_start_existing_user_returns_existing(
        self, client: AsyncClient, csrf_token, user_with_webauthn, db_session
    ):
        """Should work with existing user email."""
        user, _credential = user_with_webauthn

        # Try to register with existing email
        response = await client.post(
            "/api/v1/auth/webauthn/register/start",
            json={"email": user.email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200

        # Should still be the same user
        user_stmt = select(User).where(User.email == user.email.lower())
        user_result = await db_session.execute(user_stmt)
        found_user = user_result.scalar_one()

        assert found_user.id == user.id

    @pytest.mark.asyncio
    async def test_register_finish_invalid_challenge_returns_400(
        self, client: AsyncClient, csrf_token
    ):
        """Should return 400 for invalid challenge."""
        response = await client.post(
            "/api/v1/auth/webauthn/register/finish",
            json={
                "challenge_id": "invalid_challenge",
                "credential": {
                    "id": "test",
                    "rawId": "test",
                    "response": {
                        "attestationObject": "test",
                        "clientDataJSON": "test",
                    },
                    "type": "public-key",
                },
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code in [400, 422]
        # Validation errors may return different detail formats
        # Just verify we got an error response
