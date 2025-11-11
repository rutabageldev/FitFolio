"""Comprehensive error path tests for auth endpoints.

This file focuses on testing error handling, infrastructure failures,
and edge cases to improve coverage of auth.py to 85%+.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_session_token, hash_token
from app.db.models.auth import MagicLinkToken, Session, User, WebAuthnCredential


@pytest_asyncio.fixture
async def csrf_token(client: AsyncClient):
    """Get CSRF token for requests."""
    response = await client.get("/healthz")
    return response.cookies["csrf_token"]


@pytest_asyncio.fixture
async def verified_user(db_session):
    """Create a verified user for testing."""
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
    """Create a user with an active session."""
    now = datetime.now(UTC)
    token = create_session_token()
    session = Session(
        user_id=verified_user.id,
        token_hash=hash_token(token),
        created_at=now,
        expires_at=now + timedelta(days=14),
        ip="127.0.0.1",
        user_agent="test-agent",
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return verified_user, session, token


class TestWebAuthnRegistrationErrors:
    """Test WebAuthn registration error handling."""

    @pytest.mark.asyncio
    @patch("app.core.challenge_storage.store_challenge")
    async def test_register_start_redis_failure(
        self, mock_store_challenge, client: AsyncClient, csrf_token
    ):
        """Should handle Redis failure when storing challenge."""
        # Mock Redis failure
        mock_store_challenge.side_effect = RuntimeError(
            "Failed to store challenge in Redis: Connection error"
        )

        response = await client.post(
            "/api/v1/auth/webauthn/register/start",
            json={"email": "newuser@test.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Infrastructure failures currently propagate as 500 errors
        # This is valid behavior that should be tested
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_register_finish_malformed_credential(
        self, client: AsyncClient, db_session, csrf_token
    ):
        """Should handle malformed WebAuthn credential data."""
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

        # Store challenge in Redis
        from app.core.redis_client import get_redis

        redis = await get_redis()
        challenge_id = "test_challenge_123"
        await redis.setex(
            f"webauthn:challenge:registration:{challenge_id}",
            300,
            "webauthn@test.com:abcd1234",
        )

        # Send malformed credential (missing required fields)
        response = await client.post(
            "/api/v1/auth/webauthn/register/finish",
            json={
                "email": "webauthn@test.com",
                "credential": {
                    "id": "fake_credential"
                },  # Missing rawId, response, etc.
                "challenge_id": challenge_id,
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Should get 400 with error about credential format
        assert response.status_code == 400
        assert "detail" in response.json()

    @pytest.mark.asyncio
    async def test_register_finish_user_not_found(
        self, client: AsyncClient, csrf_token
    ):
        """Should return 404 if user doesn't exist during registration finish."""
        response = await client.post(
            "/api/v1/auth/webauthn/register/finish",
            json={
                "email": "nonexistent@test.com",
                "credential": {"id": "fake_cred"},
                "challenge_id": "fake_challenge",
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_finish_invalid_challenge(
        self, client: AsyncClient, csrf_token, verified_user
    ):
        """Should reject invalid or expired challenge."""
        response = await client.post(
            "/api/v1/auth/webauthn/register/finish",
            json={
                "email": verified_user.email,
                "credential": {"id": "fake_cred"},
                "challenge_id": "invalid_challenge_id",
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 400
        assert "Invalid or expired challenge" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_finish_challenge_email_mismatch(
        self, client: AsyncClient, db_session, csrf_token
    ):
        """Should reject if challenge was issued for different email."""
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
        challenge_id = "test_challenge_mismatch"
        await redis.setex(
            f"webauthn:challenge:registration:{challenge_id}",
            300,
            "user1@test.com:abcd1234",
        )

        # Try to use with user2
        response = await client.post(
            "/api/v1/auth/webauthn/register/finish",
            json={
                "email": "user2@test.com",
                "credential": {"id": "fake_cred"},
                "challenge_id": challenge_id,
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 400
        # The implementation returns either "different user" or
        # "expired challenge" for security
        detail = response.json()["detail"]
        assert "different user" in detail or "Invalid or expired challenge" in detail


class TestWebAuthnAuthenticationErrors:
    """Test WebAuthn authentication error handling."""

    @pytest.mark.asyncio
    async def test_authenticate_start_user_not_found(
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
    async def test_authenticate_start_no_credentials(
        self, client: AsyncClient, csrf_token, verified_user
    ):
        """Should return 400 if user has no passkeys."""
        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/start",
            json={"email": verified_user.email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 400
        assert "No passkeys registered" in response.json()["detail"]

    @pytest.mark.asyncio
    @patch("app.core.challenge_storage.store_challenge")
    async def test_authenticate_start_redis_failure(
        self,
        mock_store_challenge,
        client: AsyncClient,
        db_session,
        csrf_token,
        verified_user,
    ):
        """Should handle Redis failure when storing auth challenge."""
        # Add a credential to the user
        cred = WebAuthnCredential(
            user_id=verified_user.id,
            credential_id=bytes.fromhex("0102030405060708"),
            public_key=b"fake_public_key",
            sign_count=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(cred)
        await db_session.commit()

        # Mock Redis failure
        mock_store_challenge.side_effect = RuntimeError(
            "Failed to store challenge in Redis: Connection error"
        )

        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/start",
            json={"email": verified_user.email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Infrastructure failures propagate as 500
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_authenticate_finish_user_not_found(
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
    async def test_authenticate_finish_invalid_challenge(
        self, client: AsyncClient, csrf_token, verified_user
    ):
        """Should reject invalid challenge."""
        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/finish",
            json={
                "email": verified_user.email,
                "credential": {"id": "fake_id"},
                "challenge_id": "invalid_challenge",
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 400
        assert "Invalid or expired challenge" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_authenticate_finish_missing_credential_id(
        self, client: AsyncClient, csrf_token, verified_user
    ):
        """Should require credential ID in request."""
        # Store valid challenge
        from app.core.redis_client import get_redis

        redis = await get_redis()
        challenge_id = "test_auth_challenge"
        await redis.setex(
            f"webauthn:challenge:authentication:{challenge_id}",
            300,
            f"{verified_user.email}:abcd1234",
        )

        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/finish",
            json={
                "email": verified_user.email,
                "credential": {},  # No ID
                "challenge_id": challenge_id,
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 400
        assert "Credential ID is required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_authenticate_finish_credential_not_found(
        self, client: AsyncClient, csrf_token, verified_user
    ):
        """Should reject if credential doesn't belong to user."""
        # Store valid challenge
        from app.core.redis_client import get_redis

        redis = await get_redis()
        challenge_id = "test_badcred_challenge"
        await redis.setex(
            f"webauthn:challenge:authentication:{challenge_id}",
            300,
            f"{verified_user.email}:abcd1234",
        )

        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/finish",
            json={
                "email": verified_user.email,
                "credential": {"id": "0102030405060708"},  # Non-existent
                "challenge_id": challenge_id,
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 400
        assert "Invalid credential" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_authenticate_finish_malformed_credential(
        self, client: AsyncClient, db_session, csrf_token, verified_user
    ):
        """Should handle malformed WebAuthn authentication credential."""
        # Add credential to user
        cred = WebAuthnCredential(
            user_id=verified_user.id,
            credential_id=bytes.fromhex("0102030405060708"),
            public_key=b"fake_public_key",
            sign_count=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(cred)
        await db_session.commit()

        # Store valid challenge
        from app.core.redis_client import get_redis

        redis = await get_redis()
        challenge_id = "test_verify_fail"
        await redis.setex(
            f"webauthn:challenge:authentication:{challenge_id}",
            300,
            f"{verified_user.email}:abcd1234",
        )

        # Send malformed credential (missing required fields)
        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/finish",
            json={
                "email": verified_user.email,
                "credential": {
                    "id": "0102030405060708"
                },  # Missing rawId, response, etc.
                "challenge_id": challenge_id,
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Should get 400 with error about credential format
        assert response.status_code == 400
        assert "detail" in response.json()


class TestMagicLinkErrors:
    """Test magic link error handling."""

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.send_email")
    async def test_magic_link_start_email_failure(
        self, mock_send_email, client: AsyncClient, csrf_token
    ):
        """Should handle email send failures."""
        from smtplib import SMTPException

        mock_send_email.side_effect = SMTPException("SMTP server unavailable")

        response = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": "newuser@test.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Email failures currently propagate as 500 errors
        # This tests that infrastructure failures are observable
        assert response.status_code == 500

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.send_email")
    async def test_magic_link_start_creates_user_and_sends_verification(
        self, mock_send_email, client: AsyncClient, db_session, csrf_token
    ):
        """New user should get verification email."""
        mock_send_email.return_value = None

        response = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": "brandnew@test.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200

        # Verify user created
        stmt = select(User).where(User.email == "brandnew@test.com")
        result = await db_session.execute(stmt)
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.is_email_verified is False

        # Verify email_verification token created (not login)
        token_stmt = select(MagicLinkToken).where(
            MagicLinkToken.user_id == user.id,
            MagicLinkToken.purpose == "email_verification",
        )
        token_result = await db_session.execute(token_stmt)
        token = token_result.scalar_one_or_none()
        assert token is not None

        # Verify email was called
        mock_send_email.assert_called_once()
        assert "verify" in mock_send_email.call_args.kwargs["subject"].lower()

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.send_email")
    async def test_magic_link_start_existing_verified_user_gets_login_link(
        self,
        mock_send_email,
        client: AsyncClient,
        csrf_token,
        verified_user,
        db_session,
    ):
        """Existing verified user gets login link."""
        mock_send_email.return_value = None

        response = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": verified_user.email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200

        # Verify login token created
        stmt = select(MagicLinkToken).where(
            MagicLinkToken.user_id == verified_user.id,
            MagicLinkToken.purpose == "login",
        )
        result = await db_session.execute(stmt)
        token = result.scalar_one_or_none()
        assert token is not None

        # Verify email sent with "sign in"
        mock_send_email.assert_called_once()
        assert "sign in" in mock_send_email.call_args.kwargs["subject"].lower()

    @pytest.mark.asyncio
    async def test_magic_link_verify_inactive_user(
        self, client: AsyncClient, db_session, csrf_token
    ):
        """Should reject inactive users."""
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

        # Create magic link token
        token = "inactive_user_token"
        magic_token = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token),
            purpose="login",
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        db_session.add(magic_token)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 400
        assert "inactive" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_magic_link_verify_unverified_email(
        self, client: AsyncClient, db_session, csrf_token
    ):
        """Should reject login for unverified email."""
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

        # Create login token (not verification)
        token = "unverified_login_token"
        magic_token = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token),
            purpose="login",
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        db_session.add(magic_token)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 403
        assert "verify your email" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_magic_link_verify_account_locked(
        self, client: AsyncClient, db_session, csrf_token, verified_user
    ):
        """Should reject locked accounts."""
        # Create magic link
        now = datetime.now(UTC)
        token = "locked_account_token"
        magic_token = MagicLinkToken(
            user_id=verified_user.id,
            token_hash=hash_token(token),
            purpose="login",
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        db_session.add(magic_token)
        await db_session.commit()

        # Lock the account
        from app.core.redis_client import get_redis

        redis = await get_redis()
        lockout_key = f"lockout:{verified_user.id}"
        lockout_until = (now + timedelta(minutes=15)).isoformat()
        await redis.setex(lockout_key, 900, lockout_until)

        response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 429
        assert "temporarily locked" in response.json()["detail"].lower()


class TestEmailVerificationErrors:
    """Test email verification error handling."""

    @pytest.mark.asyncio
    async def test_email_verify_invalid_token(self, client: AsyncClient, csrf_token):
        """Should reject invalid verification token."""
        response = await client.post(
            "/api/v1/auth/email/verify",
            json={"token": "invalid_token_xyz"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 400
        assert "Invalid or expired" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_email_verify_inactive_user(
        self, client: AsyncClient, db_session, csrf_token
    ):
        """Should reject inactive users."""
        # Create inactive unverified user
        now = datetime.now(UTC)
        user = User(
            email="inactive_unverified@test.com",
            is_active=False,
            is_email_verified=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()

        # Create verification token
        token = "inactive_verification_token"
        verification_token = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token),
            purpose="email_verification",
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )
        db_session.add(verification_token)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/email/verify",
            json={"token": token},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 400
        assert "inactive" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_email_verify_wrong_purpose(
        self, client: AsyncClient, db_session, csrf_token
    ):
        """Should reject token with wrong purpose."""
        # Create user
        now = datetime.now(UTC)
        user = User(
            email="wrongpurpose@test.com",
            is_active=True,
            is_email_verified=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()

        # Create login token (wrong purpose)
        token = "wrong_purpose_token"
        magic_token = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token),
            purpose="login",  # Should be email_verification
            created_at=now,
            expires_at=now + timedelta(hours=24),
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
        assert "Invalid or expired" in response.json()["detail"]


class TestResendVerificationErrors:
    """Test resend verification error handling."""

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.send_email")
    async def test_resend_verification_email_failure(
        self, mock_send_email, client: AsyncClient, db_session, csrf_token
    ):
        """Should handle email send failures."""
        from smtplib import SMTPException

        # Create unverified user
        now = datetime.now(UTC)
        user = User(
            email="emailfail@test.com",
            is_active=True,
            is_email_verified=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()

        # Mock email failure
        mock_send_email.side_effect = SMTPException("SMTP error")

        response = await client.post(
            "/api/v1/auth/email/resend-verification",
            json={"email": "emailfail@test.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 500

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.send_email")
    async def test_resend_verification_success(
        self, mock_send_email, client: AsyncClient, db_session, csrf_token
    ):
        """Unverified user should get verification email."""
        mock_send_email.return_value = None

        # Create unverified user
        now = datetime.now(UTC)
        user = User(
            email="needsverify@test.com",
            is_active=True,
            is_email_verified=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/email/resend-verification",
            json={"email": "needsverify@test.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200

        # Verify email sent
        mock_send_email.assert_called_once()
        assert "verify" in mock_send_email.call_args.kwargs["subject"].lower()

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.send_email")
    async def test_resend_verification_already_verified_no_email(
        self, mock_send_email, client: AsyncClient, csrf_token, verified_user
    ):
        """Already verified users get success response but no email."""
        mock_send_email.return_value = None

        response = await client.post(
            "/api/v1/auth/email/resend-verification",
            json={"email": verified_user.email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Success response to prevent enumeration
        assert response.status_code == 200

        # But no email should be sent
        mock_send_email.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.send_email")
    async def test_resend_verification_nonexistent_user_no_email(
        self, mock_send_email, client: AsyncClient, csrf_token
    ):
        """Nonexistent users should get success response but no email."""
        mock_send_email.return_value = None

        response = await client.post(
            "/api/v1/auth/email/resend-verification",
            json={"email": "doesnotexist@test.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Success to prevent enumeration
        assert response.status_code == 200

        # No email sent
        mock_send_email.assert_not_called()
