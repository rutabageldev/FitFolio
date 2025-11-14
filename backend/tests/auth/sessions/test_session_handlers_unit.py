import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.api.v1.auth import (
    ListSessionsResponse,
    RevokeAllOtherSessionsResponse,
    RevokeSessionResponse,
    list_sessions,
    revoke_all_other_sessions,
    revoke_session,
)
from app.db.models.auth import LoginEvent, Session, User

pytestmark = [pytest.mark.security, pytest.mark.integration]


@pytest.mark.asyncio
async def test_list_sessions_returns_all_with_is_current_and_total(db_session):
    now = datetime.now(UTC)
    user = User(
        email=f"sessions-{uuid.uuid4().hex}@test.com",
        is_active=True,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Seed two active sessions; second will be the "current" one
    s1 = Session(
        user_id=user.id,
        token_hash=b"t1",
        created_at=now - timedelta(hours=2),
        expires_at=now + timedelta(days=14),
    )
    s2 = Session(
        user_id=user.id,
        token_hash=b"t2",
        created_at=now - timedelta(hours=1),
        expires_at=now + timedelta(days=14),
    )
    db_session.add_all([s1, s2])
    await db_session.commit()
    await db_session.refresh(s1)
    await db_session.refresh(s2)

    # Call handler directly, injecting dependency tuple
    resp: ListSessionsResponse = await list_sessions(
        session_and_user=(s2, user), db=db_session
    )

    assert isinstance(resp, ListSessionsResponse)
    assert resp.total == 2
    # Sessions ordered by most recent created_at first; s2 should be first and current
    assert resp.sessions[0].id == str(s2.id)
    assert resp.sessions[0].is_current is True
    assert resp.sessions[1].id == str(s1.id)
    assert resp.sessions[1].is_current is False


@pytest.mark.asyncio
async def test_revoke_session_not_found_returns_404(db_session):
    now = datetime.now(UTC)
    user = User(
        email=f"revoke404-{uuid.uuid4().hex}@test.com",
        is_active=True,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Current session
    current = Session(
        user_id=user.id,
        token_hash=b"x",
        created_at=now,
        expires_at=now + timedelta(days=14),
    )
    db_session.add(current)
    await db_session.commit()
    await db_session.refresh(current)

    # Revoke a random UUID that doesn't exist -> 404 path
    with pytest.raises(Exception) as ei:
        await revoke_session(
            session_id=str(uuid.uuid4()),
            session_and_user=(current, user),
            db=db_session,
        )
    # FastAPI HTTPException; status_code checked via string
    # since direct type import not required
    assert "404" in str(ei.value)


@pytest.mark.asyncio
async def test_revoke_session_success_marks_revoked_and_logs(db_session):
    now = datetime.now(UTC)
    user = User(
        email=f"revokesuccess-{uuid.uuid4().hex}@test.com",
        is_active=True,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Current session + another active session to revoke
    current = Session(
        user_id=user.id,
        token_hash=b"cur",
        created_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=13),
    )
    other = Session(
        user_id=user.id,
        token_hash=b"other",
        created_at=now - timedelta(hours=2),
        expires_at=now + timedelta(days=10),
    )
    db_session.add_all([current, other])
    await db_session.commit()
    await db_session.refresh(current)
    await db_session.refresh(other)

    resp: RevokeSessionResponse = await revoke_session(
        session_id=str(other.id), session_and_user=(current, user), db=db_session
    )

    # Response
    assert resp.revoked_session_id == str(other.id)
    # Revoked
    await db_session.refresh(other)
    assert other.revoked_at is not None
    # LoginEvent logged
    events = (
        (
            await db_session.execute(
                select(LoginEvent).where(LoginEvent.user_id == user.id)
            )
        )
        .scalars()
        .all()
    )
    assert any(e.event_type == "session_revoked" for e in events)


@pytest.mark.asyncio
async def test_revoke_all_other_sessions_revokes_and_returns_count(db_session):
    now = datetime.now(UTC)
    user = User(
        email=f"revokeall-{uuid.uuid4().hex}@test.com",
        is_active=True,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Current session + two others
    current = Session(
        user_id=user.id,
        token_hash=b"cur2",
        created_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=13),
    )
    other1 = Session(
        user_id=user.id,
        token_hash=b"o1",
        created_at=now - timedelta(hours=3),
        expires_at=now + timedelta(days=10),
    )
    other2 = Session(
        user_id=user.id,
        token_hash=b"o2",
        created_at=now - timedelta(hours=2),
        expires_at=now + timedelta(days=10),
    )
    db_session.add_all([current, other1, other2])
    await db_session.commit()
    await db_session.refresh(current)
    await db_session.refresh(other1)
    await db_session.refresh(other2)

    resp: RevokeAllOtherSessionsResponse = await revoke_all_other_sessions(
        session_and_user=(current, user), db=db_session
    )

    # Count returned
    assert resp.revoked_count == 2
    # Others revoked, current not revoked
    await db_session.refresh(other1)
    await db_session.refresh(other2)
    await db_session.refresh(current)
    assert other1.revoked_at is not None
    assert other2.revoked_at is not None
    assert current.revoked_at is None
    # Event logged
    events = (
        (
            await db_session.execute(
                select(LoginEvent).where(LoginEvent.user_id == user.id)
            )
        )
        .scalars()
        .all()
    )
    assert any(e.event_type == "sessions_revoked_all_others" for e in events)
