import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from starlette.requests import Request
from starlette.responses import Response

from app.api.v1.auth import (
    MagicLinkVerifyRequest,
    hash_token,
    verify_magic_link,
)
from app.db.models.auth import LoginEvent, MagicLinkToken, User

pytestmark = [pytest.mark.security, pytest.mark.integration]


def make_request(headers: dict[str, str] | None = None) -> Request:
    raw_headers = []
    for k, v in (headers or {}).items():
        raw_headers.append((k.lower().encode("latin-1"), v.encode("latin-1")))
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/magic-link/verify",
        "headers": raw_headers,
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_verify_precheck_locked_raises_429_and_logs_event(db_session):
    now = datetime.now(UTC)
    # Seed user and token matching the raw token we'll pass in request
    user = User(
        email=f"precheck-{uuid.uuid4().hex}@test.com",
        is_active=True,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    raw_token = f"tok-{uuid.uuid4().hex}"
    token = MagicLinkToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        purpose="login",
        created_at=now,
        expires_at=now + timedelta(minutes=10),
        used_at=None,
        requested_ip=None,
        used_ip=None,
        user_agent="ua-test",
    )
    db_session.add(token)
    await db_session.commit()

    http_req = make_request({"User-Agent": "ua-test"})
    request_model = MagicLinkVerifyRequest(token=raw_token)
    response = Response()

    async def _locked(_redis, _user_id):
        return True, 37

    with patch("app.api.v1.auth.check_account_lockout", _locked):
        with pytest.raises(HTTPException) as ei:
            await verify_magic_link(request_model, response, http_req, db_session)
    assert ei.value.status_code == 429
    assert "Account temporarily locked" in str(ei.value.detail)

    # Confirm LoginEvent was created with event_type 'login_attempt_locked'
    ev = (
        await db_session.execute(
            select(LoginEvent).where(
                LoginEvent.user_id == user.id,
                LoginEvent.event_type == "login_attempt_locked",
            )
        )
    ).scalar_one_or_none()
    assert ev is not None
