"""Tests for comprehensive audit logging."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_session_token, hash_token
from app.db.models.auth import LoginEvent, MagicLinkToken, Session, User


class TestAuditLogEvents:
    """Test that all authentication flows create audit log entries."""

    @pytest.mark.asyncio
    async def test_magic_link_request_creates_event(
        self, client: AsyncClient, db_session
    ):
        """Magic link request should create login event."""
        await client.post(
            "/api/v1/auth/magic-link/start", json={"email": "audit1@test.com"}
        )

        # Verify event was created
        stmt = select(LoginEvent).where(LoginEvent.event_type == "user_created")
        result = await db_session.execute(stmt)
        event = result.scalar_one_or_none()

        assert event is not None
        assert event.event_type == "user_created"

    @pytest.mark.asyncio
    async def test_magic_link_verification_creates_event(
        self, client: AsyncClient, db_session
    ):
        """Magic link verification should create login event."""
        # Create verified user
        now = datetime.now(UTC)
        user = User(
            email="audit2@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create magic link token
        token = "audit_test_token"
        magic_link = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token),
            purpose="login",
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        db_session.add(magic_link)
        await db_session.commit()

        # Verify magic link
        await client.post("/api/v1/auth/magic-link/verify", json={"token": token})

        # Verify event was created
        stmt = select(LoginEvent).where(
            LoginEvent.event_type == "magic_link_verified_success",
            LoginEvent.user_id == user.id,
        )
        result = await db_session.execute(stmt)
        event = result.scalar_one_or_none()

        assert event is not None
        assert event.event_type == "magic_link_verified_success"
        assert event.extra is not None
        assert "magic_link_token_id" in event.extra

    @pytest.mark.asyncio
    async def test_email_verification_creates_event(
        self, client: AsyncClient, db_session
    ):
        """Email verification should create login event."""
        # Create unverified user
        now = datetime.now(UTC)
        user = User(
            email="audit3@test.com",
            is_active=True,
            is_email_verified=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create verification token
        token = "verification_audit_token"
        verification_token = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token),
            purpose="email_verification",
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )
        db_session.add(verification_token)
        await db_session.commit()

        # Verify email
        await client.post("/api/v1/auth/email/verify", json={"token": token})

        # Verify event was created
        stmt = select(LoginEvent).where(
            LoginEvent.event_type == "email_verified", LoginEvent.user_id == user.id
        )
        result = await db_session.execute(stmt)
        event = result.scalar_one_or_none()

        assert event is not None
        assert event.event_type == "email_verified"
        assert event.extra is not None
        assert "verification_token_id" in event.extra

    @pytest.mark.asyncio
    async def test_resend_verification_creates_event(
        self, client: AsyncClient, db_session
    ):
        """Resending verification should create login event."""
        # Create unverified user
        now = datetime.now(UTC)
        user = User(
            email="audit4@test.com",
            is_active=True,
            is_email_verified=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()

        # Resend verification
        await client.post(
            "/api/v1/auth/email/resend-verification", json={"email": "audit4@test.com"}
        )

        # Verify event was created
        stmt = select(LoginEvent).where(
            LoginEvent.event_type == "email_verification_resent",
            LoginEvent.user_id == user.id,
        )
        result = await db_session.execute(stmt)
        event = result.scalar_one_or_none()

        assert event is not None
        assert event.event_type == "email_verification_resent"

    @pytest.mark.asyncio
    async def test_account_lockout_creates_event(self, client: AsyncClient, db_session):
        """Account lockout attempts should create login events."""
        from app.core.redis_client import get_redis
        from app.core.security import (
            LOCKOUT_FAILED_ATTEMPTS_THRESHOLD,
            record_failed_login,
        )

        # Create verified user
        now = datetime.now(UTC)
        user = User(
            email="audit5@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Lock the account
        redis_client = await get_redis()
        for _ in range(LOCKOUT_FAILED_ATTEMPTS_THRESHOLD):
            await record_failed_login(redis_client, user.id)

        # Create magic link token
        token = "lockout_audit_token"
        magic_link = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token),
            purpose="login",
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        db_session.add(magic_link)
        await db_session.commit()

        # Try to verify magic link (should be locked)
        await client.post("/api/v1/auth/magic-link/verify", json={"token": token})

        # Verify lockout event was created
        stmt = select(LoginEvent).where(
            LoginEvent.event_type == "login_attempt_locked",
            LoginEvent.user_id == user.id,
        )
        result = await db_session.execute(stmt)
        event = result.scalar_one_or_none()

        assert event is not None
        assert event.event_type == "login_attempt_locked"
        assert event.extra is not None
        assert "seconds_remaining" in event.extra


class TestAuditLogEndpoints:
    """Test audit log query endpoints."""

    @pytest.mark.asyncio
    async def test_get_audit_events_requires_auth(self, client: AsyncClient):
        """Audit log endpoint should require authentication."""
        response = await client.get("/api/v1/admin/audit/events")

        # Should be unauthorized
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_audit_events_with_auth(self, client: AsyncClient, db_session):
        """Authenticated users can access audit logs."""
        # Create user with session
        now = datetime.now(UTC)
        user = User(
            email="admin@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create session
        session_token = create_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(session_token),
            created_at=now,
            expires_at=now + timedelta(hours=336),
        )
        db_session.add(session)

        # Create some audit events
        for i in range(5):
            event = LoginEvent(
                user_id=user.id,
                event_type="test_event",
                created_at=now + timedelta(minutes=i),
            )
            db_session.add(event)

        await db_session.commit()

        # Query audit logs
        response = await client.get(
            "/api/v1/admin/audit/events", cookies={"ff_sess": session_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "total" in data
        assert len(data["entries"]) >= 5

    @pytest.mark.asyncio
    async def test_get_audit_events_filter_by_user(
        self, client: AsyncClient, db_session
    ):
        """Should filter audit events by user_id."""
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

        # Create events for both users
        for i in range(3):
            db_session.add(
                LoginEvent(
                    user_id=user1.id,
                    event_type="user1_event",
                    created_at=now + timedelta(minutes=i),
                )
            )
        for i in range(2):
            db_session.add(
                LoginEvent(
                    user_id=user2.id,
                    event_type="user2_event",
                    created_at=now + timedelta(minutes=i),
                )
            )

        # Create session for user1
        session_token = create_session_token()
        session = Session(
            user_id=user1.id,
            token_hash=hash_token(session_token),
            created_at=now,
            expires_at=now + timedelta(hours=336),
        )
        db_session.add(session)
        await db_session.commit()

        # Query audit logs filtered by user2
        response = await client.get(
            f"/api/v1/admin/audit/events?user_id={user2.id}",
            cookies={"ff_sess": session_token},
        )

        assert response.status_code == 200
        data = response.json()
        # Should only return user2 events
        for entry in data["entries"]:
            assert entry["user_id"] == str(user2.id)

    @pytest.mark.asyncio
    async def test_get_audit_events_filter_by_event_type(
        self, client: AsyncClient, db_session
    ):
        """Should filter audit events by event_type."""
        # Create user
        now = datetime.now(UTC)
        user = User(
            email="filter@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create events with different types
        db_session.add(
            LoginEvent(
                user_id=user.id,
                event_type="magic_link_verified_success",
                created_at=now,
            )
        )
        db_session.add(
            LoginEvent(user_id=user.id, event_type="webauthn_login", created_at=now)
        )

        # Create session
        session_token = create_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(session_token),
            created_at=now,
            expires_at=now + timedelta(hours=336),
        )
        db_session.add(session)
        await db_session.commit()

        # Query filtered by event_type
        response = await client.get(
            "/api/v1/admin/audit/events?event_type=magic_link_verified_success",
            cookies={"ff_sess": session_token},
        )

        assert response.status_code == 200
        data = response.json()
        # Should only return magic_link events
        for entry in data["entries"]:
            assert entry["event_type"] == "magic_link_verified_success"

    @pytest.mark.asyncio
    async def test_get_event_types(self, client: AsyncClient, db_session):
        """Should return list of unique event types."""
        # Create user
        now = datetime.now(UTC)
        user = User(
            email="types@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create events with different types
        for event_type in ["type_a", "type_b", "type_c"]:
            db_session.add(
                LoginEvent(user_id=user.id, event_type=event_type, created_at=now)
            )

        # Create session
        session_token = create_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(session_token),
            created_at=now,
            expires_at=now + timedelta(hours=336),
        )
        db_session.add(session)
        await db_session.commit()

        # Get event types
        response = await client.get(
            "/api/v1/admin/audit/event-types", cookies={"ff_sess": session_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert "event_types" in data
        assert "type_a" in data["event_types"]
        assert "type_b" in data["event_types"]
        assert "type_c" in data["event_types"]

    @pytest.mark.asyncio
    async def test_audit_events_pagination(self, client: AsyncClient, db_session):
        """Should properly paginate audit events."""
        # Create user
        now = datetime.now(UTC)
        user = User(
            email="pagination@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create 10 events
        for i in range(10):
            db_session.add(
                LoginEvent(
                    user_id=user.id,
                    event_type="pagination_test",
                    created_at=now + timedelta(minutes=i),
                )
            )

        # Create session
        session_token = create_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(session_token),
            created_at=now,
            expires_at=now + timedelta(hours=336),
        )
        db_session.add(session)
        await db_session.commit()

        # Get first page (5 items)
        response = await client.get(
            "/api/v1/admin/audit/events?page=1&page_size=5",
            cookies={"ff_sess": session_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 5
        assert data["has_more"] is True

        # Get second page
        response = await client.get(
            "/api/v1/admin/audit/events?page=2&page_size=5",
            cookies={"ff_sess": session_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) >= 5
        assert data["page"] == 2
