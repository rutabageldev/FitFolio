import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from starlette.requests import Request
from starlette.responses import Response

from app.api.v1.auth import EmailVerifyRequest, verify_email
from app.core.security import create_magic_link_token, hash_token
from app.db.models.auth import MagicLinkToken, Session, User

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
async def test_email_verify_success_marks_verified_creates_session_and_sets_cookie(
    db_session,
):
    now = datetime.now(UTC)
    user = User(
        email=f"emailverify-{uuid.uuid4().hex}@test.com",
        is_active=True,
        is_email_verified=False,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create valid email verification token
    raw_token = create_magic_link_token()
    token = MagicLinkToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        purpose="email_verification",
        created_at=now,
        expires_at=now + timedelta(hours=24),
        used_at=None,
        requested_ip=None,
        used_ip=None,
        user_agent="pytest",
    )
    db_session.add(token)
    await db_session.commit()
    await db_session.refresh(token)

    # Call handler
    resp = Response()
    http_req = make_request()
    req = EmailVerifyRequest(token=raw_token)
    result = await verify_email(req, resp, http_req, db_session)

    # Message and cookie
    assert "verified successfully" in result.message.lower()
    set_cookie = resp.headers.get("set-cookie", "")
    assert "ff_sess=" in set_cookie

    # User marked verified
    await db_session.refresh(user)
    assert user.is_email_verified is True

    # Session created
    rows = (
        (await db_session.execute(select(Session).where(Session.user_id == user.id)))
        .scalars()
        .all()
    )
    assert len(rows) == 1
