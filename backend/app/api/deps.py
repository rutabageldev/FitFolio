"""API dependencies for session management and authentication."""

import os
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_token
from app.core.session_rotation import check_and_rotate_if_needed
from app.db.database import get_db
from app.db.models.auth import Session, User


async def get_current_session_with_rotation(
    response: Response,
    session_token: Annotated[str | None, Cookie(alias="ff_sess")] = None,
    db: AsyncSession = Depends(get_db),
) -> tuple[Session, User]:
    """
    Get current session and user, with automatic time-based rotation.

    If session needs rotation (>7 days old), issues new token in response cookie.

    Args:
        response: FastAPI response object (for setting new cookie)
        session_token: Session token from cookie
        db: Database session

    Returns:
        tuple[Session, User]: Current/new session and user

    Raises:
        HTTPException: 401 if session invalid/expired/revoked/rotated
    """
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # Find the session
    stmt = select(Session).where(
        Session.token_hash == hash_token(session_token),
        Session.expires_at > datetime.now(UTC),
        Session.revoked_at.is_(None),
        Session.rotated_at.is_(None),  # Don't accept rotated sessions
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    # Check if rotation is needed (time-based)
    session, new_token = await check_and_rotate_if_needed(session, db)

    # If rotated, set new cookie
    if new_token:
        cookie_secure = os.getenv("COOKIE_SECURE", "false").lower() == "true"
        response.set_cookie(
            key="ff_sess",
            value=new_token,
            httponly=True,
            secure=cookie_secure,
            samesite="lax",
            max_age=336 * 3600,  # 14 days
        )

    # Get the user
    user_stmt = select(User).where(User.id == session.user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )

    return session, user


async def get_optional_session_with_rotation(
    response: Response,
    session_token: Annotated[str | None, Cookie(alias="ff_sess")] = None,
    db: AsyncSession = Depends(get_db),
) -> tuple[Session | None, User | None]:
    """
    Get current session and user if authenticated, with rotation.

    Similar to get_current_session_with_rotation but returns None instead of
    raising 401 if not authenticated. Useful for endpoints that are optionally
    authenticated.

    Args:
        response: FastAPI response object (for setting new cookie)
        session_token: Session token from cookie
        db: Database session

    Returns:
        tuple[Session | None, User | None]: Session and user if authenticated,
            (None, None) otherwise
    """
    if not session_token:
        return None, None

    try:
        return await get_current_session_with_rotation(response, session_token, db)
    except HTTPException:
        return None, None


async def get_session_allow_inactive(
    response: Response,
    session_token: Annotated[str | None, Cookie(alias="ff_sess")] = None,
    db: AsyncSession = Depends(get_db),
) -> tuple[Session, User]:
    """
    Get current session and user, allowing inactive users.

    This is intended for admin endpoints that want to return 403 for inactive
    users rather than failing at the dependency layer with 401.
    """
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    stmt = select(Session).where(
        Session.token_hash == hash_token(session_token),
        Session.expires_at > datetime.now(UTC),
        Session.revoked_at.is_(None),
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    session, new_token = await check_and_rotate_if_needed(session, db)
    if new_token:
        cookie_secure = os.getenv("COOKIE_SECURE", "false").lower() == "true"
        response.set_cookie(
            key="ff_sess",
            value=new_token,
            httponly=True,
            secure=cookie_secure,
            samesite="lax",
            max_age=336 * 3600,
        )

    user_stmt = select(User).where(User.id == session.user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one()
    return session, user
