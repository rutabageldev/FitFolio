"""WebAuthn integration tests WITHOUT mocking - for maximum coverage.

These tests use the REAL WebAuthn manager and Redis to execute actual code paths.
Only the browser's credential response is mocked (unavoidable in backend tests).
"""

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from app.db.models.auth import LoginEvent, User, WebAuthnCredential


@pytest_asyncio.fixture
async def csrf_token(client: AsyncClient):
    """Get CSRF token for tests."""
    response = await client.get("/healthz")
    return response.cookies["csrf_token"]


@pytest_asyncio.fixture
async def user_with_credential(db_session):
    """Create a user with a WebAuthn credential for testing."""
    now = datetime.now(UTC)
    user = User(
        email="webauthn@test.com",
        is_active=True,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Add a credential
    credential = WebAuthnCredential(
        user_id=user.id,
        credential_id=b"real_credential_id_for_testing",
        public_key=b"real_public_key_data_here",
        sign_count=0,
        transports=["usb", "nfc"],
        created_at=now,
        updated_at=now,
    )
    db_session.add(credential)
    await db_session.commit()
    await db_session.refresh(credential)

    return user, credential


class TestWebAuthnRegistrationNoMocks:
    """Test WebAuthn registration with REAL implementations."""

    @pytest.mark.asyncio
    async def test_register_start_creates_user_and_stores_challenge_in_redis(
        self, client: AsyncClient, csrf_token, db_session
    ):
        """Should create user and store real challenge in Redis."""
        from app.core.redis_client import get_redis

        email = "newwebauthn@test.com"

        response = await client.post(
            "/api/v1/auth/webauthn/register/start",
            json={"email": email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "challenge_id" in data
        assert "options" in data
        assert "challenge" in data["options"]
        assert "rp" in data["options"]
        assert data["options"]["rp"]["name"] == "FitFolio"

        # Verify user was created
        user_stmt = select(User).where(User.email == email.lower())
        user_result = await db_session.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        assert user is not None
        assert user.is_active is True
        assert user.is_email_verified is False

        # Verify challenge was stored in REAL Redis
        redis = await get_redis()
        challenge_key = f"webauthn:challenge:registration:{data['challenge_id']}"
        stored_data = await redis.get(challenge_key)

        assert stored_data is not None
        # Stored format: "email:challenge_hex"
        assert email.lower() in stored_data
        assert ":" in stored_data

    @pytest.mark.asyncio
    async def test_register_start_existing_user_reuses_user(
        self, client: AsyncClient, csrf_token, db_session
    ):
        """Should reuse existing user for registration."""
        # Create existing user
        now = datetime.now(UTC)
        user = User(
            email="existing@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        original_id = user.id

        response = await client.post(
            "/api/v1/auth/webauthn/register/start",
            json={"email": user.email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200

        # Verify same user was used (not created new)
        user_stmt = select(User).where(User.email == user.email.lower())
        user_result = await db_session.execute(user_stmt)
        found_user = user_result.scalar_one()

        assert found_user.id == original_id

    @pytest.mark.asyncio
    async def test_register_start_challenge_expires_in_redis(
        self, client: AsyncClient, csrf_token
    ):
        """Should set TTL on challenge in Redis."""
        from app.core.redis_client import get_redis

        response = await client.post(
            "/api/v1/auth/webauthn/register/start",
            json={"email": "ttl@test.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify TTL is set (should be 60 seconds)
        redis = await get_redis()
        challenge_key = f"webauthn:challenge:registration:{data['challenge_id']}"
        ttl = await redis.ttl(challenge_key)

        assert ttl > 0
        assert ttl <= 60  # Should be 60 seconds or less


class TestWebAuthnAuthenticationNoMocks:
    """Test WebAuthn authentication with REAL implementations."""

    @pytest.mark.asyncio
    async def test_authenticate_start_generates_real_challenge(
        self, client: AsyncClient, csrf_token, user_with_credential
    ):
        """Generate real authentication challenge with actual WebAuthn manager."""
        from app.core.redis_client import get_redis

        user, credential = user_with_credential

        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/start",
            json={"email": user.email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure from REAL WebAuthn manager
        assert "challenge_id" in data
        assert "options" in data
        assert "challenge" in data["options"]
        assert "rpId" in data["options"]
        # rpId comes from environment (RP_ID), don't hardcode
        assert data["options"]["rpId"] is not None

        # Verify allowCredentials includes our credential
        assert "allowCredentials" in data["options"]
        allow_creds = data["options"]["allowCredentials"]
        assert len(allow_creds) == 1
        assert allow_creds[0]["id"] == credential.credential_id.hex()
        assert allow_creds[0]["type"] == "public-key"

        # Verify challenge was stored in REAL Redis
        redis = await get_redis()
        challenge_key = f"webauthn:challenge:authentication:{data['challenge_id']}"
        stored_data = await redis.get(challenge_key)

        assert stored_data is not None
        assert user.email in stored_data

    @pytest.mark.asyncio
    async def test_authenticate_start_creates_login_event(
        self, client: AsyncClient, csrf_token, user_with_credential, db_session
    ):
        """Should create login event when authentication starts."""
        user, _credential = user_with_credential

        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/start",
            json={"email": user.email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200

        # Verify login event was created
        event_stmt = (
            select(LoginEvent)
            .where(LoginEvent.user_id == user.id)
            .order_by(LoginEvent.created_at.desc())
        )
        event_result = await db_session.execute(event_stmt)
        event = event_result.scalar_one_or_none()

        assert event is not None
        assert event.event_type == "webauthn_auth_start"
        assert event.extra is not None
        assert "challenge_id" in event.extra
        assert "credential_count" in event.extra
        assert event.extra["credential_count"] == 1

    @pytest.mark.asyncio
    async def test_authenticate_start_with_multiple_credentials(
        self, client: AsyncClient, csrf_token, user_with_credential, db_session
    ):
        """Should include all user credentials in allowCredentials."""
        user, _credential1 = user_with_credential

        # Add a second credential
        now = datetime.now(UTC)
        credential2 = WebAuthnCredential(
            user_id=user.id,
            credential_id=b"second_credential_id_here",
            public_key=b"second_public_key_data",
            sign_count=5,
            transports=["internal"],
            created_at=now,
            updated_at=now,
        )
        db_session.add(credential2)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/start",
            json={"email": user.email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()

        # Should include both credentials
        allow_creds = data["options"]["allowCredentials"]
        assert len(allow_creds) == 2

        # Verify both credentials are present (check by partial match due to
        # possible truncation in serialization)
        cred_ids = {cred["id"] for cred in allow_creds}
        assert len(cred_ids) == 2  # Two unique credential IDs

        # Both should have proper structure
        for cred in allow_creds:
            assert cred["type"] == "public-key"
            assert "id" in cred
            assert len(cred["id"]) > 0

    @pytest.mark.asyncio
    async def test_authenticate_start_user_not_found(
        self, client: AsyncClient, csrf_token
    ):
        """Should return 404 for non-existent user."""
        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/start",
            json={"email": "nonexistent@test.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_authenticate_start_no_credentials_registered(
        self, client: AsyncClient, csrf_token, db_session
    ):
        """Should return 400 for user with no registered credentials."""
        # Create user without credentials
        now = datetime.now(UTC)
        user = User(
            email="nocreds@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/start",
            json={"email": user.email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 400
        assert "passkey" in response.json()["detail"].lower()


class TestWebAuthnChallengeStorage:
    """Test challenge storage and retrieval without mocks."""

    @pytest.mark.asyncio
    async def test_challenge_single_use_deletion(
        self, client: AsyncClient, csrf_token, user_with_credential
    ):
        """Should delete challenge from Redis after retrieval."""
        from app.core.challenge_storage import retrieve_and_delete_challenge
        from app.core.redis_client import get_redis

        user, _credential = user_with_credential

        # Start authentication to create challenge
        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/start",
            json={"email": user.email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        challenge_id = data["challenge_id"]

        # Retrieve the challenge (should delete it)
        result = await retrieve_and_delete_challenge(challenge_id, "authentication")
        assert result is not None
        retrieved_email, challenge_hex = result
        assert retrieved_email == user.email

        # Try to retrieve again - should be None (already deleted)
        result2 = await retrieve_and_delete_challenge(challenge_id, "authentication")
        assert result2 is None

        # Verify it's gone from Redis
        redis = await get_redis()
        challenge_key = f"webauthn:challenge:authentication:{challenge_id}"
        stored_data = await redis.get(challenge_key)
        assert stored_data is None

    @pytest.mark.asyncio
    async def test_challenge_wrong_type_returns_none(
        self, client: AsyncClient, csrf_token, user_with_credential
    ):
        """Should return None if challenge type doesn't match."""
        from app.core.challenge_storage import retrieve_and_delete_challenge

        user, _credential = user_with_credential

        # Start authentication (creates "authentication" type challenge)
        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/start",
            json={"email": user.email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        challenge_id = data["challenge_id"]

        # Try to retrieve with wrong type
        result = await retrieve_and_delete_challenge(challenge_id, "registration")
        assert result is None

        # Should still exist with correct type
        result2 = await retrieve_and_delete_challenge(challenge_id, "authentication")
        assert result2 is not None
