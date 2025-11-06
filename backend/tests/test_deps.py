"""Tests for app/api/deps.py - session management dependencies."""

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from fastapi import HTTPException, Response

from app.api.deps import (
    get_current_session_with_rotation,
    get_optional_session_with_rotation,
)
from app.core.security import create_session_token, hash_token
from app.db.models.auth import Session, User


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create a test user."""
    now = datetime.now(UTC)
    user = User(
        email="test@example.com",
        is_active=True,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_get_current_session_no_token(db_session):
    """Test get_current_session_with_rotation without token raises 401."""
    response = Response()

    with pytest.raises(HTTPException) as exc_info:
        await get_current_session_with_rotation(response, None, db_session)

    assert exc_info.value.status_code == 401
    assert "Not authenticated" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_session_invalid_token(db_session):
    """Test get_current_session_with_rotation with invalid token raises 401."""
    response = Response()

    with pytest.raises(HTTPException) as exc_info:
        await get_current_session_with_rotation(response, "invalid_token", db_session)

    assert exc_info.value.status_code == 401
    assert "Invalid or expired session" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_session_expired_token(db_session, test_user):
    """Test get_current_session_with_rotation with expired session."""
    # Create an expired session
    token = create_session_token()
    token_hash = hash_token(token)
    now = datetime.now(UTC)
    expired_session = Session(
        user_id=test_user.id,
        token_hash=token_hash,
        created_at=now,
        expires_at=now - timedelta(hours=1),  # Expired 1 hour ago
        ip="127.0.0.1",
        user_agent="test",
    )
    db_session.add(expired_session)
    await db_session.commit()

    response = Response()

    with pytest.raises(HTTPException) as exc_info:
        await get_current_session_with_rotation(response, token, db_session)

    assert exc_info.value.status_code == 401
    assert "Invalid or expired session" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_session_revoked_token(db_session, test_user):
    """Test get_current_session_with_rotation with revoked session."""
    # Create a revoked session
    token = create_session_token()
    token_hash = hash_token(token)
    now = datetime.now(UTC)
    revoked_session = Session(
        user_id=test_user.id,
        token_hash=token_hash,
        created_at=now,
        expires_at=now + timedelta(days=7),
        revoked_at=now,  # Revoked
        ip="127.0.0.1",
        user_agent="test",
    )
    db_session.add(revoked_session)
    await db_session.commit()

    response = Response()

    with pytest.raises(HTTPException) as exc_info:
        await get_current_session_with_rotation(response, token, db_session)

    assert exc_info.value.status_code == 401
    assert "Invalid or expired session" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_session_rotated_token(db_session, test_user):
    """Test get_current_session_with_rotation rejects rotated sessions."""
    # Create a rotated session
    token = create_session_token()
    token_hash = hash_token(token)
    now = datetime.now(UTC)
    rotated_session = Session(
        user_id=test_user.id,
        token_hash=token_hash,
        created_at=now,
        expires_at=now + timedelta(days=7),
        rotated_at=now,  # Already rotated
        ip="127.0.0.1",
        user_agent="test",
    )
    db_session.add(rotated_session)
    await db_session.commit()

    response = Response()

    with pytest.raises(HTTPException) as exc_info:
        await get_current_session_with_rotation(response, token, db_session)

    assert exc_info.value.status_code == 401
    assert "Invalid or expired session" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_session_inactive_user(db_session, test_user):
    """Test get_current_session_with_rotation with inactive user."""
    # Create a valid session
    token = create_session_token()
    token_hash = hash_token(token)
    now = datetime.now(UTC)
    session = Session(
        user_id=test_user.id,
        token_hash=token_hash,
        created_at=now,
        expires_at=now + timedelta(days=7),
        ip="127.0.0.1",
        user_agent="test",
    )
    db_session.add(session)

    # Deactivate the user
    test_user.is_active = False
    test_user.updated_at = datetime.now(UTC)  # Manually set updated_at for SQLite
    await db_session.commit()

    response = Response()

    with pytest.raises(HTTPException) as exc_info:
        await get_current_session_with_rotation(response, token, db_session)

    assert exc_info.value.status_code == 401
    assert "User account is inactive" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_session_valid_recent_session(db_session, test_user):
    """Test get_current_session_with_rotation with recent valid session."""
    # Create a recent valid session (no rotation needed)
    token = create_session_token()
    token_hash = hash_token(token)
    session = Session(
        user_id=test_user.id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(days=7),
        created_at=datetime.now(UTC),  # Just created
        ip="127.0.0.1",
        user_agent="test",
    )
    db_session.add(session)
    await db_session.commit()

    response = Response()

    returned_session, returned_user = await get_current_session_with_rotation(
        response, token, db_session
    )

    assert returned_session.id == session.id
    assert returned_user.id == test_user.id
    # No new cookie should be set (no rotation)
    assert "ff_sess" not in response.headers.get("set-cookie", "")


@pytest.mark.asyncio
async def test_get_current_session_old_session_triggers_rotation(db_session, test_user):
    """Test get_current_session_with_rotation rotates old sessions."""
    # Create an old session (>7 days, needs rotation)
    token = create_session_token()
    token_hash = hash_token(token)
    old_session = Session(
        user_id=test_user.id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(days=7),
        created_at=datetime.now(UTC) - timedelta(days=8),  # 8 days old
        ip="127.0.0.1",
        user_agent="test",
    )
    db_session.add(old_session)
    await db_session.commit()

    response = Response()

    returned_session, returned_user = await get_current_session_with_rotation(
        response, token, db_session
    )

    # Should get a new session (rotation happened)
    assert returned_session.id != old_session.id
    assert returned_user.id == test_user.id

    # Old session should be marked as rotated
    await db_session.refresh(old_session)
    assert old_session.rotated_at is not None

    # New cookie should be set
    assert "ff_sess" in response.headers.get("set-cookie", "")


@pytest.mark.asyncio
async def test_get_current_session_respects_cookie_secure_env(
    db_session, test_user, monkeypatch
):
    """Test get_current_session_with_rotation respects COOKIE_SECURE env var."""
    # Set COOKIE_SECURE to true
    monkeypatch.setenv("COOKIE_SECURE", "true")

    # Create an old session that will trigger rotation
    token = create_session_token()
    token_hash = hash_token(token)
    old_session = Session(
        user_id=test_user.id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(days=7),
        created_at=datetime.now(UTC) - timedelta(days=8),
        ip="127.0.0.1",
        user_agent="test",
    )
    db_session.add(old_session)
    await db_session.commit()

    response = Response()

    await get_current_session_with_rotation(response, token, db_session)

    # Check that secure flag is set in cookie
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "secure" in set_cookie_header.lower() or "Secure" in set_cookie_header


@pytest.mark.asyncio
async def test_get_optional_session_no_token_returns_none(db_session):
    """Test get_optional_session_with_rotation returns None without token."""
    response = Response()

    session, user = await get_optional_session_with_rotation(response, None, db_session)

    assert session is None
    assert user is None


@pytest.mark.asyncio
async def test_get_optional_session_invalid_token_returns_none(db_session):
    """Test get_optional_session_with_rotation returns None with invalid token."""
    response = Response()

    session, user = await get_optional_session_with_rotation(
        response, "invalid_token", db_session
    )

    assert session is None
    assert user is None


@pytest.mark.asyncio
async def test_get_optional_session_valid_token_returns_session(db_session, test_user):
    """Test get_optional_session_with_rotation returns session with valid token."""
    # Create a valid session
    token = create_session_token()
    token_hash = hash_token(token)
    now = datetime.now(UTC)
    session = Session(
        user_id=test_user.id,
        token_hash=token_hash,
        created_at=now,
        expires_at=now + timedelta(days=7),
        ip="127.0.0.1",
        user_agent="test",
    )
    db_session.add(session)
    await db_session.commit()

    response = Response()

    returned_session, returned_user = await get_optional_session_with_rotation(
        response, token, db_session
    )

    assert returned_session is not None
    assert returned_session.id == session.id
    assert returned_user is not None
    assert returned_user.id == test_user.id
