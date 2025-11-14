import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select

from app.api.v1.auth import WebAuthnCredentialResponse, list_webauthn_credentials
from app.core.security import create_session_token, hash_token
from app.db.models.auth import Session, User, WebAuthnCredential

pytestmark = [pytest.mark.security, pytest.mark.integration]


@pytest.mark.asyncio
async def test_list_credentials_requires_auth_401(db_session):
    token_none: HTTPAuthorizationCredentials | None = None
    with pytest.raises(HTTPException) as ei:
        await list_webauthn_credentials(db=db_session, token=token_none)
    assert ei.value.status_code == 401


@pytest.mark.asyncio
async def test_list_credentials_invalid_session_401(db_session):
    # Pass a token that doesn't match any active session
    token = create_session_token()
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as ei:
        await list_webauthn_credentials(db=db_session, token=creds)
    assert ei.value.status_code == 401


@pytest.mark.asyncio
async def test_list_credentials_success_returns_user_credentials(db_session):
    now = datetime.now(UTC)
    user = User(
        email=f"creds-{uuid.uuid4().hex}@test.com",
        is_active=True,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Seed a credential
    cred = WebAuthnCredential(
        user_id=user.id,
        credential_id=bytes.fromhex("aabbcc"),
        public_key=b"\x01\x02",
        sign_count=0,
        created_at=now,
        updated_at=now,
    )
    db_session.add(cred)

    # Seed a valid session
    raw_token = create_session_token()
    sess = Session(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        created_at=now,
        expires_at=now + timedelta(days=10),
    )
    db_session.add(sess)
    await db_session.commit()

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=raw_token)
    result = await list_webauthn_credentials(db=db_session, token=creds)

    # Validate response
    assert isinstance(result, list)
    assert len(result) == 1
    item: WebAuthnCredentialResponse = result[0]
    assert item.id == cred.credential_id.hex()
    # Ensure it's reading from DB
    rows = (await db_session.execute(select(WebAuthnCredential))).scalars().all()
    assert len(rows) == 1
