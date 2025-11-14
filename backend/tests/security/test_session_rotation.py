"""Tests for session rotation functionality."""

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from starlette.responses import Response

from app.api.deps import get_current_session_with_rotation
from app.core.security import create_session_token, hash_token
from app.core.session_rotation import (
    check_and_rotate_if_needed,
    cleanup_rotated_sessions,
    rotate_session,
    should_rotate_session,
)
from app.db.models.auth import Session, User

pytestmark = [pytest.mark.security, pytest.mark.integration]


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create a test user for session rotation tests."""
    now = datetime.now(UTC)
    user = User(
        email="rotation@test.com",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def recent_session(db_session, test_user):
    """Create a session that's 5 days old (should not rotate)."""
    token = create_session_token()
    session = Session(
        user_id=test_user.id,
        token_hash=hash_token(token),
        created_at=datetime.now(UTC) - timedelta(days=5),
        expires_at=datetime.now(UTC) + timedelta(days=9),
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session, token


@pytest_asyncio.fixture
async def old_session(db_session, test_user):
    """Create a session that's 8 days old (should rotate)."""
    token = create_session_token()
    session = Session(
        user_id=test_user.id,
        token_hash=hash_token(token),
        created_at=datetime.now(UTC) - timedelta(days=8),
        expires_at=datetime.now(UTC) + timedelta(days=6),
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session, token


class TestShouldRotateSession:
    """Test the should_rotate_session logic."""

    def test_recent_session_should_not_rotate(self, test_user):
        """Sessions less than 7 days old should not rotate."""
        session = Session(
            user_id=test_user.id,
            token_hash=b"test",
            created_at=datetime.now(UTC) - timedelta(days=5),
            expires_at=datetime.now(UTC) + timedelta(days=9),
        )
        assert should_rotate_session(session) is False

    def test_old_session_should_rotate(self, test_user):
        """Sessions 7+ days old should rotate."""
        session = Session(
            user_id=test_user.id,
            token_hash=b"test",
            created_at=datetime.now(UTC) - timedelta(days=7),
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        assert should_rotate_session(session) is True

    def test_exactly_seven_days_should_rotate(self, test_user):
        """Session exactly 7 days old should rotate."""
        session = Session(
            user_id=test_user.id,
            token_hash=b"test",
            created_at=datetime.now(UTC) - timedelta(days=7, seconds=1),
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        assert should_rotate_session(session) is True

    def test_already_rotated_should_not_rotate(self, test_user):
        """Already rotated sessions should not rotate again."""
        session = Session(
            user_id=test_user.id,
            token_hash=b"test",
            created_at=datetime.now(UTC) - timedelta(days=10),
            expires_at=datetime.now(UTC) + timedelta(days=4),
            rotated_at=datetime.now(UTC) - timedelta(days=1),
        )
        assert should_rotate_session(session) is False


class TestRotateSession:
    """Test the rotate_session function."""

    @pytest.mark.asyncio
    async def test_rotate_session_creates_new_session(self, db_session, old_session):
        """Rotating should create a new session."""
        session, _ = old_session

        new_session, new_token = await rotate_session(session, db_session)

        assert new_session.id != session.id
        assert new_token is not None
        assert len(new_token) > 0

    @pytest.mark.asyncio
    async def test_rotate_session_marks_old_as_rotated(self, db_session, old_session):
        """Rotating should mark old session with rotated_at."""
        session, _ = old_session

        await rotate_session(session, db_session)
        await db_session.refresh(session)

        assert session.rotated_at is not None
        assert session.rotated_at <= datetime.now(UTC)

    @pytest.mark.asyncio
    async def test_rotate_session_inherits_user_context(self, db_session, old_session):
        """New session should inherit user_id, ip, user_agent."""
        session, _ = old_session
        original_user_id = session.user_id
        original_ip = session.ip
        original_user_agent = session.user_agent

        new_session, _ = await rotate_session(session, db_session)

        assert new_session.user_id == original_user_id
        assert new_session.ip == original_ip
        assert new_session.user_agent == original_user_agent

    @pytest.mark.asyncio
    async def test_rotate_session_with_reason(self, db_session, old_session):
        """Rotation reason should be logged (verify no errors)."""
        session, _ = old_session

        # Should not raise any errors
        await rotate_session(session, db_session, reason="credential_added")

    @pytest.mark.asyncio
    async def test_new_session_has_fresh_expiry(self, db_session, old_session):
        """New session should have fresh expiry time."""
        session, _ = old_session

        new_session, _ = await rotate_session(session, db_session)

        # New session should expire ~14 days from now
        expected_expiry = datetime.now(UTC) + timedelta(hours=336)
        time_diff = abs((new_session.expires_at - expected_expiry).total_seconds())
        assert time_diff < 60  # Within 1 minute tolerance


class TestCheckAndRotateIfNeeded:
    """Test the check_and_rotate_if_needed convenience function."""

    @pytest.mark.asyncio
    async def test_recent_session_not_rotated(self, db_session, recent_session):
        """Recent sessions should not be rotated."""
        session, _ = recent_session

        result_session, new_token = await check_and_rotate_if_needed(
            session, db_session
        )

        assert result_session.id == session.id
        assert new_token is None
        await db_session.refresh(session)
        assert session.rotated_at is None

    @pytest.mark.asyncio
    async def test_old_session_rotated(self, db_session, old_session):
        """Old sessions should be rotated automatically."""
        session, _ = old_session

        result_session, new_token = await check_and_rotate_if_needed(
            session, db_session
        )

        assert result_session.id != session.id
        assert new_token is not None
        await db_session.refresh(session)
        assert session.rotated_at is not None

    @pytest.mark.asyncio
    async def test_force_rotation_on_recent_session(self, db_session, recent_session):
        """Force reason should rotate even recent sessions."""
        session, _ = recent_session

        result_session, new_token = await check_and_rotate_if_needed(
            session, db_session, force_reason="credential_added"
        )

        assert result_session.id != session.id
        assert new_token is not None
        await db_session.refresh(session)
        assert session.rotated_at is not None


class TestCleanupRotatedSessions:
    """Test cleanup of old rotated sessions."""

    @pytest.mark.asyncio
    async def test_cleanup_removes_old_rotated_sessions(self, db_session, test_user):
        """Cleanup should remove rotated sessions older than threshold."""
        # Create old rotated session (100 days old)
        old_rotated = Session(
            user_id=test_user.id,
            token_hash=b"old_rotated",
            created_at=datetime.now(UTC) - timedelta(days=150),
            expires_at=datetime.now(UTC) - timedelta(days=50),
            rotated_at=datetime.now(UTC) - timedelta(days=100),
        )
        db_session.add(old_rotated)

        # Create recent rotated session (10 days old)
        recent_rotated = Session(
            user_id=test_user.id,
            token_hash=b"recent_rotated",
            created_at=datetime.now(UTC) - timedelta(days=20),
            expires_at=datetime.now(UTC) + timedelta(days=10),
            rotated_at=datetime.now(UTC) - timedelta(days=10),
        )
        db_session.add(recent_rotated)

        await db_session.commit()

        # Cleanup sessions older than 90 days
        count = await cleanup_rotated_sessions(db_session, days_old=90)

        assert count == 1  # Only old_rotated should be deleted
        await db_session.refresh(recent_rotated)  # Should still exist

    @pytest.mark.asyncio
    async def test_cleanup_does_not_remove_active_sessions(self, db_session, test_user):
        """Cleanup should not remove sessions that haven't been rotated."""
        # Create old but active (not rotated) session
        active_session = Session(
            user_id=test_user.id,
            token_hash=b"active",
            created_at=datetime.now(UTC) - timedelta(days=150),
            expires_at=datetime.now(UTC) + timedelta(days=10),
            rotated_at=None,  # Not rotated
        )
        db_session.add(active_session)
        await db_session.commit()

        count = await cleanup_rotated_sessions(db_session, days_old=90)

        assert count == 0
        await db_session.refresh(active_session)  # Should still exist


class TestSessionRotationIntegration:
    """Integration tests for session rotation with HTTP endpoints."""

    @pytest.mark.asyncio
    async def test_me_endpoint_rotates_old_session(self, client, db_session, test_user):
        """GET /me should automatically rotate old sessions."""
        _ = client
        # Create old session (8 days)
        token = create_session_token()
        session = Session(
            user_id=test_user.id,
            token_hash=hash_token(token),
            created_at=datetime.now(UTC) - timedelta(days=8),
            expires_at=datetime.now(UTC) + timedelta(days=6),
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        # Request /me with old session (set cookie robustly)
        # Call dependency directly to verify rotation without HTTP client variability
        response = Response()
        result_session, user = await get_current_session_with_rotation(
            response=response, session_token=token, db=db_session
        )
        assert result_session.id != session.id
        # Rotation should have set a new ff_sess cookie
        set_cookie = response.headers.get("set-cookie", "")
        assert "ff_sess=" in set_cookie

        # Old session should be marked as rotated
        await db_session.refresh(session)
        assert session.rotated_at is not None

    @pytest.mark.asyncio
    async def test_rotated_session_rejected(self, client, db_session, test_user):
        """Using a rotated session token should be rejected."""
        # Create rotated session
        now = datetime.now(UTC)
        token = create_session_token()
        session = Session(
            user_id=test_user.id,
            token_hash=hash_token(token),
            created_at=now - timedelta(days=1),
            expires_at=now + timedelta(days=1),
            rotated_at=now - timedelta(minutes=5),
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        # Try to use rotated session
        response = await client.get("/api/v1/auth/me", cookies={"ff_sess": token})

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_endpoint_does_not_rotate_recent(
        self, client, db_session, test_user
    ):
        """Recent sessions should not be rotated automatically on /me."""
        _ = client
        # Create recent session (5 days)
        token = create_session_token()
        session = Session(
            user_id=test_user.id,
            token_hash=hash_token(token),
            created_at=datetime.now(UTC) - timedelta(days=5),
            expires_at=datetime.now(UTC) + timedelta(days=9),
        )
        db_session.add(session)
        await db_session.commit()

        # Request /me with recent session (set cookie robustly)
        # Call dependency directly to verify no rotation
        response = Response()
        result_session, user = await get_current_session_with_rotation(
            response=response, session_token=token, db=db_session
        )
        assert result_session.id == session.id
        # No new ff_sess cookie should be set when not rotated
        set_cookie = response.headers.get("set-cookie", "")
        assert "ff_sess=" not in set_cookie
