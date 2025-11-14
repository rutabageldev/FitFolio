import uuid
from datetime import UTC, datetime
from smtplib import SMTPException
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db.models.auth import MagicLinkToken, User

pytestmark = [pytest.mark.security, pytest.mark.integration]


@pytest.mark.asyncio
@patch("app.api.v1.auth.send_email")
async def test_start_existing_user_sends_login_token_and_email(
    mock_send_email, client: AsyncClient, db_session
):
    mock_send_email.return_value = None
    now = datetime.now(UTC)
    user = User(
        email="lines-exist@test.com",
        is_active=True,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    headers = {
        "X-Forwarded-For": f"10.6.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}",
        "X-Real-IP": f"10.7.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}",
        "User-Agent": f"ua-{uuid.uuid4().hex}",
    }
    response = await client.post(
        "/api/v1/auth/magic-link/start", json={"email": user.email}, headers=headers
    )
    assert response.status_code == 200
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
async def test_start_existing_user_email_send_failure_500(
    mock_send_email, client: AsyncClient, db_session
):
    mock_send_email.side_effect = SMTPException("smtp down")
    now = datetime.now(UTC)
    user = User(
        email="lines-exist2@test.com",
        is_active=True,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()

    headers = {
        "X-Forwarded-For": f"10.8.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}",
        "X-Real-IP": f"10.9.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}",
        "User-Agent": f"ua-{uuid.uuid4().hex}",
    }
    response = await client.post(
        "/api/v1/auth/magic-link/start", json={"email": user.email}, headers=headers
    )
    assert response.status_code == 500
