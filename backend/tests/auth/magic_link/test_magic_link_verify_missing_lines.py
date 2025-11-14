import pytest
from httpx import AsyncClient

from app.core.redis_client import get_redis

pytestmark = [pytest.mark.security, pytest.mark.integration]


@pytest.mark.asyncio
async def test_verify_invalid_token_returns_429_when_any_lockout_keys_exist(
    client: AsyncClient,
):
    redis = await get_redis()
    await redis.setex("lockout:any", 60, "until")
    response = await client.post(
        "/api/v1/auth/magic-link/verify", json={"token": "totally_invalid"}
    )
    assert response.status_code == 429


@pytest.mark.asyncio
async def test_verify_invalid_token_redis_error_fallback_returns_400(
    client: AsyncClient, monkeypatch
):
    # Force get_redis to raise to hit fallback except branch
    import app.api.v1.auth as auth_api

    def _boom():
        raise RuntimeError("redis down")

    monkeypatch.setattr(auth_api, "get_redis", _boom, raising=True)
    response = await client.post(
        "/api/v1/auth/magic-link/verify", json={"token": "invalid_again"}
    )
    assert response.status_code == 400
