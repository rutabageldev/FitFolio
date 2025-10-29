import os
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from webauthn.helpers import options_to_json_dict

from app.api.deps import get_current_session_with_rotation
from app.core.email import send_email
from app.core.redis_client import get_redis
from app.core.security import (
    check_account_lockout,
    create_session_token,
    hash_token,
    reset_failed_login_attempts,
)
from app.core.webauthn import get_webauthn_manager
from app.db.database import get_db
from app.db.models.auth import (
    LoginEvent,
    MagicLinkToken,
    Session,
    User,
    WebAuthnCredential,
)
from app.observability.logging import get_logger

router = APIRouter(prefix="/auth", tags=["authentication"])

security = HTTPBearer(auto_error=False)
log = get_logger()


class MagicLinkRequest(BaseModel):
    email: EmailStr


class MagicLinkResponse(BaseModel):
    message: str = "If an account exists with this email, a magic link has been sent."


class MagicLinkVerifyRequest(BaseModel):
    token: str


class MagicLinkVerifyResponse(BaseModel):
    message: str
    session_token: str


class WebAuthnRegisterStartRequest(BaseModel):
    email: EmailStr


class WebAuthnRegisterStartResponse(BaseModel):
    options: dict
    challenge_id: str


class WebAuthnRegisterFinishRequest(BaseModel):
    email: EmailStr
    credential: dict
    challenge_id: str


class WebAuthnRegisterFinishResponse(BaseModel):
    message: str
    credential_id: str


class WebAuthnAuthenticateStartRequest(BaseModel):
    email: EmailStr


class WebAuthnAuthenticateStartResponse(BaseModel):
    options: dict
    challenge_id: str


class WebAuthnAuthenticateFinishRequest(BaseModel):
    email: EmailStr
    credential: dict
    challenge_id: str


class WebAuthnAuthenticateFinishResponse(BaseModel):
    message: str
    session_token: str


class WebAuthnCredentialResponse(BaseModel):
    id: str
    nickname: str | None
    created_at: datetime
    last_used_at: datetime | None


class EmailVerifyRequest(BaseModel):
    token: str


class EmailVerifyResponse(BaseModel):
    message: str
    session_token: str


class EmailResendVerificationRequest(BaseModel):
    email: EmailStr


class EmailResendVerificationResponse(BaseModel):
    message: str = "If an account exists, a verification email has been sent."


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

    is_new_user = False
    if not user:
        # Create new user (email not verified yet)
        now_utc = datetime.now(UTC)
        user = User(
            email=request.email.lower(),
            is_active=True,
            is_email_verified=False,
            created_at=now_utc,
            updated_at=now_utc,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        is_new_user = True

    # For new users, send email verification instead of magic link
    now = datetime.now(UTC)
    if is_new_user:
        # Send email verification
        verification_token = secrets.token_urlsafe(32)
        verification_token_hash = hash_token(verification_token)
        expires_at = now + timedelta(hours=24)  # 24 hour TTL

        magic_link_token = MagicLinkToken(
            user_id=user.id,
            token_hash=verification_token_hash,
            purpose="email_verification",
            created_at=now,
            expires_at=expires_at,
            requested_ip=http_request.client.host if http_request else None,
            user_agent=http_request.headers.get("user-agent") if http_request else None,
        )
        db.add(magic_link_token)

        # Log new user creation
        login_event = LoginEvent(
            user_id=user.id,
            event_type="user_created",
            created_at=now,
            ip=http_request.client.host if http_request else None,
            user_agent=http_request.headers.get("user-agent") if http_request else None,
        )
        db.add(login_event)

        await db.commit()

        # Send verification email
        verification_url = (
            f"http://localhost:5173/auth/verify-email?token={verification_token}"
        )
        email_body = f"""
        Welcome to FitFolio!

        Please verify your email address by clicking the link below:

        {verification_url}

        This link will expire in 24 hours.

        If you didn't create this account, you can safely ignore this email.
        """

        await send_email(
            to=request.email,
            subject="Welcome to FitFolio - Verify your email",
            body=email_body.strip(),
        )

        return MagicLinkResponse()

    # For existing users, send magic link
    expires_at = now + timedelta(minutes=15)  # 15 minute TTL

    # Store token in dedicated magic_link_tokens table
    magic_link_token = MagicLinkToken(
        user_id=user.id,
        token_hash=token_hash,
        purpose="login",
        created_at=now,
        expires_at=expires_at,
        requested_ip=http_request.client.host if http_request else None,
        user_agent=http_request.headers.get("user-agent") if http_request else None,
    )
    db.add(magic_link_token)

    # Log the login attempt
    login_event = LoginEvent(
        user_id=user.id,
        event_type="magic_link_requested",
        created_at=datetime.now(UTC),
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
    # Find the magic link token (must be for login purpose)
    stmt = select(MagicLinkToken).where(
        MagicLinkToken.token_hash == hash_token(request.token),
        MagicLinkToken.purpose == "login",
        MagicLinkToken.expires_at > datetime.now(UTC),
        MagicLinkToken.used_at.is_(None),  # Single-use enforcement
    )
    result = await db.execute(stmt)
    magic_link_token = result.scalar_one_or_none()

    if not magic_link_token:
        # Invalid token - log failed attempt if we can identify the user
        # (In this case, we can't without the token, so just return error)
        log.warning(
            "magic_link_verification_failed",
            reason="invalid_or_expired_token",
            ip=http_request.client.host if http_request else None,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired magic link token",
        )

    # Get the user
    user_stmt = select(User).where(User.id == magic_link_token.user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is inactive or not found",
        )

    # Enforce email verification
    if not user.is_email_verified:
        log.warning(
            "login_attempt_unverified_email",
            user_id=str(user.id),
            ip=http_request.client.host if http_request else None,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Please verify your email address before logging in. "
                "Check your inbox for the verification link."
            ),
        )

    # Check if account is locked due to failed attempts
    redis_client = await get_redis()
    is_locked, seconds_remaining = await check_account_lockout(redis_client, user.id)

    if is_locked:
        # Log lockout attempt
        login_event = LoginEvent(
            user_id=user.id,
            event_type="login_attempt_locked",
            created_at=datetime.now(UTC),
            ip=http_request.client.host if http_request else None,
            user_agent=http_request.headers.get("user-agent") if http_request else None,
            extra={"seconds_remaining": seconds_remaining},
        )
        db.add(login_event)
        await db.commit()

        log.warning(
            "account_locked_login_attempt",
            user_id=str(user.id),
            seconds_remaining=seconds_remaining,
            ip=http_request.client.host if http_request else None,
        )

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Account temporarily locked due to too many failed attempts. "
                f"Try again in {seconds_remaining} seconds."
            ),
        )

    # Mark magic link token as used
    now = datetime.now(UTC)
    magic_link_token.used_at = now
    magic_link_token.used_ip = http_request.client.host if http_request else None

    # Create a new session for the user
    session_token = create_session_token()
    session_token_hash = hash_token(session_token)

    new_session = Session(
        user_id=user.id,
        token_hash=session_token_hash,
        created_at=now,
        expires_at=now + timedelta(hours=336),  # 14 days
        ip=http_request.client.host if http_request else None,
        user_agent=http_request.headers.get("user-agent") if http_request else None,
    )
    db.add(new_session)

    # Update user's last login
    user.last_login_at = now
    user.updated_at = now  # Explicitly set for SQLite test compatibility

    # Reset failed login attempts on successful login
    await reset_failed_login_attempts(redis_client, user.id)

    # Log the successful login
    login_event = LoginEvent(
        user_id=user.id,
        event_type="magic_link_verified_success",
        created_at=now,
        ip=http_request.client.host if http_request else None,
        user_agent=http_request.headers.get("user-agent") if http_request else None,
        extra={"magic_link_token_id": str(magic_link_token.id)},
    )
    db.add(login_event)

    await db.commit()

    log.info(
        "magic_link_login_success",
        user_id=str(user.id),
        ip=http_request.client.host if http_request else None,
    )

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


@router.post("/webauthn/register/start", response_model=WebAuthnRegisterStartResponse)
async def start_webauthn_registration(
    request: WebAuthnRegisterStartRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Start WebAuthn passkey registration process.
    """
    from app.core.challenge_storage import store_challenge

    # Get or create user
    user_stmt = select(User).where(User.email == request.email.lower())
    result = await db.execute(user_stmt)
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

    # Get existing credentials to exclude
    cred_stmt = select(WebAuthnCredential).where(WebAuthnCredential.user_id == user.id)
    cred_result = await db.execute(cred_stmt)
    existing_credentials = cred_result.scalars().all()

    exclude_credentials = []
    for cred in existing_credentials:
        exclude_credentials.append(
            {
                "id": cred.credential_id.hex(),
                "transports": cred.transports or [],
            }
        )

    # Generate registration options
    webauthn_manager = get_webauthn_manager()
    options = webauthn_manager.generate_registration_options(
        user_id=str(user.id),
        user_name=user.email,
        user_display_name=user.email,
        exclude_credentials=exclude_credentials,
    )

    # Store challenge in Redis (server-side, secure)
    challenge_hex = options.challenge.hex()
    challenge_id = await store_challenge(
        user_email=request.email.lower(),
        challenge_hex=challenge_hex,
        challenge_type="registration",
    )

    # Log registration attempt
    login_event = LoginEvent(
        user_id=user.id,
        event_type="webauthn_register_start",
        created_at=datetime.now(UTC),
        extra={"challenge_id": challenge_id},
    )
    db.add(login_event)
    await db.commit()

    return WebAuthnRegisterStartResponse(
        options=options_to_json_dict(options),
        challenge_id=challenge_id,
    )


@router.post("/webauthn/register/finish", response_model=WebAuthnRegisterFinishResponse)
async def finish_webauthn_registration(
    request_data: WebAuthnRegisterFinishRequest,
    response: Response,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Complete WebAuthn passkey registration.

    If user is already authenticated (has session), rotates the session
    as this is a privilege escalation event.
    """
    from app.api.deps import get_optional_session_with_rotation
    from app.core.challenge_storage import retrieve_and_delete_challenge
    from app.core.session_rotation import check_and_rotate_if_needed

    # Get user
    stmt = select(User).where(User.email == request_data.email.lower())
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Retrieve challenge from Redis (single-use)
    challenge_data = await retrieve_and_delete_challenge(
        challenge_id=request_data.challenge_id,
        challenge_type="registration",
    )

    if challenge_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired challenge. Please start registration again.",
        )

    stored_email, challenge_hex = challenge_data

    # Verify the challenge was issued for this user
    if stored_email != request_data.email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Challenge was issued for a different user",
        )

    # Verify the registration response
    webauthn_manager = get_webauthn_manager()

    try:
        verification_result = webauthn_manager.verify_registration_response(
            credential=request_data.credential,
            expected_rp_id=webauthn_manager.rp_id,
            expected_origin=webauthn_manager.origin,
            expected_challenge=bytes.fromhex(challenge_hex),
            expected_user_id=str(user.id),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    # Create the credential record
    credential = WebAuthnCredential(
        user_id=user.id,
        credential_id=bytes.fromhex(verification_result["credential_id"]),
        public_key=verification_result["public_key"],
        sign_count=verification_result["sign_count"],
        transports=verification_result.get("transports"),
        backed_up=verification_result.get("backed_up"),
        uv_available=verification_result.get("uv_available"),
    )
    db.add(credential)

    # Log the credential creation
    login_event = LoginEvent(
        user_id=user.id,
        event_type="webauthn_credential_created",
        created_at=datetime.now(UTC),
        extra={"credential_id": verification_result["credential_id"]},
    )
    db.add(login_event)

    await db.commit()

    # Rotate session if user is already authenticated (privilege escalation)
    current_session, _ = await get_optional_session_with_rotation(
        response=response,
        session_token=http_request.cookies.get("ff_sess"),
        db=db,
    )

    if current_session:
        # Force rotation due to credential addition (privilege escalation)
        new_session, new_token = await check_and_rotate_if_needed(
            current_session,
            db,
            force_reason="credential_added",
        )

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

    return WebAuthnRegisterFinishResponse(
        message="Passkey registered successfully!",
        credential_id=verification_result["credential_id"],
    )


@router.post(
    "/webauthn/authenticate/start", response_model=WebAuthnAuthenticateStartResponse
)
async def start_webauthn_authentication(
    request: WebAuthnAuthenticateStartRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Start WebAuthn passkey authentication.
    """
    from app.core.challenge_storage import store_challenge

    # Get user
    user_stmt = select(User).where(User.email == request.email.lower())
    result = await db.execute(user_stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Get user's credentials
    cred_stmt = select(WebAuthnCredential).where(WebAuthnCredential.user_id == user.id)
    cred_result = await db.execute(cred_stmt)
    credentials = cred_result.scalars().all()

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No passkeys registered for this user",
        )

    allow_credentials = []
    for cred in credentials:
        allow_credentials.append(
            {
                "id": cred.credential_id.hex(),
                "transports": cred.transports or [],
            }
        )

    # Generate authentication options
    webauthn_manager = get_webauthn_manager()
    options = webauthn_manager.generate_authentication_options(
        allow_credentials=allow_credentials,
    )

    # Store challenge in Redis (server-side, secure)
    challenge_hex = options.challenge.hex()
    challenge_id = await store_challenge(
        user_email=request.email.lower(),
        challenge_hex=challenge_hex,
        challenge_type="authentication",
    )

    # Log authentication attempt
    login_event = LoginEvent(
        user_id=user.id,
        event_type="webauthn_auth_start",
        created_at=datetime.now(UTC),
        extra={"challenge_id": challenge_id, "credential_count": len(credentials)},
    )
    db.add(login_event)
    await db.commit()

    return WebAuthnAuthenticateStartResponse(
        options=options_to_json_dict(options),
        challenge_id=challenge_id,
    )


@router.post(
    "/webauthn/authenticate/finish", response_model=WebAuthnAuthenticateFinishResponse
)
async def finish_webauthn_authentication(
    request: WebAuthnAuthenticateFinishRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    http_request: Request = None,
):
    """
    Complete WebAuthn passkey authentication.
    """
    from app.core.challenge_storage import retrieve_and_delete_challenge

    # Get user
    user_stmt = select(User).where(User.email == request.email.lower())
    result = await db.execute(user_stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Retrieve challenge from Redis (single-use)
    challenge_data = await retrieve_and_delete_challenge(
        challenge_id=request.challenge_id,
        challenge_type="authentication",
    )

    if challenge_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired challenge. Please start authentication again.",
        )

    stored_email, challenge_hex = challenge_data

    # Verify the challenge was issued for this user
    if stored_email != request.email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Challenge was issued for a different user",
        )

    # Get the credential being used
    credential_id = request.credential.get("id")
    if not credential_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credential ID is required",
        )

    cred_stmt = select(WebAuthnCredential).where(
        WebAuthnCredential.user_id == user.id,
        WebAuthnCredential.credential_id == bytes.fromhex(credential_id),
    )
    cred_result = await db.execute(cred_stmt)
    credential = cred_result.scalar_one_or_none()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credential",
        )

    # Verify the authentication response
    webauthn_manager = get_webauthn_manager()

    try:
        verification_result = webauthn_manager.verify_authentication_response(
            credential=request.credential,
            expected_rp_id=webauthn_manager.rp_id,
            expected_origin=webauthn_manager.origin,
            expected_challenge=bytes.fromhex(challenge_hex),
            credential_public_key=credential.public_key,
            credential_sign_count=credential.sign_count,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    # Update credential sign count
    credential.sign_count = verification_result["new_sign_count"]
    credential.updated_at = datetime.now(UTC)

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
        event_type="webauthn_login",
        created_at=datetime.now(UTC),
        ip=http_request.client.host if http_request else None,
        user_agent=http_request.headers.get("user-agent") if http_request else None,
        extra={"credential_id": credential_id},
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

    return WebAuthnAuthenticateFinishResponse(
        message="Passkey authentication successful!",
        session_token=session_token,
    )


@router.get("/webauthn/credentials", response_model=list[WebAuthnCredentialResponse])
async def list_webauthn_credentials(
    db: AsyncSession = Depends(get_db),
    token: HTTPAuthorizationCredentials | None = Depends(security),
):
    """
    List user's WebAuthn credentials.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # Find the session
    session_stmt = select(Session).where(
        Session.token_hash == hash_token(token.credentials),
        Session.expires_at > datetime.now(UTC),
        Session.revoked_at.is_(None),
    )
    result = await db.execute(session_stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    # Get user's credentials
    cred_stmt = select(WebAuthnCredential).where(
        WebAuthnCredential.user_id == session.user_id
    )
    cred_result = await db.execute(cred_stmt)
    credentials = cred_result.scalars().all()

    return [
        WebAuthnCredentialResponse(
            id=cred.credential_id.hex(),
            nickname=cred.nickname,
            created_at=cred.created_at,
            last_used_at=cred.updated_at
            if cred.updated_at != cred.created_at
            else None,
        )
        for cred in credentials
    ]


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
    session_and_user: tuple[Session, User] = Depends(get_current_session_with_rotation),
):
    """
    Get current user information.

    Automatically rotates session if older than configured threshold (7 days).
    """
    session, user = session_and_user

    return {
        "id": str(user.id),
        "email": user.email,
        "is_email_verified": user.is_email_verified,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
        "session_created_at": session.created_at,
        "session_expires_at": session.expires_at,
    }


@router.post("/email/verify", response_model=EmailVerifyResponse)
async def verify_email(
    request: EmailVerifyRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    http_request: Request = None,
):
    """
    Verify email address using verification token.
    Creates a session and logs user in automatically.
    """
    # Find the verification token
    stmt = select(MagicLinkToken).where(
        MagicLinkToken.token_hash == hash_token(request.token),
        MagicLinkToken.purpose == "email_verification",
        MagicLinkToken.expires_at > datetime.now(UTC),
        MagicLinkToken.used_at.is_(None),
    )
    result = await db.execute(stmt)
    verification_token = result.scalar_one_or_none()

    if not verification_token:
        log.warning(
            "email_verification_failed",
            reason="invalid_or_expired_token",
            ip=http_request.client.host if http_request else None,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    # Get the user
    user_stmt = select(User).where(User.id == verification_token.user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is inactive or not found",
        )

    # Mark email as verified
    now = datetime.now(UTC)
    user.is_email_verified = True
    user.updated_at = now

    # Mark verification token as used
    verification_token.used_at = now
    verification_token.used_ip = http_request.client.host if http_request else None

    # Create a new session for the user (auto-login after verification)
    session_token = create_session_token()
    session_token_hash = hash_token(session_token)

    new_session = Session(
        user_id=user.id,
        token_hash=session_token_hash,
        created_at=now,
        expires_at=now + timedelta(hours=336),  # 14 days
        ip=http_request.client.host if http_request else None,
        user_agent=http_request.headers.get("user-agent") if http_request else None,
    )
    db.add(new_session)

    # Update user's last login
    user.last_login_at = now

    # Log the successful verification
    login_event = LoginEvent(
        user_id=user.id,
        event_type="email_verified",
        created_at=now,
        ip=http_request.client.host if http_request else None,
        user_agent=http_request.headers.get("user-agent") if http_request else None,
        extra={"verification_token_id": str(verification_token.id)},
    )
    db.add(login_event)

    await db.commit()

    log.info(
        "email_verification_success",
        user_id=str(user.id),
        ip=http_request.client.host if http_request else None,
    )

    # Set session cookie
    response.set_cookie(
        key="ff_sess",
        value=session_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=336 * 3600,  # 14 days
    )

    return EmailVerifyResponse(
        message="Email verified successfully. You are now logged in.",
        session_token=session_token,
    )


@router.post(
    "/email/resend-verification", response_model=EmailResendVerificationResponse
)
async def resend_verification_email(
    request: EmailResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
    http_request: Request = None,
):
    """
    Resend email verification link.
    Always returns success to prevent email enumeration.
    """
    # Find user by email
    stmt = select(User).where(User.email == request.email.lower())
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user and user.is_active and not user.is_email_verified:
        # Generate new verification token
        token = secrets.token_urlsafe(32)
        token_hash = hash_token(token)

        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=24)  # 24 hour TTL for verification

        verification_token = MagicLinkToken(
            user_id=user.id,
            token_hash=token_hash,
            purpose="email_verification",
            created_at=now,
            expires_at=expires_at,
            requested_ip=http_request.client.host if http_request else None,
            user_agent=http_request.headers.get("user-agent") if http_request else None,
        )
        db.add(verification_token)

        # Log the resend request
        login_event = LoginEvent(
            user_id=user.id,
            event_type="email_verification_resent",
            created_at=now,
            ip=http_request.client.host if http_request else None,
            user_agent=http_request.headers.get("user-agent") if http_request else None,
        )
        db.add(login_event)

        await db.commit()

        # Send verification email
        verification_url = f"http://localhost:5173/auth/verify-email?token={token}"
        email_body = f"""
        Welcome to FitFolio!

        Please verify your email address by clicking the link below:

        {verification_url}

        This link will expire in 24 hours.

        If you didn't create this account, you can safely ignore this email.
        """

        await send_email(
            to=request.email,
            subject="Verify your FitFolio email address",
            body=email_body.strip(),
        )

        log.info(
            "email_verification_resent",
            user_id=str(user.id),
            ip=http_request.client.host if http_request else None,
        )

    return EmailResendVerificationResponse()
