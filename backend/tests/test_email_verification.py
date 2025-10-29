"""Tests for email verification functionality."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.core.security import hash_token
from app.db.models.auth import MagicLinkToken, User


class TestEmailVerification:
    """Test email verification flow."""

    @pytest.mark.asyncio
    async def test_new_user_receives_verification_email(
        self, client: AsyncClient, db_session
    ):
        """New users should receive verification email, not magic link."""
        response = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": "newuser@test.com"},
        )

        assert response.status_code == 200
        assert "magic link has been sent" in response.json()["message"]

        # Verify a verification token was created (not a login token)
        from sqlalchemy import select

        stmt = select(MagicLinkToken).where(
            MagicLinkToken.purpose == "email_verification"
        )
        result = await db_session.execute(stmt)
        token = result.scalar_one_or_none()

        assert token is not None
        assert token.purpose == "email_verification"

    @pytest.mark.asyncio
    async def test_email_verification_success(self, client: AsyncClient, db_session):
        """Should verify email and create session."""
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
        token = "test_verification_token"
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
        )

        assert response.status_code == 200
        assert "verified successfully" in response.json()["message"]
        assert "session_token" in response.json()

        # Verify user is now verified
        await db_session.refresh(user)
        assert user.is_email_verified is True

        # Verify token was marked as used
        await db_session.refresh(verification_token)
        assert verification_token.used_at is not None

    @pytest.mark.asyncio
    async def test_email_verification_invalid_token(self, client: AsyncClient):
        """Should reject invalid verification token."""
        response = await client.post(
            "/api/v1/auth/email/verify",
            json={"token": "invalid_token"},
        )

        assert response.status_code == 400
        assert "Invalid or expired" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_email_verification_expired_token(
        self, client: AsyncClient, db_session
    ):
        """Should reject expired verification token."""
        # Create user
        now = datetime.now(UTC)
        user = User(
            email="expired@test.com",
            is_active=True,
            is_email_verified=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create expired verification token
        token = "expired_verification_token"
        verification_token = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token),
            purpose="email_verification",
            created_at=now - timedelta(hours=25),
            expires_at=now - timedelta(hours=1),  # Expired 1 hour ago
        )
        db_session.add(verification_token)
        await db_session.commit()

        # Try to verify
        response = await client.post(
            "/api/v1/auth/email/verify",
            json={"token": token},
        )

        assert response.status_code == 400
        assert "Invalid or expired" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_email_verification_already_used_token(
        self, client: AsyncClient, db_session
    ):
        """Should reject already-used verification token."""
        # Create user
        now = datetime.now(UTC)
        user = User(
            email="reuse@test.com",
            is_active=True,
            is_email_verified=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create used verification token
        token = "used_verification_token"
        verification_token = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token),
            purpose="email_verification",
            created_at=now,
            expires_at=now + timedelta(hours=24),
            used_at=now - timedelta(minutes=5),  # Already used
        )
        db_session.add(verification_token)
        await db_session.commit()

        # Try to verify again
        response = await client.post(
            "/api/v1/auth/email/verify",
            json={"token": token},
        )

        assert response.status_code == 400
        assert "Invalid or expired" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_resend_verification_email(self, client: AsyncClient, db_session):
        """Should resend verification email for unverified users."""
        # Create unverified user
        now = datetime.now(UTC)
        user = User(
            email="resend@test.com",
            is_active=True,
            is_email_verified=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()

        # Request resend
        response = await client.post(
            "/api/v1/auth/email/resend-verification",
            json={"email": "resend@test.com"},
        )

        assert response.status_code == 200
        assert "verification email has been sent" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_resend_verification_verified_user(
        self, client: AsyncClient, db_session
    ):
        """Should not send email to already-verified users."""
        # Create verified user
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

        # Request resend (should return success but not send email)
        response = await client.post(
            "/api/v1/auth/email/resend-verification",
            json={"email": "verified@test.com"},
        )

        # Should return success to prevent enumeration
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_resend_verification_nonexistent_user(self, client: AsyncClient):
        """Should return success for nonexistent users (prevent enumeration)."""
        response = await client.post(
            "/api/v1/auth/email/resend-verification",
            json={"email": "nonexistent@test.com"},
        )

        # Should return success to prevent enumeration
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_unverified_user_cannot_login(self, client: AsyncClient, db_session):
        """Unverified users should be blocked from logging in."""
        # Create unverified user
        now = datetime.now(UTC)
        user = User(
            email="blocked@test.com",
            is_active=True,
            is_email_verified=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create magic link token (for login)
        token = "test_login_token"
        magic_link = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token),
            purpose="login",
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        db_session.add(magic_link)
        await db_session.commit()

        # Try to verify magic link
        response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token},
        )

        # Should be forbidden
        assert response.status_code == 403
        assert "verify your email" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_verified_user_can_login(self, client: AsyncClient, db_session):
        """Verified users should be able to log in."""
        # Create verified user
        now = datetime.now(UTC)
        user = User(
            email="verified_login@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create magic link token
        token = "test_verified_login_token"
        magic_link = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token),
            purpose="login",
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        db_session.add(magic_link)
        await db_session.commit()

        # Verify magic link
        response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token},
        )

        # Should succeed
        assert response.status_code == 200
        assert "session_token" in response.json()

    @pytest.mark.asyncio
    async def test_me_endpoint_includes_verification_status(
        self, client: AsyncClient, db_session
    ):
        """The /me endpoint should include email verification status."""
        # Create verified user with session
        from app.core.security import create_session_token

        now = datetime.now(UTC)
        user = User(
            email="me@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create session
        from app.db.models.auth import Session

        session_token = create_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(session_token),
            created_at=now,
            expires_at=now + timedelta(hours=336),
        )
        db_session.add(session)
        await db_session.commit()

        # Call /me endpoint
        response = await client.get(
            "/api/v1/auth/me",
            cookies={"ff_sess": session_token},
        )

        assert response.status_code == 200
        assert response.json()["is_email_verified"] is True
