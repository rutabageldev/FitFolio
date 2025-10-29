"""Background cleanup tasks for session and token management."""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from sqlalchemy.engine import Result

from app.db.database import AsyncSessionLocal
from app.db.models.auth import MagicLinkToken, Session
from app.observability.logging import get_logger

log = get_logger()


async def cleanup_expired_sessions(db: AsyncSession) -> int:
    """
    Delete expired and rotated sessions.

    Cleanup criteria:
    - Sessions where expires_at < now() (expired)
    - Sessions where rotated_at is not null AND rotated_at < now() - 90 days
      (old rotated sessions, keep for 90 days for audit trail)

    Returns:
        Number of sessions deleted
    """
    now = datetime.now(UTC)
    ninety_days_ago = now - timedelta(days=90)

    # Delete expired sessions
    expired_stmt = delete(Session).where(Session.expires_at < now)

    # Delete old rotated sessions (90+ days old)
    rotated_stmt = delete(Session).where(
        Session.rotated_at.is_not(None), Session.rotated_at < ninety_days_ago
    )

    # Execute deletions
    expired_result: Result = await db.execute(expired_stmt)
    rotated_result: Result = await db.execute(rotated_stmt)

    await db.commit()

    total_deleted = expired_result.rowcount + rotated_result.rowcount  # type: ignore[attr-defined]

    log.info(
        "session_cleanup_completed",
        expired_count=expired_result.rowcount,  # type: ignore[attr-defined]
        rotated_count=rotated_result.rowcount,  # type: ignore[attr-defined]
        total_deleted=total_deleted,
    )

    return total_deleted


async def cleanup_expired_magic_links(db: AsyncSession) -> int:
    """
    Delete expired magic link tokens.

    Deletes tokens where expires_at < now()

    Returns:
        Number of tokens deleted
    """
    now = datetime.now(UTC)

    stmt = delete(MagicLinkToken).where(MagicLinkToken.expires_at < now)

    result: Result = await db.execute(stmt)
    await db.commit()

    deleted_count = result.rowcount  # type: ignore[attr-defined]

    log.info("magic_link_cleanup_completed", deleted_count=deleted_count)

    return deleted_count


async def run_cleanup_job():
    """
    Run all cleanup tasks.

    This should be called periodically (e.g., daily via cron).
    """
    log.info("cleanup_job_started")

    # Get database session
    async with AsyncSessionLocal() as db:
        try:
            sessions_deleted = await cleanup_expired_sessions(db)
            tokens_deleted = await cleanup_expired_magic_links(db)

            log.info(
                "cleanup_job_completed",
                sessions_deleted=sessions_deleted,
                tokens_deleted=tokens_deleted,
            )

        except Exception as e:
            log.error("cleanup_job_failed", error=str(e), exc_info=True)
            raise


async def schedule_cleanup_job(interval_hours: int = 24):
    """
    Schedule cleanup job to run periodically.

    Args:
        interval_hours: Hours between cleanup runs (default: 24)

    This function runs indefinitely and should be run as a background task.
    """
    while True:
        try:
            await run_cleanup_job()
        except Exception as e:
            log.error("cleanup_job_error", error=str(e), exc_info=True)

        # Wait for next run
        await asyncio.sleep(interval_hours * 3600)
