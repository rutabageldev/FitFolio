"""Tests for /api/v1/auth/logout endpoint."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.core.security import create_session_token, hash_token
from app.db.models.auth import Session, User

pytestmark = [pytest.mark.security, pytest.mark.integration]


class TestLogout:
    """Test logout endpoint behavior."""

    @pytest.mark.asyncio
    async def test_logout_unauthenticated(self, client: AsyncClient):
        """Should succeed even without authentication (idempotent)."""
        # CSRF token is handled by middleware in tests via /healthz
        csrf_token = (await client.get("/healthz")).cookies["csrf_token"]
        response = await client.post(
            "/api/v1/auth/logout",
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 200
        assert "Logged out successfully" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_logout_with_valid_session(self, client: AsyncClient, db_session):
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

        csrf_token = (await client.get("/healthz")).cookies["csrf_token"]
        response = await client.post(
            "/api/v1/auth/logout",
            cookies={"csrf_token": csrf_token},
            headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 200
        assert "Logged out successfully" in response.json()["message"]
        await db_session.refresh(session)
        assert session.revoked_at is not None

    @pytest.mark.asyncio
    async def test_logout_already_revoked_session(
        self, client: AsyncClient, db_session
    ):
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
            revoked_at=now,
            ip="127.0.0.1",
            user_agent="test",
        )
        db_session.add(session)
        await db_session.commit()

        csrf_token = (await client.get("/healthz")).cookies["csrf_token"]
        response = await client.post(
            "/api/v1/auth/logout",
            cookies={"csrf_token": csrf_token},
            headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 200
        assert "Logged out successfully" in response.json()["message"]
