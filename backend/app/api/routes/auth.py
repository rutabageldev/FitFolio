import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from webauthn.helpers import options_to_json_dict

from app.core.email import send_email
from app.core.security import create_session_token, hash_token
from app.core.webauthn import get_webauthn_manager
from app.db.database import get_db
from app.db.models.auth import LoginEvent, Session, User, WebAuthnCredential

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


class WebAuthnRegisterStartRequest(BaseModel):
    email: EmailStr


class WebAuthnRegisterStartResponse(BaseModel):
    options: dict
    challenge: str


class WebAuthnRegisterFinishRequest(BaseModel):
    email: EmailStr
    credential: dict
    challenge: str


class WebAuthnRegisterFinishResponse(BaseModel):
    message: str
    credential_id: str


class WebAuthnAuthenticateStartRequest(BaseModel):
    email: EmailStr


class WebAuthnAuthenticateStartResponse(BaseModel):
    options: dict
    challenge: str


class WebAuthnAuthenticateFinishRequest(BaseModel):
    email: EmailStr
    credential: dict
    challenge: str


class WebAuthnAuthenticateFinishResponse(BaseModel):
    message: str
    session_token: str


class WebAuthnCredentialResponse(BaseModel):
    id: str
    nickname: str | None
    created_at: datetime
    last_used_at: datetime | None


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


@router.post("/webauthn/register/start", response_model=WebAuthnRegisterStartResponse)
async def start_webauthn_registration(
    request: WebAuthnRegisterStartRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Start WebAuthn passkey registration process.
    """
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

    # Store challenge in session (in production, use Redis or similar)
    # For now, we'll return it in the response
    challenge = options.challenge.hex()

    return WebAuthnRegisterStartResponse(
        options=options_to_json_dict(options),
        challenge=challenge,
    )


@router.post("/webauthn/register/finish", response_model=WebAuthnRegisterFinishResponse)
async def finish_webauthn_registration(
    request: WebAuthnRegisterFinishRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Complete WebAuthn passkey registration.
    """
    # Get user
    stmt = select(User).where(User.email == request.email.lower())
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Verify the registration response
    webauthn_manager = get_webauthn_manager()

    try:
        verification_result = webauthn_manager.verify_registration_response(
            credential=request.credential,
            expected_rp_id=webauthn_manager.rp_id,
            expected_origin=webauthn_manager.origin,
            expected_challenge=bytes.fromhex(request.challenge),
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
        extra={"credential_id": verification_result["credential_id"]},
    )
    db.add(login_event)

    await db.commit()

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

    # Store challenge in session (in production, use Redis or similar)
    challenge = options.challenge.hex()

    return WebAuthnAuthenticateStartResponse(
        options=options_to_json_dict(options),
        challenge=challenge,
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
    # Get user
    user_stmt = select(User).where(User.email == request.email.lower())
    result = await db.execute(user_stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
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
            expected_challenge=bytes.fromhex(request.challenge),
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
