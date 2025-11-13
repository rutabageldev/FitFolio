"""Tests for session management endpoints and cleanup."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.core.cleanup import cleanup_expired_magic_links, cleanup_expired_sessions
from app.core.security import create_session_token, hash_token
from app.db.models.auth import MagicLinkToken, Session, User

pytestmark = [pytest.mark.security, pytest.mark.integration]


class TestListSessions:
    """Test listing active sessions."""

    @pytest.mark.asyncio
    async def test_list_sessions_requires_auth(self, client: AsyncClient):
        """Should require authentication."""
        response = await client.get("/api/v1/auth/sessions")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_sessions_success(self, client: AsyncClient, db_session):
        """Should list all active sessions for user."""
        # Get CSRF token
        csrf_response = await client.get("/healthz")
        csrf_token = csrf_response.cookies["csrf_token"]

        # Create user
        now = datetime.now(UTC)
        user = User(
            email="sessionlist@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create multiple sessions
        sessions = []
        for i in range(3):
            session_token = create_session_token()
            session = Session(
                user_id=user.id,
                token_hash=hash_token(session_token),
                created_at=now + timedelta(minutes=i),
                expires_at=now + timedelta(hours=336),
                ip=f"192.168.1.{i}",
                user_agent=f"Browser {i}",
            )
            db_session.add(session)
            sessions.append((session, session_token))

        await db_session.commit()

        # Use first session to list all
        current_token = sessions[0][1]
        response = await client.get(
            "/api/v1/auth/sessions",
            cookies={"ff_sess": current_token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert data["total"] == 3

        # Verify current session is marked
        current_marked = [s for s in data["sessions"] if s["is_current"]]
        assert len(current_marked) == 1

    @pytest.mark.asyncio
    async def test_list_sessions_excludes_expired(
        self, client: AsyncClient, db_session
    ):
        """Should not include expired sessions."""
        # Get CSRF token
        csrf_response = await client.get("/healthz")
        csrf_token = csrf_response.cookies["csrf_token"]

        # Create user
        now = datetime.now(UTC)
        user = User(
            email="expired@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create active session
        active_token = create_session_token()
        active_session = Session(
            user_id=user.id,
            token_hash=hash_token(active_token),
            created_at=now,
            expires_at=now + timedelta(hours=336),
        )
        db_session.add(active_session)

        # Create expired session
        expired_session = Session(
            user_id=user.id,
            token_hash=hash_token("expired"),
            created_at=now - timedelta(days=15),
            expires_at=now - timedelta(days=1),  # Expired yesterday
        )
        db_session.add(expired_session)

        await db_session.commit()

        # List sessions
        response = await client.get(
            "/api/v1/auth/sessions",
            cookies={"ff_sess": active_token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        # Should only return the active session
        assert data["total"] == 1


class TestRevokeSession:
    """Test revoking specific sessions."""

    @pytest.mark.asyncio
    async def test_revoke_session_success(self, client: AsyncClient, db_session):
        """Should successfully revoke a session."""
        # Get CSRF token
        csrf_response = await client.get("/healthz")
        csrf_token = csrf_response.cookies["csrf_token"]

        # Create user
        now = datetime.now(UTC)
        user = User(
            email="revoke@test.com",
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
            expires_at=now + timedelta(hours=336),
        )
        db_session.add(current_session)

        target_token = create_session_token()
        target_session = Session(
            user_id=user.id,
            token_hash=hash_token(target_token),
            created_at=now,
            expires_at=now + timedelta(hours=336),
        )
        db_session.add(target_session)

        await db_session.commit()
        await db_session.refresh(target_session)

        # Revoke the target session
        response = await client.delete(
            f"/api/v1/auth/sessions/{target_session.id}",
            cookies={"ff_sess": current_token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "revoked" in data["message"].lower()
        assert data["revoked_session_id"] == str(target_session.id)

        # Verify session was marked as revoked
        await db_session.refresh(target_session)
        assert target_session.revoked_at is not None

    @pytest.mark.asyncio
    async def test_cannot_revoke_current_session(self, client: AsyncClient, db_session):
        """Should not allow revoking current session."""
        # Get CSRF token
        csrf_response = await client.get("/healthz")
        csrf_token = csrf_response.cookies["csrf_token"]

        # Create user and session
        now = datetime.now(UTC)
        user = User(
            email="nocurrent@test.com",
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
        await db_session.refresh(session)

        # Try to revoke current session
        response = await client.delete(
            f"/api/v1/auth/sessions/{session.id}",
            cookies={"ff_sess": session_token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 400
        assert "current session" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_cannot_revoke_other_users_session(
        self, client: AsyncClient, db_session
    ):
        """Should not allow revoking another user's session."""
        # Get CSRF token
        csrf_response = await client.get("/healthz")
        csrf_token = csrf_response.cookies["csrf_token"]

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
        db_session.add_all([user1, user2])
        await db_session.commit()
        await db_session.refresh(user1)
        await db_session.refresh(user2)

        # Create sessions for both users
        user1_token = create_session_token()
        user1_session = Session(
            user_id=user1.id,
            token_hash=hash_token(user1_token),
            created_at=now,
            expires_at=now + timedelta(hours=336),
        )
        user2_session = Session(
            user_id=user2.id,
            token_hash=hash_token(create_session_token()),
            created_at=now,
            expires_at=now + timedelta(hours=336),
        )
        db_session.add_all([user1_session, user2_session])
        await db_session.commit()
        await db_session.refresh(user2_session)

        # User1 tries to revoke User2's session
        response = await client.delete(
            f"/api/v1/auth/sessions/{user2_session.id}",
            cookies={"ff_sess": user1_token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 404


class TestRevokeAllOtherSessions:
    """Test revoking all sessions except current."""

    @pytest.mark.asyncio
    async def test_revoke_all_others_success(self, client: AsyncClient, db_session):
        """Should revoke all sessions except current."""
        # Get CSRF token
        csrf_response = await client.get("/healthz")
        csrf_token = csrf_response.cookies["csrf_token"]

        # Create user
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

        # Create 4 sessions
        sessions = []
        for _ in range(4):
            session_token = create_session_token()
            session = Session(
                user_id=user.id,
                token_hash=hash_token(session_token),
                created_at=now,
                expires_at=now + timedelta(hours=336),
            )
            db_session.add(session)
            sessions.append((session, session_token))

        await db_session.commit()

        # Use first session to revoke all others
        current_token = sessions[0][1]
        response = await client.post(
            "/api/v1/auth/sessions/revoke-all-others",
            cookies={"ff_sess": current_token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["revoked_count"] == 3  # 4 total - 1 current = 3 revoked

        # Verify other sessions were revoked
        for session, _ in sessions[1:]:
            await db_session.refresh(session)
            assert session.revoked_at is not None

        # Verify current session was NOT revoked
        await db_session.refresh(sessions[0][0])
        assert sessions[0][0].revoked_at is None

    @pytest.mark.asyncio
    async def test_revoke_all_others_with_no_other_sessions(
        self, client: AsyncClient, db_session
    ):
        """Should handle case with no other sessions gracefully."""
        # Get CSRF token
        csrf_response = await client.get("/healthz")
        csrf_token = csrf_response.cookies["csrf_token"]

        # Create user with single session
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

        session_token = create_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(session_token),
            created_at=now,
            expires_at=now + timedelta(hours=336),
        )
        db_session.add(session)
        await db_session.commit()

        # Revoke all others (there are none)
        response = await client.post(
            "/api/v1/auth/sessions/revoke-all-others",
            cookies={"ff_sess": session_token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["revoked_count"] == 0


class TestSessionCleanup:
    """Test automated session cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, db_session):
        """Should delete expired sessions."""
        # Create user
        now = datetime.now(UTC)
        user = User(
            email="cleanup@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create expired session
        expired_session = Session(
            user_id=user.id,
            token_hash=hash_token("expired"),
            created_at=now - timedelta(days=15),
            expires_at=now - timedelta(days=1),
        )
        db_session.add(expired_session)

        # Create active session
        active_session = Session(
            user_id=user.id,
            token_hash=hash_token("active"),
            created_at=now,
            expires_at=now + timedelta(hours=336),
        )
        db_session.add(active_session)

        await db_session.commit()

        # Run cleanup
        deleted_count = await cleanup_expired_sessions(db_session)

        assert deleted_count == 1

        # Verify expired session was deleted
        from sqlalchemy import select

        stmt = select(Session).where(Session.user_id == user.id)
        result = await db_session.execute(stmt)
        remaining_sessions = result.scalars().all()

        assert len(remaining_sessions) == 1
        assert remaining_sessions[0].id == active_session.id

    @pytest.mark.asyncio
    async def test_cleanup_old_rotated_sessions(self, db_session):
        """Should delete rotated sessions older than 90 days."""
        # Create user
        now = datetime.now(UTC)
        user = User(
            email="rotated@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create old rotated session (100 days ago)
        old_rotated = Session(
            user_id=user.id,
            token_hash=hash_token("old_rotated"),
            created_at=now - timedelta(days=100),
            expires_at=now + timedelta(hours=336),
            rotated_at=now - timedelta(days=100),
        )
        db_session.add(old_rotated)

        # Create recent rotated session (30 days ago)
        recent_rotated = Session(
            user_id=user.id,
            token_hash=hash_token("recent_rotated"),
            created_at=now - timedelta(days=30),
            expires_at=now + timedelta(hours=336),
            rotated_at=now - timedelta(days=30),
        )
        db_session.add(recent_rotated)

        await db_session.commit()

        # Run cleanup
        deleted_count = await cleanup_expired_sessions(db_session)

        assert deleted_count == 1

        # Verify only old rotated session was deleted
        from sqlalchemy import select

        stmt = select(Session).where(Session.user_id == user.id)
        result = await db_session.execute(stmt)
        remaining_sessions = result.scalars().all()

        assert len(remaining_sessions) == 1
        assert remaining_sessions[0].id == recent_rotated.id

    @pytest.mark.asyncio
    async def test_cleanup_expired_magic_links(self, db_session):
        """Should delete expired magic link tokens."""
        # Create user
        now = datetime.now(UTC)
        user = User(
            email="magiccleanup@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create expired magic link
        expired_token = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token("expired"),
            purpose="login",
            created_at=now - timedelta(hours=2),
            expires_at=now - timedelta(hours=1),
        )
        db_session.add(expired_token)

        # Create active magic link
        active_token = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token("active"),
            purpose="login",
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        db_session.add(active_token)

        await db_session.commit()

        # Run cleanup
        deleted_count = await cleanup_expired_magic_links(db_session)

        assert deleted_count == 1

        # Verify only active token remains
        from sqlalchemy import select

        stmt = select(MagicLinkToken).where(MagicLinkToken.user_id == user.id)
        result = await db_session.execute(stmt)
        remaining_tokens = result.scalars().all()

        assert len(remaining_tokens) == 1
        assert remaining_tokens[0].id == active_token.id
