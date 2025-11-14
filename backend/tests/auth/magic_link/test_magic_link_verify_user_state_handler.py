import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi import HTTPException
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


async def _seed_token(db_session, *, email, is_active=True, is_email_verified=True):
    now = datetime.now(UTC)
    user = User(
        email=email,
        is_active=is_active,
        is_email_verified=is_email_verified,
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
    return user, raw_token


@pytest.mark.asyncio
async def test_verify_inactive_user_returns_400(db_session):
    email = f"state-inactive-{uuid.uuid4().hex}@test.com"
    user, raw_token = await _seed_token(
        db_session, email=email, is_active=False, is_email_verified=True
    )
    http_req = make_request({"User-Agent": "ua-test"})
    response = Response()
    req_model = MagicLinkVerifyRequest(token=raw_token)
    with pytest.raises(HTTPException) as ei:
        await verify_magic_link(req_model, response, http_req, db_session)
    assert ei.value.status_code == 400


@pytest.mark.asyncio
async def test_verify_unverified_email_returns_403(db_session):
    email = f"state-unverified-{uuid.uuid4().hex}@test.com"
    user, raw_token = await _seed_token(
        db_session, email=email, is_active=True, is_email_verified=False
    )
    http_req = make_request({"User-Agent": "ua-test"})
    response = Response()
    req_model = MagicLinkVerifyRequest(token=raw_token)
    with pytest.raises(HTTPException) as ei:
        await verify_magic_link(req_model, response, http_req, db_session)
    assert ei.value.status_code == 403


@pytest.mark.asyncio
async def test_verify_locked_after_user_load_returns_429(db_session):
    email = f"state-locked-{uuid.uuid4().hex}@test.com"
    user, raw_token = await _seed_token(
        db_session, email=email, is_active=True, is_email_verified=True
    )
    http_req = make_request({"User-Agent": "ua-test"})
    response = Response()
    req_model = MagicLinkVerifyRequest(token=raw_token)

    call_count = {"n": 0}

    async def _locked_then_true(_redis, _user_id):
        # First (precheck) -> unlocked; Second (post-load) -> locked
        call_count["n"] += 1
        if call_count["n"] == 1:
            return False, 0
        return True, 42

    with patch("app.api.v1.auth.check_account_lockout", _locked_then_true):
        with pytest.raises(HTTPException) as ei:
            await verify_magic_link(req_model, response, http_req, db_session)
    assert ei.value.status_code == 429
