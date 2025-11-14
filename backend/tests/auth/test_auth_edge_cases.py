"""Tests for authentication edge cases and additional scenarios.

Tests for inactive users, email verification auth requirements, and session rotation.
"""

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.core.security import create_magic_link_token, create_session_token, hash_token
from app.db.models.auth import MagicLinkToken, Session, User


@pytest_asyncio.fixture
async def inactive_user(db_session):
    """Create an inactive user."""
    now = datetime.now(UTC)
    user = User(
        email="inactive@test.com",
        is_active=False,  # Inactive
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def inactive_user_with_session(db_session, inactive_user):
    """Create inactive user with active session."""
    now = datetime.now(UTC)
    session_token = create_session_token()
    session = Session(
        user_id=inactive_user.id,
        token_hash=hash_token(session_token),
        created_at=now,
        expires_at=now + timedelta(hours=336),
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return inactive_user, session_token


class TestInactiveUserEdgeCases:
    """Tests for inactive user behavior across endpoints."""

    @pytest.mark.asyncio
    async def test_me_endpoint_inactive_user_rejected(self):
        pass  # TODO: Implement test

    @pytest.mark.asyncio
    async def test_email_verify_inactive_user_rejected(
        self, client: AsyncClient, csrf_token, inactive_user, db_session
    ):
        """Should reject email verification for inactive user."""
        # Create verification token for inactive user
        now = datetime.now(UTC)
        token_str = create_magic_link_token()
        token = MagicLinkToken(
            user_id=inactive_user.id,
            token_hash=hash_token(token_str),
            purpose="email_verification",
            created_at=now,
            expires_at=now + timedelta(hours=1),
        )
        db_session.add(token)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/email/verify",
            json={"token": token_str},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Should reject inactive user email verification
        assert response.status_code == 400
        assert "inactive" in response.json()["detail"].lower()


class TestEmailVerificationAuthentication:
    """Tests for email verification authentication requirements."""

    @pytest.mark.asyncio
    async def test_email_verify_already_verified_idempotent(
        self, client: AsyncClient, csrf_token, db_session
    ):
        """Should handle already verified email gracefully (idempotent)."""
        # Create verified user
        now = datetime.now(UTC)
        user = User(
            email="alreadyverified@test.com",
            is_active=True,
            is_email_verified=True,  # Already verified
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create verification token
        token_str = create_magic_link_token()
        token = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token_str),
            purpose="email_verification",
            created_at=now,
            expires_at=now + timedelta(hours=1),
        )
        db_session.add(token)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/email/verify",
            json={"token": token_str},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Should succeed idempotently
        assert response.status_code == 200


# Note: Session rotation tests omitted as the implementation uses a different
# mechanism than originally documented. Session rotation is tested in
# test_session_rotation.py
