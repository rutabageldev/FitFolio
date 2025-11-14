import uuid
from datetime import UTC, datetime
from smtplib import SMTPException
from unittest.mock import patch

import pytest
from sqlalchemy import select
from starlette.requests import Request

from app.api.v1.auth import MagicLinkRequest, start_magic_link_login
from app.db.models.auth import MagicLinkToken, User

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
async def test_unit_start_existing_user_creates_login_token_and_sends_email(
    mock_send_email, db_session
):
    mock_send_email.return_value = None
    now = datetime.now(UTC)
    user = User(
        email=f"unit-exist-{uuid.uuid4().hex}@test.com",
        is_active=True,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    req_model = MagicLinkRequest(email=user.email)
    http_req = make_request({"User-Agent": f"ua-{uuid.uuid4().hex}"})

    await start_magic_link_login(req_model, http_req, db_session)

    token = (
        await db_session.execute(
            select(MagicLinkToken)
            .where(MagicLinkToken.user_id == user.id)
            .order_by(MagicLinkToken.created_at.desc())
        )
    ).scalar_one()
    assert token.purpose == "login"
    assert mock_send_email.called


@pytest.mark.asyncio
@patch("app.api.v1.auth.send_email")
async def test_unit_start_existing_user_email_send_failure_raises_500(
    mock_send_email, db_session
):
    mock_send_email.side_effect = SMTPException("smtp fail")
    now = datetime.now(UTC)
    user = User(
        email=f"unit-exist-fail-{uuid.uuid4().hex}@test.com",
        is_active=True,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()

    req_model = MagicLinkRequest(email=user.email)
    http_req = make_request({"User-Agent": f"ua-{uuid.uuid4().hex}"})

    with pytest.raises(Exception) as ei:
        await start_magic_link_login(req_model, http_req, db_session)
    assert "Failed to send magic link email" in str(ei.value)
