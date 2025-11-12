"""Tests for user-facing auth endpoints.

Tests for /me, /logout, /webauthn/credentials, and /email/verify endpoints.
"""

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.core.security import create_magic_link_token, create_session_token, hash_token
from app.db.models.auth import MagicLinkToken, Session, User, WebAuthnCredential


@pytest_asyncio.fixture
async def csrf_token(client: AsyncClient):
    """Get CSRF token for requests."""
    response = await client.get("/healthz")
    return response.cookies["csrf_token"]


@pytest_asyncio.fixture
async def verified_user(db_session):
    """Create a verified user."""
    now = datetime.now(UTC)
    user = User(
        email="verified@test.com",
        is_active=True,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def user_with_session(db_session, verified_user):
    """Create user with active session."""
    now = datetime.now(UTC)
    session_token = create_session_token()
    session = Session(
        user_id=verified_user.id,
        token_hash=hash_token(session_token),
        created_at=now,
        expires_at=now + timedelta(hours=336),
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return verified_user, session_token


@pytest_asyncio.fixture
async def user_with_credentials(db_session, verified_user):
    """Create user with multiple WebAuthn credentials."""
    now = datetime.now(UTC)
    credentials = []
    for i in range(3):
        cred = WebAuthnCredential(
            user_id=verified_user.id,
            credential_id=bytes.fromhex(f"{'0' * (i * 2)}{'1' * (16 - i * 2)}"),
            public_key=f"public_key_{i}".encode(),
            sign_count=i,
            transports=["internal"],
            nickname=f"Device {i + 1}" if i > 0 else None,
            created_at=now,
            updated_at=now,
        )
        db_session.add(cred)
        credentials.append(cred)

    await db_session.commit()
    for cred in credentials:
        await db_session.refresh(cred)

    return verified_user, credentials


class TestMeEndpoint:
    """Tests for GET /api/v1/auth/me endpoint."""

    @pytest.mark.asyncio
    async def test_me_authenticated_user(
        self, client: AsyncClient, csrf_token, user_with_session
    ):
        """Should return user info for authenticated user."""
        user, session_token = user_with_session

        response = await client.get(
            "/api/v1/auth/me",
            cookies={"ff_sess": session_token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user.email
        assert data["is_email_verified"] is True
        assert "session_created_at" in data
        assert "session_expires_at" in data

    @pytest.mark.asyncio
    async def test_me_unauthenticated(self, client: AsyncClient, csrf_token):
        """Should reject unauthenticated request."""
        response = await client.get(
            "/api/v1/auth/me",
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 401


class TestLogoutEndpoint:
    """Tests for POST /api/v1/auth/logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_revokes_session(
        self, client: AsyncClient, csrf_token, user_with_session, db_session
    ):
        """Should revoke session and clear cookie."""
        user, session_token = user_with_session

        response = await client.post(
            "/api/v1/auth/logout",
            cookies={"csrf_token": csrf_token},
            headers={
                "X-CSRF-Token": csrf_token,
                "Authorization": f"Bearer {session_token}",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "logged out" in data["message"].lower()

        # Verify session was revoked in database
        from sqlalchemy import select

        stmt = select(Session).where(Session.token_hash == hash_token(session_token))
        result = await db_session.execute(stmt)
        session = result.scalar_one_or_none()
        assert session is not None
        assert session.revoked_at is not None

    @pytest.mark.asyncio
    async def test_logout_unauthenticated_still_succeeds(
        self, client: AsyncClient, csrf_token
    ):
        """Should return 200 even when not authenticated (idempotent)."""
        response = await client.post(
            "/api/v1/auth/logout",
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_logout_already_logged_out(
        self, client: AsyncClient, csrf_token, user_with_session
    ):
        """Should handle double logout gracefully (idempotent)."""
        user, session_token = user_with_session

        # First logout
        response1 = await client.post(
            "/api/v1/auth/logout",
            cookies={"csrf_token": csrf_token},
            headers={
                "X-CSRF-Token": csrf_token,
                "Authorization": f"Bearer {session_token}",
            },
        )
        assert response1.status_code == 200

        # Second logout with same token (should still succeed)
        response2 = await client.post(
            "/api/v1/auth/logout",
            cookies={"csrf_token": csrf_token},
            headers={
                "X-CSRF-Token": csrf_token,
                "Authorization": f"Bearer {session_token}",
            },
        )
        assert response2.status_code == 200


class TestCredentialListEndpoint:
    """Tests for GET /api/v1/auth/webauthn/credentials endpoint."""

    @pytest.mark.asyncio
    async def test_list_credentials_success(
        self, client: AsyncClient, csrf_token, user_with_credentials, db_session
    ):
        """Should list user's credentials without exposing public keys."""
        user, credentials = user_with_credentials

        # Create session for user
        now = datetime.now(UTC)
        session_token = create_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(session_token),
            created_at=now,
            expires_at=now + timedelta(hours=336),
        )
        db_session.add(session)
        await db_session.commit()

        response = await client.get(
            "/api/v1/auth/webauthn/credentials",
            cookies={"csrf_token": csrf_token},
            headers={
                "X-CSRF-Token": csrf_token,
                "Authorization": f"Bearer {session_token}",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3

        # Verify public keys are not exposed and correct fields present
        for cred_data in data:
            assert "public_key" not in cred_data
            assert "id" in cred_data  # credential_id as hex string
            assert "created_at" in cred_data
            assert "nickname" in cred_data
            assert "last_used_at" in cred_data

    @pytest.mark.asyncio
    async def test_list_credentials_empty(
        self, client: AsyncClient, csrf_token, verified_user, db_session
    ):
        """Should return empty list for user with no credentials."""
        # Create session
        now = datetime.now(UTC)
        session_token = create_session_token()
        session = Session(
            user_id=verified_user.id,
            token_hash=hash_token(session_token),
            created_at=now,
            expires_at=now + timedelta(hours=336),
        )
        db_session.add(session)
        await db_session.commit()

        response = await client.get(
            "/api/v1/auth/webauthn/credentials",
            cookies={"csrf_token": csrf_token},
            headers={
                "X-CSRF-Token": csrf_token,
                "Authorization": f"Bearer {session_token}",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


class TestEmailVerifyEndpoint:
    """Tests for POST /api/v1/auth/email/verify endpoint."""

    @pytest.mark.asyncio
    async def test_verify_email_success(
        self, client: AsyncClient, csrf_token, db_session
    ):
        """Should verify email with valid token."""
        # Create unverified user
        now = datetime.now(UTC)
        user = User(
            email="unverified@test.com",
            is_active=True,
            is_email_verified=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create verification token
        token_value = create_magic_link_token()
        verification_token = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token_value),
            purpose="email_verification",
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )
        db_session.add(verification_token)
        await db_session.commit()

        # Verify email
        response = await client.post(
            "/api/v1/auth/email/verify",
            json={"token": token_value},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "verified" in data["message"].lower()

        # Check user is now verified
        await db_session.refresh(user)
        assert user.is_email_verified is True

    @pytest.mark.asyncio
    async def test_verify_email_already_verified_idempotent(
        self, client: AsyncClient, csrf_token, db_session
    ):
        """Should handle already verified email gracefully (idempotent)."""
        # Create verified user
        now = datetime.now(UTC)
        user = User(
            email="alreadyverified@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create verification token
        token_value = create_magic_link_token()
        verification_token = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token_value),
            purpose="email_verification",
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )
        db_session.add(verification_token)
        await db_session.commit()

        # Verify again
        response = await client.post(
            "/api/v1/auth/email/verify",
            json={"token": token_value},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Should succeed (idempotent)
        assert response.status_code == 200
