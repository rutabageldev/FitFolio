from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.core.redis_client import get_redis
from app.core.security import create_magic_link_token, hash_token
from app.db.models.auth import MagicLinkToken, User

pytestmark = [pytest.mark.security, pytest.mark.integration]


@pytest.mark.asyncio
async def test_verify_inactive_user_returns_400(client: AsyncClient, db_session):
    now = datetime.now(UTC)
    user = User(
        email="inactive-lines@test.com",
        is_active=False,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_magic_link_token()
    db_session.add(
        MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token),
            purpose="login",
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
    )
    await db_session.commit()

    response = await client.post(
        "/api/v1/auth/magic-link/verify", json={"token": token}
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_verify_unverified_email_returns_403(client: AsyncClient, db_session):
    now = datetime.now(UTC)
    user = User(
        email="unverified-lines@test.com",
        is_active=True,
        is_email_verified=False,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_magic_link_token()
    db_session.add(
        MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token),
            purpose="login",
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
    )
    await db_session.commit()

    response = await client.post(
        "/api/v1/auth/magic-link/verify", json={"token": token}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_verify_locked_after_user_load_returns_429(
    client: AsyncClient, db_session
):
    now = datetime.now(UTC)
    user = User(
        email="locked-after-lines@test.com",
        is_active=True,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_magic_link_token()
    db_session.add(
        MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token),
            purpose="login",
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
    )
    await db_session.commit()

    # Lock user AFTER token resolution path
    redis = await get_redis()
    await redis.setex(
        f"lockout:{user.id}", 60, (now + timedelta(minutes=1)).isoformat()
    )

    response = await client.post(
        "/api/v1/auth/magic-link/verify", json={"token": token}
    )
    assert response.status_code == 429
