"""Email integration tests using email capture fixture for maximum coverage.

Tests the actual email sending code paths by capturing emails instead of mocking.
This allows the full code execution including error handling paths.
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from app.db.models.auth import LoginEvent, MagicLinkToken, User

pytestmark = [pytest.mark.security, pytest.mark.integration]


@pytest_asyncio.fixture
async def csrf_token(client: AsyncClient):
    """Get CSRF token for tests."""
    response = await client.get("/healthz")
    return response.cookies["csrf_token"]


class EmailCapture:
    """Capture emails sent during tests instead of actually sending them."""

    def __init__(self):
        self.emails = []
        self.should_fail = False
        self.failure_message = "SMTP connection failed"

    async def send_email(self, to: str, subject: str, body: str):
        """Capture email details while executing the full code path."""
        if self.should_fail:
            raise Exception(self.failure_message)

        self.emails.append({"to": to, "subject": subject, "body": body})

    def reset(self):
        """Reset captured emails and failure state."""
        self.emails = []
        self.should_fail = False


@pytest_asyncio.fixture
async def email_capture():
    """Provide email capture fixture for tests."""
    capture = EmailCapture()
    with patch("app.api.v1.auth.send_email", side_effect=capture.send_email):
        yield capture


class TestMagicLinkNewUserWithEmailCapture:
    """Test magic link for new users with email capture (no mocking)."""

    @pytest.mark.asyncio
    async def test_new_user_registration_full_flow_with_email(
        self, client: AsyncClient, csrf_token, db_session, email_capture
    ):
        """Should execute full new user registration with real email capture."""
        email = "newuser_capture@example.com"

        response = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200

        # Verify user was created
        user_stmt = select(User).where(User.email == email.lower())
        user_result = await db_session.execute(user_stmt)
        user = user_result.scalar_one()

        assert user.email == email.lower()
        assert user.is_active is True
        assert user.is_email_verified is False

        # Verify verification token was created
        token_stmt = select(MagicLinkToken).where(MagicLinkToken.user_id == user.id)
        token_result = await db_session.execute(token_stmt)
        token = token_result.scalar_one()

        assert token.purpose == "email_verification"
        assert token.expires_at > datetime.now(UTC)
        # Verify 24 hour expiry
        expiry_delta = token.expires_at - datetime.now(UTC)
        assert expiry_delta.total_seconds() < (24 * 3600 + 60)
        assert expiry_delta.total_seconds() > (24 * 3600 - 60)

        # Verify login event was created
        event_stmt = select(LoginEvent).where(LoginEvent.user_id == user.id)
        event_result = await db_session.execute(event_stmt)
        event = event_result.scalar_one()

        assert event.event_type == "user_created"

        # Verify email was captured (not mocked away)
        assert len(email_capture.emails) == 1
        captured_email = email_capture.emails[0]
        assert captured_email["to"] == email
        assert "verify" in captured_email["subject"].lower()
        assert "FitFolio" in captured_email["body"]
        assert "http://localhost:5173/auth/verify-email" in captured_email["body"]

    @pytest.mark.asyncio
    async def test_new_user_email_send_failure_returns_500(
        self, client: AsyncClient, csrf_token, db_session, email_capture
    ):
        """Should return 500 and proper error when email sending fails."""
        email = "emailfail@example.com"

        # Configure capture to fail
        email_capture.should_fail = True
        email_capture.failure_message = "SMTP server unavailable"

        response = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Should get 500 error
        assert response.status_code == 500
        detail = response.json()["detail"]
        assert "verification email" in detail.lower()

        # Verify user WAS created (failure happens after user creation)
        user_stmt = select(User).where(User.email == email.lower())
        user_result = await db_session.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        # User and token should exist even though email failed
        assert user is not None

    @pytest.mark.asyncio
    async def test_existing_verified_user_gets_login_email(
        self, client: AsyncClient, csrf_token, db_session, email_capture
    ):
        """Should send login magic link (not verification) for existing user."""
        # Create existing verified user
        now = datetime.now(UTC)
        user = User(
            email="existing_verified@example.com",
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
            json={"email": user.email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200

        # Verify login token (not verification token) was created
        token_stmt = (
            select(MagicLinkToken)
            .where(MagicLinkToken.user_id == user.id)
            .order_by(MagicLinkToken.created_at.desc())
        )
        token_result = await db_session.execute(token_stmt)
        token = token_result.scalar_one()

        assert token.purpose == "login"
        # Login tokens expire in 15 minutes
        expiry_delta = token.expires_at - datetime.now(UTC)
        assert expiry_delta.total_seconds() < (15 * 60 + 30)
        assert expiry_delta.total_seconds() > (15 * 60 - 30)

        # Verify email was sent
        assert len(email_capture.emails) == 1
        captured_email = email_capture.emails[0]
        assert captured_email["to"] == user.email
        assert "sign in" in captured_email["subject"].lower()


class TestEmailVerificationWithCapture:
    """Test email verification resend with capture."""

    @pytest.mark.asyncio
    async def test_resend_verification_creates_new_token_and_sends_email(
        self, client: AsyncClient, csrf_token, db_session, email_capture
    ):
        """Should create new verification token and send email."""
        # Create unverified user
        now = datetime.now(UTC)
        user = User(
            email="unverified_resend@example.com",
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
            json={"email": user.email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200

        # Verify token was created
        token_stmt = select(MagicLinkToken).where(MagicLinkToken.user_id == user.id)
        token_result = await db_session.execute(token_stmt)
        token = token_result.scalar_one()

        assert token.purpose == "email_verification"

        # Verify login event was created
        event_stmt = select(LoginEvent).where(LoginEvent.user_id == user.id)
        event_result = await db_session.execute(event_stmt)
        event = event_result.scalar_one()

        assert event.event_type == "email_verification_resent"

        # Verify email was sent
        assert len(email_capture.emails) == 1
        assert email_capture.emails[0]["to"] == user.email

    @pytest.mark.asyncio
    async def test_resend_verification_email_failure_returns_500(
        self, client: AsyncClient, csrf_token, db_session, email_capture
    ):
        """Should return 500 when email sending fails during resend."""
        # Create unverified user
        now = datetime.now(UTC)
        user = User(
            email="unverified_fail@example.com",
            is_active=True,
            is_email_verified=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()

        # Configure email to fail
        email_capture.should_fail = True

        response = await client.post(
            "/api/v1/auth/email/resend-verification",
            json={"email": user.email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 500
        detail = response.json()["detail"]
        assert "verification email" in detail.lower()

    @pytest.mark.asyncio
    async def test_resend_for_already_verified_user_no_email(
        self, client: AsyncClient, csrf_token, db_session, email_capture
    ):
        """Should return 200 but not send email for already verified user."""
        # Create verified user
        now = datetime.now(UTC)
        user = User(
            email="already_verified@example.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/email/resend-verification",
            json={"email": user.email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Returns 200 for anti-enumeration
        assert response.status_code == 200

        # No email should be sent
        assert len(email_capture.emails) == 0

    @pytest.mark.asyncio
    async def test_resend_for_inactive_user_no_email(
        self, client: AsyncClient, csrf_token, db_session, email_capture
    ):
        """Should return 200 but not send email for inactive user."""
        # Create inactive user
        now = datetime.now(UTC)
        user = User(
            email="inactive_resend@example.com",
            is_active=False,
            is_email_verified=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/email/resend-verification",
            json={"email": user.email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Returns 200 for anti-enumeration
        assert response.status_code == 200

        # No email should be sent (user inactive)
        assert len(email_capture.emails) == 0

    @pytest.mark.asyncio
    async def test_resend_for_nonexistent_user_returns_200_no_email(
        self, client: AsyncClient, csrf_token, email_capture
    ):
        """Should return 200 but not send email for non-existent user."""
        response = await client.post(
            "/api/v1/auth/email/resend-verification",
            json={"email": "doesnotexist@example.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Returns 200 for anti-enumeration
        assert response.status_code == 200

        # No email sent
        assert len(email_capture.emails) == 0
