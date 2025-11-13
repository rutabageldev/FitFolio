"""Additional listing behaviors for /api/v1/auth/sessions."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.core.security import create_session_token, hash_token
from app.db.models.auth import Session, User

pytestmark = [pytest.mark.security, pytest.mark.integration]


class TestSessionListingVariants:
    @pytest.mark.asyncio
    async def test_list_sessions_multiple_sessions(
        self, client: AsyncClient, db_session
    ):
        csrf_token = (await client.get("/healthz")).cookies["csrf_token"]
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
        other_session1 = Session(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=hash_token(create_session_token()),
            created_at=now - timedelta(days=1),
            expires_at=now + timedelta(days=6),
            ip="192.168.1.1",
            user_agent="mobile-agent",
        )
        other_session2 = Session(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=hash_token(create_session_token()),
            created_at=now - timedelta(days=2),
            expires_at=now + timedelta(days=5),
            ip="10.0.0.1",
            user_agent="desktop-agent",
        )
        revoked_session = Session(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=hash_token(create_session_token()),
            created_at=now - timedelta(days=3),
            expires_at=now + timedelta(days=4),
            revoked_at=now,
        )
        expired_session = Session(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=hash_token(create_session_token()),
            created_at=now - timedelta(days=8),
            expires_at=now - timedelta(days=1),
        )
        db_session.add_all(
            [
                current_session,
                other_session1,
                other_session2,
                revoked_session,
                expired_session,
            ]
        )
        await db_session.commit()

        response = await client.get(
            "/api/v1/auth/sessions",
            cookies={"ff_sess": token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["sessions"]) == 3
        current_sessions = [s for s in data["sessions"] if s["is_current"]]
        assert (
            len(current_sessions) == 1
            and current_sessions[0]["user_agent"] == "current-agent"
        )
        assert data["sessions"][0]["user_agent"] == "current-agent"
        assert data["sessions"][1]["user_agent"] == "mobile-agent"
        assert data["sessions"][2]["user_agent"] == "desktop-agent"

    @pytest.mark.asyncio
    async def test_list_sessions_excludes_rotated(
        self, client: AsyncClient, db_session
    ):
        csrf_token = (await client.get("/healthz")).cookies["csrf_token"]
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

        token = create_session_token()
        current_session = Session(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + timedelta(days=7),
        )
        rotated_session = Session(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=hash_token(create_session_token()),
            created_at=now - timedelta(days=1),
            expires_at=now + timedelta(days=6),
            rotated_at=now,
        )
        db_session.add_all([current_session, rotated_session])
        await db_session.commit()

        response = await client.get(
            "/api/v1/auth/sessions",
            cookies={"ff_sess": token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
