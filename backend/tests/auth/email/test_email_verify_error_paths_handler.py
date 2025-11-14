import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from app.api.v1.auth import EmailVerifyRequest, verify_email
from app.core.security import create_magic_link_token, hash_token
from app.db.models.auth import MagicLinkToken, User

pytestmark = [pytest.mark.security, pytest.mark.integration]


def make_request() -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/email/verify",
        "headers": [(b"user-agent", b"pytest")],
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_verify_email_invalid_token_returns_400(db_session):
    # No token in DB -> should hit invalid token path (HTTP 400)
    http_req = make_request()
    resp = Response()
    req = EmailVerifyRequest(token="not-a-real-token")
    with pytest.raises(HTTPException) as ei:
        await verify_email(req, resp, http_req, db_session)
    assert ei.value.status_code == 400


@pytest.mark.asyncio
async def test_verify_email_inactive_user_returns_400(db_session):
    # Seed inactive user and a valid email verification token
    now = datetime.now(UTC)
    email = f"verify-inactive-{uuid.uuid4().hex}@test.com"
    user = User(
        email=email,
        is_active=False,
        is_email_verified=False,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    raw_token = create_magic_link_token()
    token = MagicLinkToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        purpose="email_verification",
        created_at=now,
        expires_at=now + timedelta(hours=24),
    )
    db_session.add(token)
    await db_session.commit()

    http_req = make_request()
    resp = Response()
    req = EmailVerifyRequest(token=raw_token)
    with pytest.raises(HTTPException) as ei:
        await verify_email(req, resp, http_req, db_session)
    assert ei.value.status_code == 400
