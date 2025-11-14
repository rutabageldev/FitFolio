import uuid
from smtplib import SMTPException
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.redis_client import get_redis
from app.db.models.auth import LoginEvent, MagicLinkToken, User

pytestmark = [pytest.mark.security, pytest.mark.integration]


@pytest.mark.asyncio
async def test_start_new_user_creates_user_record(client: AsyncClient, db_session):
    email = f"lines-new-{uuid.uuid4().hex}@test.com"
    headers = {
        "X-Forwarded-For": f"10.0.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}",
        "X-Real-IP": f"10.1.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}",
        "User-Agent": f"ua-{uuid.uuid4().hex}",
    }
    # Ensure rate-limit keys are clear for this path
    redis = await get_redis()
    async for key in redis.scan_iter("rl:magic_link_start*"):
        await redis.delete(key)
    response = await client.post(
        "/api/v1/auth/magic-link/start", json={"email": email}, headers=headers
    )
    assert response.status_code == 200
    user = (
        await db_session.execute(select(User).where(User.email == email))
    ).scalar_one()
    assert user.is_active is True and user.is_email_verified is False
    # Prove branch executed: user_created login event exists
    ev = (
        await db_session.execute(
            select(LoginEvent).where(
                LoginEvent.user_id == user.id, LoginEvent.event_type == "user_created"
            )
        )
    ).scalar_one_or_none()
    assert ev is not None


@pytest.mark.asyncio
@patch("app.api.v1.auth.send_email")
async def test_start_new_user_sends_verification_token_and_email(
    mock_send_email, client: AsyncClient, db_session
):
    mock_send_email.return_value = None
    email = f"lines-new2-{uuid.uuid4().hex}@test.com"
    headers = {
        "X-Forwarded-For": f"10.2.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}",
        "X-Real-IP": f"10.3.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}",
        "User-Agent": f"ua-{uuid.uuid4().hex}",
    }
    redis = await get_redis()
    async for key in redis.scan_iter("rl:magic_link_start*"):
        await redis.delete(key)
    response = await client.post(
        "/api/v1/auth/magic-link/start", json={"email": email}, headers=headers
    )
    assert response.status_code == 200
    user = (
        await db_session.execute(select(User).where(User.email == email))
    ).scalar_one()
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
async def test_start_new_user_email_send_failure_500(
    mock_send_email, client: AsyncClient
):
    mock_send_email.side_effect = SMTPException("smtp down")
    email = f"lines-new3-{uuid.uuid4().hex}@test.com"
    headers = {
        "X-Forwarded-For": f"10.4.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}",
        "X-Real-IP": f"10.5.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}",
        "User-Agent": f"ua-{uuid.uuid4().hex}",
    }
    redis = await get_redis()
    async for key in redis.scan_iter("rl:magic_link_start*"):
        await redis.delete(key)
    response = await client.post(
        "/api/v1/auth/magic-link/start", json={"email": email}, headers=headers
    )
    assert response.status_code == 500
