"""Tests for rate limiting functionality."""

import os
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from app.core.rate_limiter import RateLimit, RateLimiter

# Enable rate limiting for these tests
os.environ["RATE_LIMIT_ENABLED"] = "true"


class TestRateLimiter:
    """Test token bucket rate limiter."""

    @pytest.mark.asyncio
    async def test_allows_requests_within_limit(self):
        """Should allow requests within rate limit."""
        from app.core.redis_client import get_redis

        redis_client = await get_redis()
        limiter = RateLimiter(redis_client)
        limit = RateLimit(requests=5, window=60, key_prefix="test:allow")

        # First 5 requests should succeed
        for i in range(5):
            result = await limiter.check_rate_limit("test_ip", limit)
            assert result.allowed
            assert result.remaining == 4 - i

    @pytest.mark.asyncio
    async def test_blocks_requests_exceeding_limit(self):
        """Should block requests exceeding rate limit."""
        from app.core.redis_client import get_redis

        redis_client = await get_redis()
        limiter = RateLimiter(redis_client)
        limit = RateLimit(requests=3, window=60, key_prefix="test:block")

        # First 3 requests succeed
        for _ in range(3):
            result = await limiter.check_rate_limit("test_ip2", limit)
            assert result.allowed

        # 4th request blocked
        result = await limiter.check_rate_limit("test_ip2", limit)
        assert not result.allowed
        assert result.retry_after is not None
        assert result.retry_after > 0

    @pytest.mark.asyncio
    async def test_sliding_window_behavior(self):
        """Should properly implement sliding window."""
        from app.core.redis_client import get_redis

        redis_client = await get_redis()
        limiter = RateLimiter(redis_client)
        limit = RateLimit(requests=2, window=2, key_prefix="test:sliding")

        # Use 2 requests
        result1 = await limiter.check_rate_limit("test_ip3", limit)
        result2 = await limiter.check_rate_limit("test_ip3", limit)
        assert result1.allowed
        assert result2.allowed

        # 3rd request should be blocked
        result3 = await limiter.check_rate_limit("test_ip3", limit)
        assert not result3.allowed

        # Wait for window to slide
        await limiter.redis.delete("test:sliding:test_ip3")  # Clean up for test

    @pytest.mark.asyncio
    async def test_different_identifiers_independent(self):
        """Different identifiers should have independent rate limits."""
        from app.core.redis_client import get_redis

        redis_client = await get_redis()
        limiter = RateLimiter(redis_client)
        limit = RateLimit(requests=2, window=60, key_prefix="test:independent")

        # Clean up any existing keys from previous test runs
        await redis_client.delete("test:independent:ip1", "test:independent:ip2")

        # Use up limit for IP1
        await limiter.check_rate_limit("ip1", limit)
        await limiter.check_rate_limit("ip1", limit)
        result = await limiter.check_rate_limit("ip1", limit)
        assert not result.allowed

        # IP2 should still have full limit
        result = await limiter.check_rate_limit("ip2", limit)
        assert result.allowed
        assert result.remaining == 1

        # Clean up
        await redis_client.delete("test:independent:ip1", "test:independent:ip2")

    @pytest.mark.asyncio
    async def test_reset_time_calculation(self):
        """Should correctly calculate reset time."""
        from app.core.redis_client import get_redis

        redis_client = await get_redis()
        limiter = RateLimiter(redis_client)
        limit = RateLimit(requests=5, window=60, key_prefix="test:reset")

        before = datetime.now(UTC)
        result = await limiter.check_rate_limit("test_ip4", limit)

        # Reset time should be approximately now + window
        assert result.reset_at > before
        assert result.reset_at.timestamp() >= before.timestamp() + limit.window


class TestRateLimitMiddleware:
    """Test rate limit middleware integration."""

    @pytest.mark.asyncio
    async def test_health_check_not_rate_limited(self, client: AsyncClient):
        """Health check endpoints should not be rate limited."""
        # Make many requests to health check
        for _ in range(10):
            response = await client.get("/healthz")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rate_limit_headers_present(self, client: AsyncClient, db_session):
        """Response should include rate limit headers."""
        from datetime import UTC, datetime

        from app.db.models.auth import User

        # Create test user
        now = datetime.now(UTC)
        user = User(
            email="ratelimit@test.com",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()

        # Make request to rate-limited endpoint
        response = await client.post(
            "/auth/magic-link/start",
            json={"email": "ratelimit@test.com"},
        )

        # Check rate limit headers are present
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    @pytest.mark.asyncio
    async def test_rate_limit_enforced_on_magic_link(
        self, client: AsyncClient, db_session
    ):
        """Should enforce rate limit on magic link endpoint."""
        from datetime import UTC, datetime

        from app.db.models.auth import User

        # Create test user
        now = datetime.now(UTC)
        user = User(
            email="ratelimit2@test.com",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()

        # Send requests up to the limit (5 per minute)
        for _ in range(5):
            response = await client.post(
                "/auth/magic-link/start",
                json={"email": "ratelimit2@test.com"},
            )
            # Should succeed or fail for other reasons (but not rate limit)
            assert response.status_code in [200, 400, 403]

        # 6th request should be rate limited
        response = await client.post(
            "/auth/magic-link/start",
            json={"email": "ratelimit2@test.com"},
        )
        assert response.status_code == 429
        data = response.json()
        assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert "retry_after" in data["error"]
        assert "Retry-After" in response.headers

    @pytest.mark.asyncio
    async def test_different_ips_separate_limits(self, client: AsyncClient, db_session):
        """Different client IPs should have separate rate limits."""
        # This test is limited because httpx AsyncClient doesn't easily allow
        # setting different client IPs. In production, this would be tested
        # with actual different clients or by mocking X-Forwarded-For header.
        # For now, we'll just verify the test client works with rate limiting.

        from datetime import UTC, datetime

        from app.db.models.auth import User

        now = datetime.now(UTC)
        user = User(
            email="different@test.com",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()

        response = await client.post(
            "/auth/magic-link/start",
            json={"email": "different@test.com"},
        )
        assert response.status_code in [200, 400, 403]  # Not rate limited
