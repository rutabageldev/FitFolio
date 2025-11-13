"""Real integration tests with MINIMAL mocking to maximize coverage.

These tests let the actual code execute as much as possible.
Email sending is mocked to async no-op to avoid SMTP failures
but let all other code run.
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from app.db.models.auth import LoginEvent, MagicLinkToken, User


@pytest_asyncio.fixture
async def csrf_token(client: AsyncClient):
    """Get CSRF token for tests."""
    response = await client.get("/healthz")
    return response.cookies["csrf_token"]


# Create a truly async no-op email sender
async def mock_email_send(*_args, **_kwargs):
    """Async no-op that doesn't raise exceptions."""
    pass


class TestRealMagicLinkFlow:
    """Real integration tests that execute actual code paths."""

    @patch("app.api.v1.auth.send_email", new=mock_email_send)
    @pytest.mark.asyncio
    async def test_magic_link_start_creates_new_user_full_flow(
        self, client: AsyncClient, csrf_token, db_session
    ):
        """Full flow: start magic link for new user - executes real DB operations."""
        email = "realintegration@example.com"

        response = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200

        # Verify user was actually created in DB
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

        # Verify login event was created
        event_stmt = select(LoginEvent).where(LoginEvent.user_id == user.id)
        event_result = await db_session.execute(event_stmt)
        event = event_result.scalar_one()

        assert event.event_type == "user_created"

    @patch("app.api.v1.auth.send_email", new=mock_email_send)
    @pytest.mark.asyncio
    async def test_magic_link_start_existing_user_full_flow(
        self, client: AsyncClient, csrf_token, db_session
    ):
        """Full flow: start magic link for existing user - real DB operations."""
        # Create user first
        now = datetime.now(UTC)
        user = User(
            email="existingreal@example.com",
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

        # Verify login token was created (not verification)
        token_stmt = (
            select(MagicLinkToken)
            .where(MagicLinkToken.user_id == user.id)
            .order_by(MagicLinkToken.created_at.desc())
        )
        token_result = await db_session.execute(token_stmt)
        token = token_result.scalar_one()

        assert token.purpose == "login"

    @patch("app.api.v1.auth.send_email", new=mock_email_send)
    @pytest.mark.asyncio
    async def test_email_resend_verification_full_flow(
        self, client: AsyncClient, csrf_token, db_session
    ):
        """Full flow: resend verification for unverified user."""
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

        # Verify event was logged
        event_stmt = select(LoginEvent).where(LoginEvent.user_id == user.id)
        event_result = await db_session.execute(event_stmt)
        event = event_result.scalar_one()

        assert event.event_type == "email_verification_resent"
