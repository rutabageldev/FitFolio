"""Tests for session management endpoints.

Tests for /sessions, /sessions/{id}, and /sessions/revoke-all-others endpoints.
"""

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.core.security import create_session_token, hash_token
from app.db.models.auth import Session, User


@pytest_asyncio.fixture
async def verified_user(db_session):
    """Create a verified user."""
    now = datetime.now(UTC)
    user = User(
        email="sessionuser@test.com",
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
async def user_with_multiple_sessions(db_session, verified_user):
    """Create user with multiple active sessions."""
    now = datetime.now(UTC)
    sessions = []

    for i in range(3):
        session_token = create_session_token()
        session = Session(
            user_id=verified_user.id,
            token_hash=hash_token(session_token),
            created_at=now - timedelta(hours=i),  # Different creation times
            expires_at=now + timedelta(hours=336 - i),
        )
        db_session.add(session)
        sessions.append((session, session_token))

    await db_session.commit()
    for session, _ in sessions:
        await db_session.refresh(session)

    return verified_user, sessions


@pytest_asyncio.fixture
async def csrf_token(client: AsyncClient):
    """Get CSRF token for requests."""
    response = await client.get("/healthz")
    return response.cookies["csrf_token"]


class TestListSessions:
    """Tests for GET /api/v1/auth/sessions endpoint."""

    @pytest.mark.asyncio
    async def test_list_sessions_single(
        self, client: AsyncClient, csrf_token, verified_user, db_session
    ):
        """Should list user's single session."""
        # Create session
        now = datetime.now(UTC)
        session_token = create_session_token()
        session = Session(
            user_id=verified_user.id,
            token_hash=hash_token(session_token),
            created_at=now,
            expires_at=now + timedelta(hours=336),
        )
        db_session.add(session)
        await db_session.commit()

        response = await client.get(
            "/api/v1/auth/sessions",
            cookies={"ff_sess": session_token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["is_current"] is True

    @pytest.mark.asyncio
    async def test_list_sessions_multiple(
        self, client: AsyncClient, csrf_token, user_with_multiple_sessions
    ):
        """Should list all user's sessions with current session marked."""
        user, sessions = user_with_multiple_sessions
        current_session, current_token = sessions[0]

        response = await client.get(
            "/api/v1/auth/sessions",
            cookies={"ff_sess": current_token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert len(data["sessions"]) == 3

        # Verify current session is marked
        current_sessions = [s for s in data["sessions"] if s["is_current"]]
        assert len(current_sessions) == 1
        assert current_sessions[0]["id"] == str(current_session.id)

    @pytest.mark.asyncio
    async def test_list_sessions_excludes_revoked(
        self, client: AsyncClient, csrf_token, user_with_multiple_sessions, db_session
    ):
        """Should exclude revoked sessions from list."""
        user, sessions = user_with_multiple_sessions
        current_session, current_token = sessions[0]
        revoked_session, _ = sessions[1]

        # Revoke one session
        revoked_session.revoked_at = datetime.now(UTC)
        await db_session.commit()

        response = await client.get(
            "/api/v1/auth/sessions",
            cookies={"ff_sess": current_token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 2  # Only active sessions

    @pytest.mark.asyncio
    async def test_list_sessions_unauthenticated(self, client: AsyncClient, csrf_token):
        """Should reject unauthenticated request."""
        response = await client.get(
            "/api/v1/auth/sessions",
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 401


class TestRevokeSession:
    """Tests for DELETE /api/v1/auth/sessions/{session_id} endpoint."""

    @pytest.mark.asyncio
    async def test_revoke_other_session(
        self, client: AsyncClient, csrf_token, user_with_multiple_sessions, db_session
    ):
        """Should revoke another session."""
        user, sessions = user_with_multiple_sessions
        current_session, current_token = sessions[0]
        target_session, _ = sessions[1]

        response = await client.delete(
            f"/api/v1/auth/sessions/{target_session.id}",
            cookies={"ff_sess": current_token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "revoked" in data["message"].lower()

        # Verify session was revoked in database
        await db_session.refresh(target_session)
        assert target_session.revoked_at is not None

    @pytest.mark.asyncio
    async def test_revoke_current_session_rejected(
        self, client: AsyncClient, csrf_token, user_with_multiple_sessions
    ):
        """Should reject attempt to revoke current session."""
        user, sessions = user_with_multiple_sessions
        current_session, current_token = sessions[0]

        response = await client.delete(
            f"/api/v1/auth/sessions/{current_session.id}",
            cookies={"ff_sess": current_token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 400
        assert "current session" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_session(
        self, client: AsyncClient, csrf_token, verified_user, db_session
    ):
        """Should return 404 for nonexistent session."""
        # Create session
        now = datetime.now(UTC)
        session_token = create_session_token()
        session = Session(
            user_id=verified_user.id,
            token_hash=hash_token(session_token),
            created_at=now,
            expires_at=now + timedelta(hours=336),
        )
        db_session.add(session)
        await db_session.commit()

        # Try to revoke fake session
        response = await client.delete(
            "/api/v1/auth/sessions/00000000-0000-0000-0000-000000000000",
            cookies={"ff_sess": session_token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_revoke_session_of_other_user(
        self, client: AsyncClient, csrf_token, db_session
    ):
        """Should return 404 for session belonging to another user (no enumeration)."""
        # Create two users with sessions
        now = datetime.now(UTC)

        user1 = User(
            email="user1@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user1)

        user2 = User(
            email="user2@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user2)
        await db_session.commit()
        await db_session.refresh(user1)
        await db_session.refresh(user2)

        # Create session for user1
        token1 = create_session_token()
        session1 = Session(
            user_id=user1.id,
            token_hash=hash_token(token1),
            created_at=now,
            expires_at=now + timedelta(hours=336),
        )
        db_session.add(session1)

        # Create session for user2
        token2 = create_session_token()
        session2 = Session(
            user_id=user2.id,
            token_hash=hash_token(token2),
            created_at=now,
            expires_at=now + timedelta(hours=336),
        )
        db_session.add(session2)
        await db_session.commit()
        await db_session.refresh(session1)
        await db_session.refresh(session2)

        # User1 tries to revoke user2's session
        response = await client.delete(
            f"/api/v1/auth/sessions/{session2.id}",
            cookies={"ff_sess": token1, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Should return 404 to prevent enumeration
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_revoke_already_revoked_session(
        self, client: AsyncClient, csrf_token, user_with_multiple_sessions, db_session
    ):
        """Should return 404 for already revoked session."""
        user, sessions = user_with_multiple_sessions
        current_session, current_token = sessions[0]
        target_session, _ = sessions[1]

        # Revoke the session first
        target_session.revoked_at = datetime.now(UTC)
        await db_session.commit()

        # Try to revoke again
        response = await client.delete(
            f"/api/v1/auth/sessions/{target_session.id}",
            cookies={"ff_sess": current_token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 404


class TestRevokeAllOtherSessions:
    """Tests for POST /api/v1/auth/sessions/revoke-all-others endpoint."""

    @pytest.mark.asyncio
    async def test_revoke_all_others_success(
        self, client: AsyncClient, csrf_token, user_with_multiple_sessions, db_session
    ):
        """Should revoke all sessions except current."""
        user, sessions = user_with_multiple_sessions
        current_session, current_token = sessions[0]

        response = await client.post(
            "/api/v1/auth/sessions/revoke-all-others",
            cookies={"ff_sess": current_token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["revoked_count"] == 2  # 2 other sessions revoked

        # Verify only current session is active
        await db_session.refresh(current_session)
        assert current_session.revoked_at is None

        # Verify other sessions are revoked
        for session, _ in sessions[1:]:
            await db_session.refresh(session)
            assert session.revoked_at is not None

    @pytest.mark.asyncio
    async def test_revoke_all_others_no_other_sessions(
        self, client: AsyncClient, csrf_token, verified_user, db_session
    ):
        """Should return 0 revoked count when no other sessions exist."""
        # Create single session
        now = datetime.now(UTC)
        session_token = create_session_token()
        session = Session(
            user_id=verified_user.id,
            token_hash=hash_token(session_token),
            created_at=now,
            expires_at=now + timedelta(hours=336),
        )
        db_session.add(session)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/sessions/revoke-all-others",
            cookies={"ff_sess": session_token, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["revoked_count"] == 0

    @pytest.mark.asyncio
    async def test_revoke_all_others_unauthenticated(
        self, client: AsyncClient, csrf_token
    ):
        """Should reject unauthenticated request."""
        response = await client.post(
            "/api/v1/auth/sessions/revoke-all-others",
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 401
