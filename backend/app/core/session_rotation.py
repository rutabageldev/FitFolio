"""Session rotation utilities for security best practices."""

import os
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_session_token, hash_token
from app.db.models.auth import Session
from app.observability.logging import get_logger

log = get_logger()

# Configuration
SESSION_ROTATE_DAYS = int(os.getenv("SESSION_ROTATE_DAYS", "7"))


def should_rotate_session(session: Session) -> bool:
    """
    Determine if a session should be rotated based on time.

    Args:
        session: The session to check

    Returns:
        bool: True if rotation is needed, False otherwise
    """
    # Never rotate if already rotated
    if session.rotated_at is not None:
        return False

    # Check if session is older than rotation threshold
    rotation_threshold = timedelta(days=SESSION_ROTATE_DAYS)
    age = datetime.now(UTC) - session.created_at

    return age >= rotation_threshold


async def rotate_session(
    session: Session,
    db: AsyncSession,
    reason: str = "time_based",
) -> tuple[Session, str]:
    """
    Rotate a session by creating a new session and marking the old one as rotated.

    Args:
        session: The session to rotate
        db: Database session
        reason: Reason for rotation (for logging)

    Returns:
        tuple[Session, str]: New session object and new token (not hashed)

    Security notes:
        - Old session is marked as rotated (not deleted for audit trail)
        - New session inherits user_id, ip, user_agent
        - New token is cryptographically random
        - Rotation is logged for security monitoring
    """
    # Mark old session as rotated
    session.rotated_at = datetime.now(UTC)

    # Create new session token
    new_token = create_session_token()
    new_token_hash = hash_token(new_token)

    # Create new session with extended expiry
    now = datetime.now(UTC)
    new_session = Session(
        user_id=session.user_id,
        token_hash=new_token_hash,
        created_at=now,  # Explicitly set for database compatibility
        expires_at=now + timedelta(hours=336),  # 14 days
        ip=session.ip,
        user_agent=session.user_agent,
    )
    db.add(new_session)

    # Log the rotation
    log.info(
        "session_rotated",
        user_id=str(session.user_id),
        old_session_id=str(session.id),
        new_session_id=str(new_session.id),
        reason=reason,
        old_session_age_days=(datetime.now(UTC) - session.created_at).days,
    )

    await db.commit()
    await db.refresh(new_session)

    return new_session, new_token


async def check_and_rotate_if_needed(
    session: Session,
    db: AsyncSession,
    force_reason: str | None = None,
) -> tuple[Session, str | None]:
    """
    Check if session needs rotation and rotate if necessary.

    Args:
        session: Current session
        db: Database session
        force_reason: If provided, forces rotation with this reason

    Returns:
        tuple[Session, str | None]:
            - Updated or new session
            - New token if rotated (None if not rotated)
    """
    if force_reason:
        # Forced rotation (e.g., after credential addition)
        return await rotate_session(session, db, reason=force_reason)

    if should_rotate_session(session):
        # Time-based rotation
        return await rotate_session(session, db, reason="time_based")

    # No rotation needed
    return session, None


async def cleanup_rotated_sessions(db: AsyncSession, days_old: int = 90) -> int:
    """
    Clean up rotated sessions older than specified days (housekeeping).

    Args:
        db: Database session
        days_old: Delete rotated sessions older than this many days

    Returns:
        int: Number of sessions deleted

    Note:
        This is optional housekeeping. Rotated sessions provide audit trail
        but can be cleaned up after sufficient retention period.
    """
    cutoff_date = datetime.now(UTC) - timedelta(days=days_old)

    stmt = select(Session).where(
        Session.rotated_at.isnot(None),
        Session.rotated_at < cutoff_date,
    )
    result = await db.execute(stmt)
    old_sessions = result.scalars().all()

    count = len(old_sessions)
    for old_session in old_sessions:
        await db.delete(old_session)

    await db.commit()

    if count > 0:
        log.info("rotated_sessions_cleaned_up", count=count, days_old=days_old)

    return count
