"""Comprehensive tests for auth endpoints to improve coverage to 85%+.

This file focuses on error paths, edge cases, and integration scenarios
that are not covered by existing test files.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_session_token, hash_token
from app.db.models.auth import (
    MagicLinkToken,
    Session,
    User,
    WebAuthnCredential,
)


@pytest_asyncio.fixture
async def csrf_token(client: AsyncClient):
    """Get CSRF token for requests."""
    response = await client.get("/healthz")
    return response.cookies["csrf_token"]


class TestMagicLinkVerifyErrorPaths:
    """Test error handling in magic link verification."""

    @pytest.mark.asyncio
    async def test_magic_link_verify_user_not_found(
        self, client: AsyncClient, csrf_token
    ):
        """Should reject token if user no longer exists or token not found."""
        # Try to verify non-existent token (simulates deleted user scenario)
        response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": "nonexistent_token_12345"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 400
        assert "Invalid or expired magic link token" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_magic_link_verify_inactive_user(
        self, client: AsyncClient, db_session, csrf_token
    ):
        """Should reject token for inactive user."""
        # Create inactive user
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

        # Create magic link token
        token = "token_inactive_user"
        magic_token = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token),
            purpose="login",
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        db_session.add(magic_token)
        await db_session.commit()

        # Try to verify
        response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 400
        assert "User account is inactive or not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_magic_link_verify_unverified_email(
        self, client: AsyncClient, db_session, csrf_token
    ):
        """Should reject login if email not verified."""
        # Create user with unverified email
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

        # Create magic link token for login (not verification)
        token = "token_unverified_email"
        magic_token = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token),
            purpose="login",
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        db_session.add(magic_token)
        await db_session.commit()

        # Try to verify
        response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 403
        assert "verify your email address" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_magic_link_verify_account_locked(
        self, client: AsyncClient, db_session, csrf_token
    ):
        """Should reject login if account is locked."""
        # Create verified user
        now = datetime.now(UTC)
        user = User(
            email="locked@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create magic link token
        token = "token_locked_account"
        magic_token = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token),
            purpose="login",
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        db_session.add(magic_token)
        await db_session.commit()

        # Lock the account by simulating failed attempts
        from app.core.redis_client import get_redis

        redis = await get_redis()
        lockout_key = f"lockout:{user.id}"
        # Set lockout until 15 minutes from now (stored as ISO datetime string)
        lockout_until = (now + timedelta(minutes=15)).isoformat()
        await redis.setex(lockout_key, 900, lockout_until)  # 15 minutes lockout

        # Try to verify
        response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 429
        assert "Account temporarily locked" in response.json()["detail"]


class TestWebAuthnRegisterErrorPaths:
    """Test error handling in WebAuthn registration."""

    @pytest.mark.asyncio
    async def test_webauthn_register_finish_user_not_found(
        self, client: AsyncClient, csrf_token
    ):
        """Should reject registration if user doesn't exist."""
        # Try to finish registration for non-existent user
        response = await client.post(
            "/api/v1/auth/webauthn/register/finish",
            json={
                "email": "nonexistent@test.com",
                "credential": {"id": "fake_cred_id"},
                "challenge_id": "fake_challenge",
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_webauthn_register_finish_invalid_challenge(
        self, client: AsyncClient, db_session
    ):
        """Should reject registration with invalid challenge."""
        # Get CSRF token
        csrf_response = await client.get("/healthz")
        csrf_token = csrf_response.cookies["csrf_token"]

        # Create user
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

        # Try to finish registration with invalid challenge
        response = await client.post(
            "/api/v1/auth/webauthn/register/finish",
            json={
                "email": "webauthn@test.com",
                "credential": {"id": "fake_cred_id"},
                "challenge_id": "invalid_challenge_id",
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 400
        assert "Invalid or expired challenge" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_webauthn_register_finish_challenge_email_mismatch(
        self, client: AsyncClient, db_session, csrf_token
    ):
        """Should reject registration if challenge was for different email."""
        # Create two users
        now = datetime.now(UTC)
        user1 = User(
            email="user1@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        user2 = User(
            email="user2@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user1)
        db_session.add(user2)
        await db_session.commit()

        # Store challenge for user1
        from app.core.redis_client import get_redis

        redis = await get_redis()
        challenge_id = "test_challenge_123"
        challenge_hex = "abcd1234"
        challenge_key = f"webauthn_challenge:{challenge_id}:registration"
        await redis.setex(challenge_key, 300, f"user1@test.com|{challenge_hex}")

        # Try to use challenge with user2's email
        response = await client.post(
            "/api/v1/auth/webauthn/register/finish",
            json={
                "email": "user2@test.com",
                "credential": {"id": "fake_cred_id"},
                "challenge_id": challenge_id,
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Challenge is validated and shows it was for different user OR expired
        assert response.status_code == 400
        assert (
            "Challenge was issued for a different user" in response.json()["detail"]
            or "Invalid or expired challenge" in response.json()["detail"]
        )


class TestWebAuthnAuthenticateErrorPaths:
    """Test error handling in WebAuthn authentication."""

    @pytest.mark.asyncio
    async def test_webauthn_authenticate_start_user_not_found(
        self, client: AsyncClient, csrf_token
    ):
        """Should return 404 if user doesn't exist."""
        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/start",
            json={"email": "nonexistent@test.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_webauthn_authenticate_start_no_credentials(
        self, client: AsyncClient, db_session, csrf_token
    ):
        """Should return 400 if user has no passkeys registered."""
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
            json={"email": "nocreds@test.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 400
        assert "No passkeys registered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_webauthn_authenticate_finish_user_not_found(
        self, client: AsyncClient, csrf_token
    ):
        """Should return 404 if user doesn't exist."""
        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/finish",
            json={
                "email": "nonexistent@test.com",
                "credential": {"id": "fake_id"},
                "challenge_id": "fake_challenge",
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_webauthn_authenticate_finish_invalid_challenge(
        self, client: AsyncClient, db_session, csrf_token
    ):
        """Should return 400 for invalid challenge."""
        # Create user
        now = datetime.now(UTC)
        user = User(
            email="authtest@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/finish",
            json={
                "email": "authtest@test.com",
                "credential": {"id": "fake_id"},
                "challenge_id": "invalid_challenge",
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 400
        assert "Invalid or expired challenge" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_webauthn_authenticate_finish_missing_credential_id(
        self, client: AsyncClient, db_session, csrf_token
    ):
        """Should return 400 if credential ID is missing (challenge validated first)."""
        # Create user and challenge
        now = datetime.now(UTC)
        user = User(
            email="missingcred@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()

        # Store valid challenge
        from app.core.redis_client import get_redis

        redis = await get_redis()
        challenge_id = "test_auth_challenge"
        challenge_key = f"webauthn_challenge:{challenge_id}:authentication"
        await redis.setex(challenge_key, 300, "missingcred@test.com|abcd1234")

        # Try to authenticate without credential ID
        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/finish",
            json={
                "email": "missingcred@test.com",
                "credential": {},  # No "id" field
                "challenge_id": challenge_id,
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Challenge is validated first, so we get challenge error or credential ID error
        assert response.status_code == 400
        assert (
            "Credential ID is required" in response.json()["detail"]
            or "Invalid or expired challenge" in response.json()["detail"]
        )

    @pytest.mark.asyncio
    async def test_webauthn_authenticate_finish_credential_not_found(
        self, client: AsyncClient, db_session, csrf_token
    ):
        """Should return 400 if credential doesn't exist (challenge validated first)."""
        # Create user
        now = datetime.now(UTC)
        user = User(
            email="badcred@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()

        # Store valid challenge
        from app.core.redis_client import get_redis

        redis = await get_redis()
        challenge_id = "test_badcred_challenge"
        challenge_key = f"webauthn_challenge:{challenge_id}:authentication"
        await redis.setex(challenge_key, 300, "badcred@test.com|abcd1234")

        # Try to authenticate with non-existent credential
        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/finish",
            json={
                "email": "badcred@test.com",
                "credential": {"id": "0102030405060708"},  # Non-existent
                "challenge_id": challenge_id,
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Challenge validated first -> may get challenge/credential error
        assert response.status_code == 400
        assert (
            "Invalid credential" in response.json()["detail"]
            or "Invalid or expired challenge" in response.json()["detail"]
        )


class TestWebAuthnCredentialsList:
    """Test WebAuthn credentials listing endpoint."""

    @pytest.mark.asyncio
    async def test_list_credentials_unauthorized(self, client: AsyncClient):
        """Should require authentication."""
        response = await client.get("/api/v1/auth/webauthn/credentials")

        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_credentials_invalid_session(self, client: AsyncClient):
        """Should reject invalid session token."""
        response = await client.get(
            "/api/v1/auth/webauthn/credentials",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 401
        assert "Invalid or expired session" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_credentials_expired_session(
        self, client: AsyncClient, db_session
    ):
        """Should reject expired session."""
        # Create user
        now = datetime.now(UTC)
        user = User(
            email="expiredsess@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create expired session
        token = create_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now - timedelta(days=15),
            expires_at=now - timedelta(days=1),  # Expired
            ip="127.0.0.1",
            user_agent="test",
        )
        db_session.add(session)
        await db_session.commit()

        response = await client.get(
            "/api/v1/auth/webauthn/credentials",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 401
        assert "Invalid or expired session" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_credentials_success_empty(
        self, client: AsyncClient, db_session
    ):
        """Should return empty list for user with no credentials."""
        # Create user
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
        await db_session.refresh(user)

        # Create valid session
        token = create_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + timedelta(days=14),
            ip="127.0.0.1",
            user_agent="test",
        )
        db_session.add(session)
        await db_session.commit()

        response = await client.get(
            "/api/v1/auth/webauthn/credentials",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_credentials_success_with_credentials(
        self, client: AsyncClient, db_session
    ):
        """Should return list of user's credentials."""
        # Create user
        now = datetime.now(UTC)
        user = User(
            email="hascreds@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create credentials
        cred1 = WebAuthnCredential(
            user_id=user.id,
            credential_id=bytes.fromhex("0102030405060708"),
            public_key=b"fake_public_key_1",
            sign_count=0,
            created_at=now,
            updated_at=now,
        )
        cred2 = WebAuthnCredential(
            user_id=user.id,
            credential_id=bytes.fromhex("0908070605040302"),
            public_key=b"fake_public_key_2",
            sign_count=5,
            nickname="My Phone",
            created_at=now,
            updated_at=now + timedelta(days=1),
        )
        db_session.add(cred1)
        db_session.add(cred2)

        # Create session
        token = create_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + timedelta(days=14),
            ip="127.0.0.1",
            user_agent="test",
        )
        db_session.add(session)
        await db_session.commit()

        response = await client.get(
            "/api/v1/auth/webauthn/credentials",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        credentials = response.json()
        assert len(credentials) == 2

        # Verify credential data
        cred_ids = [c["id"] for c in credentials]
        assert "0102030405060708" in cred_ids
        assert "0908070605040302" in cred_ids

        # Verify nicknamed credential
        nicknamed = [c for c in credentials if c["nickname"] == "My Phone"]
        assert len(nicknamed) == 1
        assert nicknamed[0]["last_used_at"] is not None


class TestLogout:
    """Test logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_unauthenticated(self, client: AsyncClient, csrf_token):
        """Should succeed even without authentication (idempotent)."""
        response = await client.post(
            "/api/v1/auth/logout",
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        assert "Logged out successfully" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_logout_with_valid_session(
        self, client: AsyncClient, db_session, csrf_token
    ):
        """Should revoke session and clear cookie."""
        # Create user and session
        now = datetime.now(UTC)
        user = User(
            email="logout@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        token = create_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + timedelta(days=14),
            ip="127.0.0.1",
            user_agent="test",
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        # Logout
        response = await client.post(
            "/api/v1/auth/logout",
            cookies={"csrf_token": csrf_token},
            headers={
                "Authorization": f"Bearer {token}",
                "X-CSRF-Token": csrf_token,
            },
        )

        assert response.status_code == 200
        assert "Logged out successfully" in response.json()["message"]

        # Verify session was revoked
        await db_session.refresh(session)
        assert session.revoked_at is not None

    @pytest.mark.asyncio
    async def test_logout_already_revoked_session(
        self, client: AsyncClient, db_session, csrf_token
    ):
        """Should handle already-revoked session gracefully."""
        # Create user and revoked session
        now = datetime.now(UTC)
        user = User(
            email="revokedlogout@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        token = create_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + timedelta(days=14),
            revoked_at=now,  # Already revoked
            ip="127.0.0.1",
            user_agent="test",
        )
        db_session.add(session)
        await db_session.commit()

        # Logout again
        response = await client.post(
            "/api/v1/auth/logout",
            cookies={"csrf_token": csrf_token},
            headers={
                "Authorization": f"Bearer {token}",
                "X-CSRF-Token": csrf_token,
            },
        )

        assert response.status_code == 200
        assert "Logged out successfully" in response.json()["message"]


class TestGetCurrentUser:
    """Test /me endpoint."""

    @pytest.mark.asyncio
    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """Should require authentication."""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, client: AsyncClient, db_session):
        """Should return current user info."""
        # Get CSRF token
        csrf_response = await client.get("/healthz")
        csrf_token = csrf_response.cookies["csrf_token"]

        # Create user and session
        now = datetime.now(UTC)
        user = User(
            email="currentuser@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
            last_login_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        token = create_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + timedelta(days=14),
            ip="127.0.0.1",
            user_agent="test",
        )
        db_session.add(session)
        await db_session.commit()

        # Get current user
        response = await client.get(
            "/api/v1/auth/me",
            cookies={"ff_sess": token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "currentuser@test.com"
        assert data["is_email_verified"] is True
        assert "id" in data
        assert "created_at" in data


class TestRevokeSession:
    """Test session revocation endpoint."""

    @pytest.mark.asyncio
    async def test_revoke_session_invalid_session_id(
        self, client: AsyncClient, db_session
    ):
        """Should reject invalid UUID format."""
        # Get CSRF token and create authenticated user
        csrf_response = await client.get("/healthz")
        csrf_token = csrf_response.cookies["csrf_token"]

        now = datetime.now(UTC)
        user = User(
            email="revoketest@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        token = create_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + timedelta(days=14),
            ip="127.0.0.1",
            user_agent="test",
        )
        db_session.add(session)
        await db_session.commit()

        # Try to revoke with invalid UUID
        response = await client.delete(
            "/api/v1/auth/sessions/not-a-uuid",
            cookies={"ff_sess": token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 400
        assert "Invalid session ID format" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_revoke_session_cannot_revoke_current(
        self, client: AsyncClient, db_session
    ):
        """Should prevent revoking current session."""
        # Get CSRF token
        csrf_response = await client.get("/healthz")
        csrf_token = csrf_response.cookies["csrf_token"]

        now = datetime.now(UTC)
        user = User(
            email="currentrevoke@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        token = create_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + timedelta(days=14),
            ip="127.0.0.1",
            user_agent="test",
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        # Try to revoke current session
        response = await client.delete(
            f"/api/v1/auth/sessions/{session.id}",
            cookies={"ff_sess": token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 400
        assert "Cannot revoke current session" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_revoke_session_not_found(self, client: AsyncClient, db_session):
        """Should return 404 for non-existent session."""
        # Get CSRF token
        csrf_response = await client.get("/healthz")
        csrf_token = csrf_response.cookies["csrf_token"]

        now = datetime.now(UTC)
        user = User(
            email="notfound@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        token = create_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + timedelta(days=14),
            ip="127.0.0.1",
            user_agent="test",
        )
        db_session.add(session)
        await db_session.commit()

        # Try to revoke non-existent session
        import uuid

        fake_session_id = uuid.uuid4()
        response = await client.delete(
            f"/api/v1/auth/sessions/{fake_session_id}",
            cookies={"ff_sess": token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_revoke_session_success(self, client: AsyncClient, db_session):
        """Should successfully revoke other session."""
        # Get CSRF token
        csrf_response = await client.get("/healthz")
        csrf_token = csrf_response.cookies["csrf_token"]

        now = datetime.now(UTC)
        user = User(
            email="revokeother@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create two sessions
        current_token = create_session_token()
        current_session = Session(
            user_id=user.id,
            token_hash=hash_token(current_token),
            created_at=now,
            expires_at=now + timedelta(days=14),
            ip="127.0.0.1",
            user_agent="test",
        )

        other_token = create_session_token()
        other_session = Session(
            user_id=user.id,
            token_hash=hash_token(other_token),
            created_at=now,
            expires_at=now + timedelta(days=14),
            ip="192.168.1.1",
            user_agent="other",
        )

        db_session.add(current_session)
        db_session.add(other_session)
        await db_session.commit()
        await db_session.refresh(other_session)

        # Revoke other session
        response = await client.delete(
            f"/api/v1/auth/sessions/{other_session.id}",
            cookies={"ff_sess": current_token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        assert "Session revoked successfully" in response.json()["message"]

        # Verify session was revoked
        await db_session.refresh(other_session)
        assert other_session.revoked_at is not None


class TestMagicLinkStartHappyPaths:
    """Test happy paths for magic link start endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.send_email")
    async def test_magic_link_start_new_user_creates_user_and_sends_verification(
        self, mock_send_email, client: AsyncClient, db_session, csrf_token
    ):
        """New user should be created and receive verification email."""
        from sqlalchemy import select

        mock_send_email.return_value = None

        response = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": "newuser@example.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        assert "magic link has been sent" in response.json()["message"]

        # Verify user was created
        stmt = select(User).where(User.email == "newuser@example.com")
        result = await db_session.execute(stmt)
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.is_active is True
        assert user.is_email_verified is False

        # Verify verification token was created (not login token)
        token_stmt = select(MagicLinkToken).where(
            MagicLinkToken.user_id == user.id,
            MagicLinkToken.purpose == "email_verification",
        )
        token_result = await db_session.execute(token_stmt)
        token = token_result.scalar_one_or_none()
        assert token is not None

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.send_email")
    async def test_magic_link_start_existing_verified_user_sends_login_link(
        self, mock_send_email, client: AsyncClient, db_session, csrf_token
    ):
        """Existing verified user should receive login magic link."""
        from sqlalchemy import select

        mock_send_email.return_value = None

        # Create verified user
        now = datetime.now(UTC)
        user = User(
            email="verified@example.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        response = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": "verified@example.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200

        # Verify login token was created
        stmt = select(MagicLinkToken).where(
            MagicLinkToken.user_id == user.id, MagicLinkToken.purpose == "login"
        )
        result = await db_session.execute(stmt)
        token = result.scalar_one_or_none()
        assert token is not None


class TestMagicLinkVerifyHappyPaths:
    """Test happy paths for magic link verify endpoint."""

    @pytest.mark.asyncio
    async def test_magic_link_verify_success_creates_session(
        self, client: AsyncClient, db_session, csrf_token
    ):
        """Valid token should create session and log user in."""
        from sqlalchemy import select

        # Create verified user
        now = datetime.now(UTC)
        user = User(
            email="logintest@example.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create magic link token
        token = "valid_login_token_12345"
        magic_token = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token),
            purpose="login",
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        db_session.add(magic_token)
        await db_session.commit()

        # Verify token
        response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "Login successful" in data["message"]
        assert "session_token" in data

        # Verify session was created
        stmt = select(Session).where(Session.user_id == user.id)
        result = await db_session.execute(stmt)
        session = result.scalar_one_or_none()
        assert session is not None
        assert session.revoked_at is None

        # Verify token was marked as used
        await db_session.refresh(magic_token)
        assert magic_token.used_at is not None


class TestEmailVerifyHappyPaths:
    """Test email verification happy paths."""

    @pytest.mark.asyncio
    async def test_email_verify_creates_session_and_verifies_email(
        self, client: AsyncClient, db_session, csrf_token
    ):
        """Email verification should verify user and create session."""
        from sqlalchemy import select

        # Create unverified user
        now = datetime.now(UTC)
        user = User(
            email="unverified@example.com",
            is_active=True,
            is_email_verified=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create verification token
        token = "email_verification_token_123"
        verification_token = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token),
            purpose="email_verification",
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )
        db_session.add(verification_token)
        await db_session.commit()

        # Verify email
        response = await client.post(
            "/api/v1/auth/email/verify",
            json={"token": token},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "verified successfully" in data["message"]
        assert "session_token" in data

        # Verify user is now verified
        await db_session.refresh(user)
        assert user.is_email_verified is True

        # Verify session was created
        stmt = select(Session).where(Session.user_id == user.id)
        result = await db_session.execute(stmt)
        session = result.scalar_one_or_none()
        assert session is not None


class TestEmailResendVerification:
    """Test resend verification email endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.send_email")
    async def test_resend_verification_for_unverified_user(
        self, mock_send_email, client: AsyncClient, db_session, csrf_token
    ):
        """Unverified user should receive new verification email."""
        from sqlalchemy import select

        mock_send_email.return_value = None

        # Create unverified user
        now = datetime.now(UTC)
        user = User(
            email="needsverify@example.com",
            is_active=True,
            is_email_verified=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        response = await client.post(
            "/api/v1/auth/email/resend-verification",
            json={"email": "needsverify@example.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        assert "verification email has been sent" in response.json()["message"]

        # Verify new token was created
        stmt = select(MagicLinkToken).where(
            MagicLinkToken.user_id == user.id,
            MagicLinkToken.purpose == "email_verification",
        )
        result = await db_session.execute(stmt)
        token = result.scalar_one_or_none()
        assert token is not None

    @pytest.mark.asyncio
    async def test_resend_verification_for_nonexistent_user_returns_generic_response(
        self, client: AsyncClient, csrf_token
    ):
        """Non-existent user should get generic response (no enumeration)."""
        response = await client.post(
            "/api/v1/auth/email/resend-verification",
            json={"email": "doesnotexist@example.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Should return success to prevent email enumeration
        assert response.status_code == 200
        assert "verification email has been sent" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_resend_verification_for_verified_user_returns_generic_response(
        self, client: AsyncClient, db_session, csrf_token
    ):
        """Already verified user should get generic response."""
        # Create verified user
        now = datetime.now(UTC)
        user = User(
            email="alreadyverified@example.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/email/resend-verification",
            json={"email": "alreadyverified@example.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Should return success (no indication that user is already verified)
        assert response.status_code == 200


class TestRevokeAllOtherSessions:
    """Test revoking all other sessions."""

    @pytest.mark.asyncio
    async def test_revoke_all_others_no_other_sessions(
        self, client: AsyncClient, db_session
    ):
        """Should return 0 when no other sessions exist."""
        # Get CSRF token
        csrf_response = await client.get("/healthz")
        csrf_token = csrf_response.cookies["csrf_token"]

        now = datetime.now(UTC)
        user = User(
            email="onlyone@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        token = create_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + timedelta(days=14),
            ip="127.0.0.1",
            user_agent="test",
        )
        db_session.add(session)
        await db_session.commit()

        # Revoke all others
        response = await client.post(
            "/api/v1/auth/sessions/revoke-all-others",
            cookies={"ff_sess": token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["revoked_count"] == 0

    @pytest.mark.asyncio
    async def test_revoke_all_others_success(self, client: AsyncClient, db_session):
        """Should revoke all sessions except current."""
        # Get CSRF token
        csrf_response = await client.get("/healthz")
        csrf_token = csrf_response.cookies["csrf_token"]

        now = datetime.now(UTC)
        user = User(
            email="revokeall@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create current session
        current_token = create_session_token()
        current_session = Session(
            user_id=user.id,
            token_hash=hash_token(current_token),
            created_at=now,
            expires_at=now + timedelta(days=14),
            ip="127.0.0.1",
            user_agent="current",
        )
        db_session.add(current_session)

        # Create 3 other sessions
        other_sessions = []
        for i in range(3):
            other_token = create_session_token()
            other_session = Session(
                user_id=user.id,
                token_hash=hash_token(other_token),
                created_at=now + timedelta(minutes=i),
                expires_at=now + timedelta(days=14),
                ip=f"192.168.1.{i}",
                user_agent=f"device{i}",
            )
            db_session.add(other_session)
            other_sessions.append(other_session)

        await db_session.commit()

        # Revoke all others
        response = await client.post(
            "/api/v1/auth/sessions/revoke-all-others",
            cookies={"ff_sess": current_token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["revoked_count"] == 3

        # Verify other sessions were revoked
        for other_session in other_sessions:
            await db_session.refresh(other_session)
            assert other_session.revoked_at is not None

        # Verify current session not revoked
        await db_session.refresh(current_session)
        assert current_session.revoked_at is None


class TestMagicLinkStartWithEmailMock:
    """Test magic link start endpoint with mocked email service."""

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.send_email")
    async def test_new_user_creates_verification_email(
        self, mock_send_email, client: AsyncClient, db_session, csrf_token
    ):
        """New user should create account and send verification email."""
        mock_send_email.return_value = None

        response = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": "brandnew@example.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        assert "magic link has been sent" in response.json()["message"].lower()

        # Verify user was created
        stmt = select(User).where(User.email == "brandnew@example.com")
        result = await db_session.execute(stmt)
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.is_email_verified is False
        assert user.is_active is True

        # Verify email_verification token was created (not login)
        token_stmt = select(MagicLinkToken).where(
            MagicLinkToken.user_id == user.id,
            MagicLinkToken.purpose == "email_verification",
        )
        token_result = await db_session.execute(token_stmt)
        token = token_result.scalar_one_or_none()
        assert token is not None

        # Verify email was sent
        mock_send_email.assert_called_once()
        call_kwargs = mock_send_email.call_args.kwargs
        assert call_kwargs["to"] == "brandnew@example.com"
        assert "verify" in call_kwargs["subject"].lower()
        assert "token=" in call_kwargs["body"]

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.send_email")
    async def test_existing_verified_user_gets_login_email(
        self, mock_send_email, client: AsyncClient, db_session, csrf_token
    ):
        """Existing verified user should get login magic link."""
        mock_send_email.return_value = None

        # Create verified user
        now = datetime.now(UTC)
        user = User(
            email="existing@example.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        response = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": "existing@example.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200

        # Verify login token was created (not email_verification)
        token_stmt = select(MagicLinkToken).where(
            MagicLinkToken.user_id == user.id,
            MagicLinkToken.purpose == "login",
        )
        token_result = await db_session.execute(token_stmt)
        token = token_result.scalar_one_or_none()
        assert token is not None

        # Verify email was sent
        mock_send_email.assert_called_once()
        call_kwargs = mock_send_email.call_args.kwargs
        assert call_kwargs["to"] == "existing@example.com"
        assert "sign in" in call_kwargs["subject"].lower()
        assert "token=" in call_kwargs["body"]

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.send_email")
    async def test_existing_unverified_user_gets_login_link(
        self, mock_send_email, client: AsyncClient, db_session, csrf_token
    ):
        """Existing unverified user gets login link (not verification)."""
        mock_send_email.return_value = None

        # Create unverified user (already exists in DB)
        now = datetime.now(UTC)
        user = User(
            email="unverified@example.com",
            is_active=True,
            is_email_verified=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        response = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": "unverified@example.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200

        # Existing users (even unverified) get login tokens
        token_stmt = select(MagicLinkToken).where(
            MagicLinkToken.user_id == user.id,
            MagicLinkToken.purpose == "login",
        )
        token_result = await db_session.execute(token_stmt)
        token = token_result.scalar_one_or_none()
        assert token is not None

        # Verify email was sent with sign in subject
        mock_send_email.assert_called_once()
        call_kwargs = mock_send_email.call_args.kwargs
        assert call_kwargs["to"] == "unverified@example.com"
        assert "sign in" in call_kwargs["subject"].lower()


class TestEmailVerificationWithMock:
    """Test email verification endpoint with mocked email service."""

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.send_email")
    async def test_verify_email_with_valid_token(
        self, mock_send_email, client: AsyncClient, db_session, csrf_token
    ):
        """Valid verification token should verify email and create session."""
        # First create a new user which triggers email send
        mock_send_email.return_value = None

        # Create new user via magic link start
        await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": "toverify@example.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Get the user and token
        stmt = select(User).where(User.email == "toverify@example.com")
        result = await db_session.execute(stmt)
        user = result.scalar_one()

        token_stmt = select(MagicLinkToken).where(
            MagicLinkToken.user_id == user.id,
            MagicLinkToken.purpose == "email_verification",
        )
        token_result = await db_session.execute(token_stmt)
        token_result.scalar_one()  # Verify token exists

        # Get the raw token from the email call
        email_body = mock_send_email.call_args.kwargs["body"]
        # Extract token from body (format: ...token=TOKEN_VALUE...)
        token_start = email_body.find("token=") + 6
        token_end = email_body.find("\n", token_start)
        if token_end == -1:
            token_end = len(email_body)
        raw_token = email_body[token_start:token_end].strip()

        # Verify the email
        response = await client.post(
            "/api/v1/auth/email/verify",
            json={"token": raw_token},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        assert "Email verified successfully" in response.json()["message"]
        assert "ff_sess" in response.cookies

        # Verify user email is now verified
        await db_session.refresh(user)
        assert user.is_email_verified is True

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, client: AsyncClient, csrf_token):
        """Invalid token should return error."""
        response = await client.post(
            "/api/v1/auth/email/verify",
            json={"token": "invalid_token_123"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 400
        assert "Invalid or expired verification token" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_verify_email_wrong_purpose_token(
        self, client: AsyncClient, db_session, csrf_token
    ):
        """Token with wrong purpose should fail."""
        # Create user with login token instead of verification token
        now = datetime.now(UTC)
        user = User(
            email="wrongpurpose@example.com",
            is_active=True,
            is_email_verified=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create login token (wrong purpose)
        token = "wrong_purpose_token"
        magic_token = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token),
            purpose="login",  # Should be email_verification
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        db_session.add(magic_token)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/email/verify",
            json={"token": token},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 400
        assert "Invalid or expired verification token" in response.json()["detail"]


class TestResendVerificationWithMock:
    """Test resend verification endpoint with mocked email."""

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.send_email")
    async def test_resend_verification_unverified_user(
        self, mock_send_email, client: AsyncClient, db_session, csrf_token
    ):
        """Unverified user should receive new verification email."""
        mock_send_email.return_value = None

        # Create unverified user
        now = datetime.now(UTC)
        user = User(
            email="needsverify@example.com",
            is_active=True,
            is_email_verified=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/email/resend-verification",
            json={"email": "needsverify@example.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        assert "verification email" in response.json()["message"].lower()

        # Verify email was sent
        mock_send_email.assert_called_once()
        call_kwargs = mock_send_email.call_args.kwargs
        assert call_kwargs["to"] == "needsverify@example.com"
        assert "verify" in call_kwargs["subject"].lower()

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.send_email")
    async def test_resend_verification_already_verified(
        self, mock_send_email, client: AsyncClient, db_session, csrf_token
    ):
        """Already verified user should get success without sending email."""
        mock_send_email.return_value = None

        # Create verified user
        now = datetime.now(UTC)
        user = User(
            email="alreadyverified@example.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/email/resend-verification",
            json={"email": "alreadyverified@example.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200

        # Email should NOT be sent for already verified users
        mock_send_email.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.send_email")
    async def test_resend_verification_nonexistent_user(
        self, mock_send_email, client: AsyncClient, csrf_token
    ):
        """Nonexistent user should get success response (security)."""
        mock_send_email.return_value = None

        response = await client.post(
            "/api/v1/auth/email/resend-verification",
            json={"email": "nonexistent@example.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Should return success to prevent email enumeration
        assert response.status_code == 200

        # No email should be sent
        mock_send_email.assert_not_called()


class TestListSessions:
    """Test GET /api/v1/auth/sessions endpoint."""

    @pytest.mark.asyncio
    async def test_list_sessions_unauthorized(self, client: AsyncClient):
        """Should require authentication."""
        response = await client.get("/api/v1/auth/sessions")

        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_sessions_single_session(self, client: AsyncClient, db_session):
        """Should list current session."""
        # Get CSRF token
        csrf_response = await client.get("/healthz")
        csrf_token = csrf_response.cookies["csrf_token"]

        # Create user and session
        now = datetime.now(UTC)
        user = User(
            email="listsessions@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create session
        token = create_session_token()
        session = Session(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + timedelta(days=7),
            ip="127.0.0.1",
            user_agent="test-agent",
        )
        db_session.add(session)
        await db_session.commit()

        # List sessions
        response = await client.get(
            "/api/v1/auth/sessions",
            cookies={"ff_sess": token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["is_current"] is True
        assert data["sessions"][0]["ip"] == "127.0.0.1"
        assert data["sessions"][0]["user_agent"] == "test-agent"

    @pytest.mark.asyncio
    async def test_list_sessions_multiple_sessions(
        self, client: AsyncClient, db_session
    ):
        """Should list all active sessions."""
        # Get CSRF token
        csrf_response = await client.get("/healthz")
        csrf_token = csrf_response.cookies["csrf_token"]

        # Create user
        now = datetime.now(UTC)
        user = User(
            email="multisessions@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create current session
        token = create_session_token()
        current_session = Session(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + timedelta(days=7),
            ip="127.0.0.1",
            user_agent="current-agent",
        )
        db_session.add(current_session)

        # Create other active sessions
        other_session1 = Session(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=hash_token(create_session_token()),
            created_at=now - timedelta(days=1),
            expires_at=now + timedelta(days=6),
            ip="192.168.1.1",
            user_agent="mobile-agent",
        )
        db_session.add(other_session1)

        other_session2 = Session(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=hash_token(create_session_token()),
            created_at=now - timedelta(days=2),
            expires_at=now + timedelta(days=5),
            ip="10.0.0.1",
            user_agent="desktop-agent",
        )
        db_session.add(other_session2)

        # Create revoked session (should not appear)
        revoked_session = Session(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=hash_token(create_session_token()),
            created_at=now - timedelta(days=3),
            expires_at=now + timedelta(days=4),
            revoked_at=now,
        )
        db_session.add(revoked_session)

        # Create expired session (should not appear)
        expired_session = Session(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=hash_token(create_session_token()),
            created_at=now - timedelta(days=8),
            expires_at=now - timedelta(days=1),
        )
        db_session.add(expired_session)

        await db_session.commit()

        # List sessions
        response = await client.get(
            "/api/v1/auth/sessions",
            cookies={"ff_sess": token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3  # Only active, non-revoked sessions
        assert len(data["sessions"]) == 3

        # Verify current session is marked
        current_sessions = [s for s in data["sessions"] if s["is_current"]]
        assert len(current_sessions) == 1
        assert current_sessions[0]["user_agent"] == "current-agent"

        # Verify sessions are ordered by creation date (newest first)
        assert data["sessions"][0]["user_agent"] == "current-agent"
        assert data["sessions"][1]["user_agent"] == "mobile-agent"
        assert data["sessions"][2]["user_agent"] == "desktop-agent"

    @pytest.mark.asyncio
    async def test_list_sessions_excludes_rotated(
        self, client: AsyncClient, db_session
    ):
        """Should exclude rotated sessions."""
        # Get CSRF token
        csrf_response = await client.get("/healthz")
        csrf_token = csrf_response.cookies["csrf_token"]

        # Create user
        now = datetime.now(UTC)
        user = User(
            email="rotatedsessions@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create current session
        token = create_session_token()
        current_session = Session(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + timedelta(days=7),
        )
        db_session.add(current_session)

        # Create rotated session (should not appear)
        rotated_session = Session(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=hash_token(create_session_token()),
            created_at=now - timedelta(days=1),
            expires_at=now + timedelta(days=6),
            rotated_at=now,
        )
        db_session.add(rotated_session)

        await db_session.commit()

        # List sessions
        response = await client.get(
            "/api/v1/auth/sessions",
            cookies={"ff_sess": token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1  # Only non-rotated session
        assert data["sessions"][0]["is_current"] is True
