"""Tests for /api/v1/auth/me endpoint behavior."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.core.security import create_session_token, hash_token
from app.db.models.auth import Session, User

pytestmark = [pytest.mark.security, pytest.mark.integration]


class TestMeEndpoint:
    """Session-profile behavior for /me."""

    @pytest.mark.asyncio
    async def test_me_includes_verification_status(
        self, client: AsyncClient, db_session
    ):
        """The /me endpoint should include email verification status."""
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
            "/api/v1/auth/me", cookies={"ff_sess": session_token}
        )
        assert response.status_code == 200
        assert response.json()["is_email_verified"] is True

    @pytest.mark.asyncio
    async def test_me_inactive_user_rejected(self, client: AsyncClient, db_session):
        """Should reject /me request from inactive user."""
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
            "/api/v1/auth/me", cookies={"ff_sess": session_token}
        )
        assert response.status_code == 401
        assert "inactive" in response.json()["detail"].lower()
