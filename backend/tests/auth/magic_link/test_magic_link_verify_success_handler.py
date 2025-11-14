import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from starlette.requests import Request
from starlette.responses import Response

from app.api.v1.auth import (
    MagicLinkVerifyRequest,
    hash_token,
    verify_magic_link,
)
from app.db.models.auth import MagicLinkToken, User

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
async def test_verify_success_sets_cookie_and_logs(db_session):
    now = datetime.now(UTC)
    user = User(
        email=f"ok-{uuid.uuid4().hex}@test.com",
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
    response = Response()
    req_model = MagicLinkVerifyRequest(token=raw_token)

    async def _not_locked(_redis, _user_id):
        return False, 0

    async def _noop_reset(_redis, _user_id):
        return None

    with (
        patch("app.api.v1.auth.check_account_lockout", _not_locked),
        patch("app.api.v1.auth.reset_failed_login_attempts", _noop_reset),
    ):
        result = await verify_magic_link(req_model, response, http_req, db_session)

    # Cookie set
    cookies = [
        c for c in response.headers.getlist("set-cookie") if c.startswith("ff_sess=")
    ]
    assert cookies, "ff_sess cookie should be set"
    # Response model returned
    assert result.message == "Login successful!"
