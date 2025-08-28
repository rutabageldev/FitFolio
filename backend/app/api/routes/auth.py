import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.email import send_email
from app.core.security import create_session_token, hash_token
from app.db.database import get_db
from app.db.models.auth import LoginEvent, Session, User

router = APIRouter(prefix="/auth", tags=["authentication"])

security = HTTPBearer(auto_error=False)


class MagicLinkRequest(BaseModel):
    email: EmailStr


class MagicLinkResponse(BaseModel):
    message: str = "If an account exists with this email, a magic link has been sent."


class MagicLinkVerifyRequest(BaseModel):
    token: str


class MagicLinkVerifyResponse(BaseModel):
    message: str
    session_token: str


@router.post("/magic-link/start", response_model=MagicLinkResponse)
async def start_magic_link_login(
    request: MagicLinkRequest,
    db: AsyncSession = Depends(get_db),
    http_request: Request = None,
):
    """
    Start magic link login process.
    Always returns success to prevent email enumeration.
    """
    # Generate a secure token
    token = secrets.token_urlsafe(32)
    token_hash = hash_token(token)

    # Check if user exists, create if not
    stmt = select(User).where(User.email == request.email.lower())
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        # Create new user
        user = User(
            email=request.email.lower(),
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Create magic link token with expiration
    expires_at = datetime.now(UTC) + timedelta(minutes=15)  # 15 minute TTL

    # Store token hash in database (you might want a separate MagicLinkToken model)
    # For now, we'll use a simple approach with the session table
    magic_link_session = Session(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        ip=http_request.client.host if http_request else None,
        user_agent=http_request.headers.get("user-agent") if http_request else None,
    )
    db.add(magic_link_session)

    # Log the login attempt
    login_event = LoginEvent(
        user_id=user.id,
        event_type="magic_link_requested",
        ip=http_request.client.host if http_request else None,
        user_agent=http_request.headers.get("user-agent") if http_request else None,
    )
    db.add(login_event)

    await db.commit()

    # Send magic link email
    magic_link_url = f"http://localhost:5173/auth/verify?token={token}"
    email_body = f"""
    Hello!

    Click the link below to sign in to FitFolio:

    {magic_link_url}

    This link will expire in 15 minutes.

    If you didn't request this link, you can safely ignore this email.
    """

    await send_email(
        to=request.email,
        subject="Sign in to FitFolio",
        body=email_body.strip(),
    )

    return MagicLinkResponse()


@router.post("/magic-link/verify", response_model=MagicLinkVerifyResponse)
async def verify_magic_link(
    request: MagicLinkVerifyRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    http_request: Request = None,
):
    """
    Verify magic link token and create session.
    """
    # Find the session with this token
    stmt = select(Session).where(
        Session.token_hash == hash_token(request.token),
        Session.expires_at > datetime.now(UTC),
        Session.revoked_at.is_(None),
    )
    result = await db.execute(stmt)
    magic_link_session = result.scalar_one_or_none()

    if not magic_link_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired magic link token",
        )

    # Get the user
    user_stmt = select(User).where(User.id == magic_link_session.user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is inactive or not found",
        )

    # Revoke the magic link token
    magic_link_session.revoked_at = datetime.now(UTC)

    # Create a new session for the user
    session_token = create_session_token()
    session_token_hash = hash_token(session_token)

    new_session = Session(
        user_id=user.id,
        token_hash=session_token_hash,
        expires_at=datetime.now(UTC) + timedelta(hours=336),  # 14 days
        ip=http_request.client.host if http_request else None,
        user_agent=http_request.headers.get("user-agent") if http_request else None,
    )
    db.add(new_session)

    # Update user's last login
    user.last_login_at = datetime.now(UTC)

    # Log the successful login
    login_event = LoginEvent(
        user_id=user.id,
        event_type="magic_link_used",
        ip=http_request.client.host if http_request else None,
        user_agent=http_request.headers.get("user-agent") if http_request else None,
    )
    db.add(login_event)

    await db.commit()

    # Set session cookie
    response.set_cookie(
        key="ff_sess",
        value=session_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=336 * 3600,  # 14 days in seconds
    )

    return MagicLinkVerifyResponse(
        message="Login successful!", session_token=session_token
    )


@router.post("/logout")
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_db),
    token: HTTPAuthorizationCredentials | None = Depends(security),
):
    """
    Logout and invalidate session.
    """
    if token:
        # Find and revoke the session
        stmt = select(Session).where(
            Session.token_hash == hash_token(token.credentials),
            Session.revoked_at.is_(None),
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if session:
            session.revoked_at = datetime.now(UTC)
            await db.commit()

    # Clear the session cookie
    response.delete_cookie(key="ff_sess")

    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: HTTPAuthorizationCredentials | None = Depends(security),
):
    """
    Get current user information.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # Find the session
    stmt = select(Session).where(
        Session.token_hash == hash_token(token.credentials),
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

    # Get the user
    user_stmt = select(User).where(User.id == session.user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or not found",
        )

    return {
        "id": str(user.id),
        "email": user.email,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
    }
