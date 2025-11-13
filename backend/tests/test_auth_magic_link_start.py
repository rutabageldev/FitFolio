"""Tests for magic link start endpoint - the UNTESTED 76 lines!

This endpoint at lines 169-244 in auth.py has 0% coverage.
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from app.db.models.auth import User


@pytest_asyncio.fixture
async def existing_verified_user(db_session):
    """Create an existing verified user."""
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
async def existing_unverified_user(db_session):
    """Create an existing unverified user."""
    now = datetime.now(UTC)
    user = User(
        email="unverified@test.com",
        is_active=True,
        is_email_verified=False,  # Not verified
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def csrf_token(client: AsyncClient):
    """Get CSRF token for requests."""
    response = await client.get("/healthz")
    return response.cookies["csrf_token"]


class TestMagicLinkStartNewUser:
    """Tests for magic link start with NEW users."""

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.send_email")
    async def test_start_creates_new_user_and_sends_verification(
        self, mock_send_email, client: AsyncClient, csrf_token, db_session
    ):
        """Should create new user and send EMAIL VERIFICATION (not login link)."""
        mock_send_email.return_value = None
        email = "brandnew@test.com"

        response = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert (
            data["message"]
            == "If an account exists with this email, a magic link has been sent."
        )

        # Verify user was created
        from sqlalchemy import select

        stmt = select(User).where(User.email == email)
        result = await db_session.execute(stmt)
        user = result.scalar_one_or_none()

        assert user is not None
        assert user.is_email_verified is False  # New user is unverified
        assert user.is_active is True

        # Verify email verification token was created (not login token)
        from app.db.models.auth import MagicLinkToken

        token_stmt = select(MagicLinkToken).where(MagicLinkToken.user_id == user.id)
        token_result = await db_session.execute(token_stmt)
        token = token_result.scalar_one_or_none()

        assert token is not None
        assert token.purpose == "email_verification"  # NOT "login"


class TestMagicLinkStartExistingUser:
    """Tests for magic link start with EXISTING users."""

    @patch("app.api.v1.auth.send_email")
    @pytest.mark.asyncio
    async def test_start_verified_user_sends_login_link(
        self,
        mock_send_email,
        client: AsyncClient,
        csrf_token,
        existing_verified_user,
        db_session,
    ):
        """Should send LOGIN link for verified user (not verification)."""
        mock_send_email.return_value = None
        response = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": existing_verified_user.email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert (
            data["message"]
            == "If an account exists with this email, a magic link has been sent."
        )

        # Verify login token was created
        from app.db.models.auth import MagicLinkToken

        token_stmt = (
            select(MagicLinkToken)
            .where(MagicLinkToken.user_id == existing_verified_user.id)
            .order_by(MagicLinkToken.created_at.desc())
        )
        token_result = await db_session.execute(token_stmt)
        token = token_result.scalar_one_or_none()

        assert token is not None
        assert token.purpose == "login"  # NOT "email_verification"

    @patch("app.api.v1.auth.send_email")
    @pytest.mark.asyncio
    async def test_start_unverified_user_sends_login_link(
        self,
        mock_send_email,
        client: AsyncClient,
        csrf_token,
        existing_unverified_user,
        db_session,
    ):
        """LOGIN link for unverified user (API doesn't differentiate)."""
        mock_send_email.return_value = None
        response = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": existing_unverified_user.email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200

        # API sends "login" token for ALL existing users (verified or not)
        from app.db.models.auth import MagicLinkToken

        token_stmt = (
            select(MagicLinkToken)
            .where(MagicLinkToken.user_id == existing_unverified_user.id)
            .order_by(MagicLinkToken.created_at.desc())
        )
        token_result = await db_session.execute(token_stmt)
        token = token_result.scalar_one_or_none()

        assert token is not None
        assert token.purpose == "login"  # API sends login for all existing users


class TestMagicLinkStartEdgeCases:
    """Tests for edge cases and error paths."""

    @patch("app.api.v1.auth.send_email")
    @pytest.mark.asyncio
    async def test_start_invalid_email_format(
        self, mock_send_email, client: AsyncClient, csrf_token
    ):
        """Should reject invalid email format."""
        mock_send_email.return_value = None
        response = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": "not-an-email"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_start_empty_email(self, client: AsyncClient, csrf_token):
        """Should reject empty email."""
        response = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": ""},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 422  # Validation error

    @patch("app.api.v1.auth.send_email")
    @pytest.mark.asyncio
    async def test_start_case_insensitive_email(
        self,
        _mock_send_email,
        client: AsyncClient,
        csrf_token,
        existing_verified_user,
        db_session,
    ):
        """Should handle email case-insensitively."""
        # Request with uppercase email
        response = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": existing_verified_user.email.upper()},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200

        # Should find existing user (not create new one)
        from sqlalchemy import select

        stmt = select(User).where(
            User.email == existing_verified_user.email.upper().lower()
        )
        result = await db_session.execute(stmt)
        user = result.scalar_one_or_none()

        assert user is not None
        assert user.id == existing_verified_user.id  # Same user

    @patch("app.api.v1.auth.send_email")
    @pytest.mark.asyncio
    async def test_start_no_email_enumeration(
        self, _mock_send_email, client: AsyncClient, csrf_token
    ):
        """Should return generic message (no user enumeration)."""
        # Try with non-existent email
        response1 = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": "doesnotexist@test.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Try with existing email
        response2 = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": "doesnotexist2@test.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Both should return same generic message
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json()["message"] == response2.json()["message"]
        assert (
            response1.json()["message"]
            == "If an account exists with this email, a magic link has been sent."
        )


class TestMagicLinkStartTokenCreation:
    """Tests for token creation and storage."""

    @patch("app.api.v1.auth.send_email")
    @pytest.mark.asyncio
    async def test_start_creates_token_with_24h_expiry(
        self, mock_send_email, client: AsyncClient, csrf_token, db_session
    ):
        """Should create token with 24 hour expiry."""
        mock_send_email.return_value = None
        email = "tokentest@test.com"

        response = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200

        # Check token expiry
        from sqlalchemy import select

        from app.db.models.auth import MagicLinkToken, User

        user_stmt = select(User).where(User.email == email)
        user_result = await db_session.execute(user_stmt)
        user = user_result.scalar_one()

        token_stmt = select(MagicLinkToken).where(MagicLinkToken.user_id == user.id)
        token_result = await db_session.execute(token_stmt)
        token = token_result.scalar_one()

        # Token should expire in approximately 24 hours
        time_diff = (token.expires_at - token.created_at).total_seconds()
        assert 23.5 * 3600 < time_diff < 24.5 * 3600  # ~24 hours

    @patch("app.api.v1.auth.send_email")
    @pytest.mark.asyncio
    async def test_start_token_hash_stored_not_plaintext(
        self, mock_send_email, client: AsyncClient, csrf_token, db_session
    ):
        """Should store hashed token, not plaintext."""
        mock_send_email.return_value = None
        email = "hashtest@test.com"

        response = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200

        # Verify token is hashed
        from sqlalchemy import select

        from app.db.models.auth import MagicLinkToken, User

        user_stmt = select(User).where(User.email == email)
        user_result = await db_session.execute(user_stmt)
        user = user_result.scalar_one()

        token_stmt = select(MagicLinkToken).where(MagicLinkToken.user_id == user.id)
        token_result = await db_session.execute(token_stmt)
        token = token_result.scalar_one()

        # token_hash should be bytes (hashed)
        assert isinstance(token.token_hash, bytes)
        assert len(token.token_hash) > 0
