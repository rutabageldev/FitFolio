from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.redis_client import get_redis
from app.core.security import create_magic_link_token, hash_token
from app.db.models.auth import LoginEvent, MagicLinkToken, User

pytestmark = [pytest.mark.security, pytest.mark.integration]


@pytest.mark.asyncio
async def test_verify_precheck_locked_returns_429_and_logs_event(
    client: AsyncClient, db_session
):
    now = datetime.now(UTC)
    user = User(
        email="precheck-lines@test.com",
        is_active=True,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token_value = create_magic_link_token()
    db_session.add(
        MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token_value),
            purpose="login",
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
    )
    await db_session.commit()

    # Lock the account via Redis to trigger precheck path
    redis = await get_redis()
    await redis.setex(
        f"lockout:{user.id}", 120, (now + timedelta(minutes=2)).isoformat()
    )

    response = await client.post(
        "/api/v1/auth/magic-link/verify",
        json={"token": token_value},
    )
    assert response.status_code == 429

    # Verify login_attempt_locked event recorded
    ev = (
        await db_session.execute(
            select(LoginEvent).where(
                LoginEvent.user_id == user.id,
                LoginEvent.event_type == "login_attempt_locked",
            )
        )
    ).scalar_one_or_none()
    assert ev is not None
