import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from starlette.requests import Request

from app.api.v1.auth import (
    EmailResendVerificationRequest,
    resend_verification_email,
)
from app.db.models.auth import LoginEvent, MagicLinkToken, User

pytestmark = [pytest.mark.security, pytest.mark.integration]


def make_request() -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/email/resend-verification",
        "headers": [(b"user-agent", b"pytest")],
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_resend_verification_creates_token_logs_event_and_sends_email(
    monkeypatch, db_session
):
    now = datetime.now(UTC)
    email = f"resend-{uuid.uuid4().hex}@test.com"
    user = User(
        email=email,
        is_active=True,
        is_email_verified=False,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    sent = SimpleNamespace(calls=0, last_to=None, last_subj=None)

    async def _fake_send_email(*, to, subject, body):
        sent.calls += 1
        sent.last_to = to
        sent.last_subj = subject
        # mark body as used for linter
        sent.last_body_len = len(body)

    monkeypatch.setattr("app.api.v1.auth.send_email", _fake_send_email)

    req = EmailResendVerificationRequest(email=email)
    http_req = make_request()
    result = await resend_verification_email(req, http_req, db_session)

    # Always success message
    assert "verification" in result.message.lower()
    # Email sent
    assert sent.calls == 1 and sent.last_to == email
    # Token created
    rows = (
        (
            await db_session.execute(
                select(MagicLinkToken).where(MagicLinkToken.user_id == user.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1 and rows[0].purpose == "email_verification"
    # Event logged
    events = (
        (
            await db_session.execute(
                select(LoginEvent).where(LoginEvent.user_id == user.id)
            )
        )
        .scalars()
        .all()
    )
    assert any(e.event_type == "email_verification_resent" for e in events)


@pytest.mark.asyncio
async def test_resend_verification_send_failure_returns_500(monkeypatch, db_session):
    now = datetime.now(UTC)
    email = f"resend-fail-{uuid.uuid4().hex}@test.com"
    user = User(
        email=email,
        is_active=True,
        is_email_verified=False,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()

    async def _raise_send_email(*, to, subject, body):
        # mark args as intentionally unused for linter
        del to, subject, body
        raise RuntimeError("smtp failure")

    monkeypatch.setattr("app.api.v1.auth.send_email", _raise_send_email)

    req = EmailResendVerificationRequest(email=email)
    http_req = make_request()

    with pytest.raises(HTTPException) as ei:
        await resend_verification_email(req, http_req, db_session)
    assert ei.value.status_code == 500
