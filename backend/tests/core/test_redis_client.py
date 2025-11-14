import pytest

from app.core import redis_client as rc


class _DummyRedisOK:
    async def ping(self):
        return True

    async def aclose(self):
        self.closed = True


class _DummyRedisNoAClose:
    async def ping(self):
        return True

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_get_redis_raises_runtime_error_when_ping_fails(monkeypatch):
    # Close any existing real client opened by autouse fixtures to avoid warnings
    await rc.close_redis()

    class _FailPing:
        async def ping(self):
            raise RuntimeError("cannot reach")

    # Ensure fresh state
    rc._redis_client = None

    def fake_from_url(_url, **_kw):
        return _FailPing()

    monkeypatch.setattr(rc.redis, "from_url", fake_from_url, raising=True)
    # Use a known URL to exercise message content path (not asserting on it)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/15")

    with pytest.raises(RuntimeError):
        await rc.get_redis()

    # Should not cache a failed client
    assert rc._redis_client is None


@pytest.mark.asyncio
async def test_close_redis_falls_back_to_close_and_clears_client():
    # Provide a client without aclose() to force AttributeError path
    # Close any existing real client opened by autouse fixtures to avoid warnings
    await rc.close_redis()
    client = _DummyRedisNoAClose()
    rc._redis_client = client

    await rc.close_redis()

    # Client reference cleared
    assert rc._redis_client is None
    # Attribute set by close() indicates it was called
    assert getattr(client, "closed", False) is True
