"""Tests for WebAuthn challenge storage utilities."""

import pytest

from app.core.challenge_storage import (
    CHALLENGE_TTL,
    cleanup_expired_challenges,
    retrieve_and_delete_challenge,
    store_challenge,
)
from app.core.redis_client import get_redis

pytestmark = [pytest.mark.security, pytest.mark.integration]


class TestChallengeStorage:
    @pytest.mark.asyncio
    async def test_store_challenge_sets_ttl_and_opaque_id(self):
        """Store returns opaque id and sets TTL."""
        user_email = "ttl@test.com"
        challenge_hex = "cafebabe"
        challenge_id = await store_challenge(user_email, challenge_hex, "registration")

        assert isinstance(challenge_id, str) and len(challenge_id) > 10
        assert user_email not in challenge_id and challenge_hex not in challenge_id

        redis = await get_redis()
        key = f"webauthn:challenge:registration:{challenge_id}"
        ttl = await redis.ttl(key)
        # ttl may be float/int depending on client; ensure >0 and <= configured TTL
        is_num = isinstance(ttl, int) or isinstance(ttl, float)
        assert ttl is None or (is_num and 0 < ttl <= CHALLENGE_TTL)

    @pytest.mark.asyncio
    async def test_retrieve_and_delete_returns_tuple_then_none(self):
        """Retrieve returns (email, challenge) once, then deletes key."""
        user_email = "once@test.com"
        challenge_hex = "deadbeef"
        challenge_id = await store_challenge(
            user_email, challenge_hex, "authentication"
        )

        result = await retrieve_and_delete_challenge(challenge_id, "authentication")
        assert result == (user_email, challenge_hex)

        # Second retrieval should return None (single-use)
        result2 = await retrieve_and_delete_challenge(challenge_id, "authentication")
        assert result2 is None

    @pytest.mark.asyncio
    async def test_retrieve_missing_or_expired_returns_none(self):
        """Missing challenge_id returns None."""
        result = await retrieve_and_delete_challenge("nope", "registration")
        assert result is None

    @pytest.mark.asyncio
    async def test_malformed_stored_value_returns_none(self):
        """If stored value is malformed, retrieval returns None."""
        redis = await get_redis()
        challenge_id = "malformed-1"
        key = f"webauthn:challenge:registration:{challenge_id}"
        await redis.set(key, "malformed")  # no colon

        result = await retrieve_and_delete_challenge(challenge_id, "registration")
        assert result is None

    @pytest.mark.asyncio
    async def test_store_raises_on_redis_error(self, monkeypatch):
        """Store should raise RuntimeError when Redis setex fails."""
        redis = await get_redis()

        async def boom(*_args, **_kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(redis, "setex", boom)
        with pytest.raises(RuntimeError):
            await store_challenge("err@test.com", "abcd", "registration")

    @pytest.mark.asyncio
    async def test_pipeline_execute_error_raises(self, monkeypatch):
        """Pipeline execute failure in retrieval raises RuntimeError."""

        class FakePipe:
            def get(self, *_args, **_kwargs):  # noqa: D401
                return self

            def delete(self, *_args, **_kwargs):  # noqa: D401
                return self

            async def execute(self):
                raise RuntimeError("pipeline failed")

        redis = await get_redis()
        monkeypatch.setattr(redis, "pipeline", lambda: FakePipe())
        with pytest.raises(RuntimeError):
            await retrieve_and_delete_challenge("id", "authentication")

    @pytest.mark.asyncio
    async def test_cleanup_deletes_keys_by_user_and_type(self):
        """Cleanup should delete only keys for the given user and type."""
        redis = await get_redis()
        # Prepare keys for two users and two types
        await redis.set("webauthn:challenge:registration:1", "user1:aa")
        await redis.set("webauthn:challenge:registration:2", "user1:bb")
        await redis.set("webauthn:challenge:registration:3", "user2:cc")
        await redis.set("webauthn:challenge:authentication:4", "user1:dd")

        deleted = await cleanup_expired_challenges("user1", "registration")
        assert deleted == 2

        # Remaining keys should be ones not matching user/type
        assert await redis.get("webauthn:challenge:registration:3") is not None
        assert await redis.get("webauthn:challenge:authentication:4") is not None
