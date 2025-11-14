import uuid
from smtplib import SMTPException
from unittest.mock import patch

import pytest
from sqlalchemy import select
from starlette.requests import Request

from app.api.v1.auth import MagicLinkRequest, start_magic_link_login
from app.core.redis_client import get_redis
from app.db.models.auth import LoginEvent, MagicLinkToken, User

pytestmark = [pytest.mark.security, pytest.mark.integration]


def make_request(headers: dict[str, str] | None = None) -> Request:
    raw_headers = []
    for k, v in (headers or {}).items():
        raw_headers.append((k.lower().encode("latin-1"), v.encode("latin-1")))
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/magic-link/start",
        "headers": raw_headers,
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


@pytest.mark.asyncio
@patch("app.api.v1.auth.send_email")
async def test_unit_start_new_user_executes_creation_block_and_sends_verification(
    mock_send_email, db_session
):
    mock_send_email.return_value = None
    email = f"unit-new-{uuid.uuid4().hex}@test.com"
    req_model = MagicLinkRequest(email=email)
    http_req = make_request({"User-Agent": f"ua-{uuid.uuid4().hex}"})

    # Clear RL keys to avoid interference (defensive)
    redis = await get_redis()
    async for key in redis.scan_iter("rl:magic_link_start*"):
        await redis.delete(key)

    await start_magic_link_login(req_model, http_req, db_session)

    user = (
        await db_session.execute(select(User).where(User.email == email))
    ).scalar_one()
    assert user.is_active is True and user.is_email_verified is False
    # 'user_created' event confirms the creation branch executed
    ev = (
        await db_session.execute(
            select(LoginEvent).where(
                LoginEvent.user_id == user.id, LoginEvent.event_type == "user_created"
            )
        )
    ).scalar_one_or_none()
    assert ev is not None

    token = (
        await db_session.execute(
            select(MagicLinkToken)
            .where(MagicLinkToken.user_id == user.id)
            .order_by(MagicLinkToken.created_at.desc())
        )
    ).scalar_one()
    assert token.purpose == "email_verification"
    assert mock_send_email.called


@pytest.mark.asyncio
@patch("app.api.v1.auth.send_email")
async def test_unit_start_new_user_verification_send_failure_raises_500(
    mock_send_email, db_session
):
    mock_send_email.side_effect = SMTPException("smtp fail")
    email = f"unit-new-fail-{uuid.uuid4().hex}@test.com"
    req_model = MagicLinkRequest(email=email)
    http_req = make_request({"User-Agent": f"ua-{uuid.uuid4().hex}"})

    with pytest.raises(Exception) as ei:
        await start_magic_link_login(req_model, http_req, db_session)
    assert "Failed to send verification email" in str(ei.value)
