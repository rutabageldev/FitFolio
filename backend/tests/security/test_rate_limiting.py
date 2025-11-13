"""Tests for rate limiting functionality."""

import asyncio
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from app.core.rate_limiter import RateLimit, RateLimiter

# All tests in this module are security-focused integration tests
pytestmark = [pytest.mark.security, pytest.mark.integration]


@pytest.fixture(autouse=True, scope="function")
def enable_rate_limit_env(monkeypatch):
    """Ensure rate limiting is enabled for this module without leaking env changes."""
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    yield


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
        """Should properly implement sliding window with natural expiry."""
        from app.core.redis_client import get_redis

        redis_client = await get_redis()
        limiter = RateLimiter(redis_client)
        limit = RateLimit(requests=1, window=1, key_prefix="test:sliding")

        # First request allowed
        result1 = await limiter.check_rate_limit("test_ip3", limit)
        assert result1.allowed

        # Second request within window should be blocked
        result2 = await limiter.check_rate_limit("test_ip3", limit)
        assert not result2.allowed

        # Wait for window to expire and try again
        await asyncio.sleep(1.1)
        result3 = await limiter.check_rate_limit("test_ip3", limit)
        assert result3.allowed

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

    @pytest.mark.asyncio
    async def test_pipeline_atomicity_under_concurrency(self):
        """Concurrent checks should not allow more than limit."""
        from app.core.redis_client import get_redis

        redis_client = await get_redis()
        limiter = RateLimiter(redis_client)
        limit = RateLimit(requests=5, window=5, key_prefix="test:atomic")
        identifier = "ip:9.9.9.9"

        # Clear any prior state
        await redis_client.delete(f"{limit.key_prefix}:{identifier}")

        async def attempt():
            return await limiter.check_rate_limit(identifier, limit)

        # Launch 10 concurrent attempts
        results = await asyncio.gather(*[attempt() for _ in range(10)])
        allowed_count = sum(1 for r in results if r.allowed)
        assert allowed_count <= limit.requests


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
    async def test_fallback_limit_applies(self, client: AsyncClient):
        """Global fallback limit should apply to endpoints without explicit config."""
        # /api/v1/auth/me is not explicitly configured; fallback should apply
        response = await client.get("/api/v1/auth/me")
        # Should not be 404; we accept 401 when unauthenticated
        assert response.status_code in (200, 401)
        # Header should reflect fallback budget (1000 per minute)
        assert response.headers.get("X-RateLimit-Limit") == "1000"

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
            "/api/v1/auth/magic-link/start",
            json={"email": "ratelimit@test.com"},
        )

        # Check rate limit headers are present
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    @pytest.mark.asyncio
    async def test_headers_remaining_and_reset_progress(
        self, client: AsyncClient, db_session
    ):
        """Remaining should decrement and reset should be a valid epoch second."""
        from datetime import UTC, datetime

        from app.db.models.auth import User

        now = datetime.now(UTC)
        user = User(
            email="ratelimit3@test.com",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()

        r1 = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": "ratelimit3@test.com"},
        )
        r2 = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": "ratelimit3@test.com"},
        )
        assert r1.status_code in (200, 400, 403)
        assert r2.status_code in (200, 400, 403)
        rem1 = int(r1.headers["X-RateLimit-Remaining"])
        rem2 = int(r2.headers["X-RateLimit-Remaining"])
        assert rem2 <= rem1
        reset_epoch = int(r2.headers["X-RateLimit-Reset"])
        assert reset_epoch > 0

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
                "/api/v1/auth/magic-link/start",
                json={"email": "ratelimit2@test.com"},
            )
            # Should succeed or fail for other reasons (but not rate limit)
            assert response.status_code in [200, 400, 403]

        # 6th request should be rate limited
        response = await client.post(
            "/api/v1/auth/magic-link/start",
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
        from datetime import UTC, datetime

        from app.db.models.auth import User

        now = datetime.now(UTC)
        # Ensure a user exists for each email
        for email in ["ip1@test.com", "ip2@test.com"]:
            user = User(email=email, is_active=True, created_at=now, updated_at=now)
            db_session.add(user)
        await db_session.commit()

        # Exhaust limit for IP 1
        for _ in range(5):
            r = await client.post(
                "/api/v1/auth/magic-link/start",
                json={"email": "ip1@test.com"},
                headers={"X-Forwarded-For": "1.1.1.1"},
            )
            assert r.status_code in [200, 400, 403]  # Not rate limited yet
        r6 = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": "ip1@test.com"},
            headers={"X-Forwarded-For": "1.1.1.1"},
        )
        assert r6.status_code == 429

        # IP 2 should still be under its own budget
        r_ok = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": "ip2@test.com"},
            headers={"X-Forwarded-For": "2.2.2.2"},
        )
        assert r_ok.status_code in [200, 400, 403]

        # Verify 429 includes headers
        assert "Retry-After" in r6.headers
        assert r6.headers.get("X-RateLimit-Remaining") == "0"

    @pytest.mark.asyncio
    async def test_rate_limit_disabled_via_env(self, client: AsyncClient, monkeypatch):
        """RATE_LIMIT_ENABLED=false disables checks and headers."""
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
        r = await client.get("/api/v1/auth/me")
        # Should not include rate limit headers when disabled
        assert "X-RateLimit-Limit" not in r.headers
        assert "X-RateLimit-Remaining" not in r.headers
        assert "X-RateLimit-Reset" not in r.headers

    @pytest.mark.asyncio
    async def test_exempt_paths_bypass_limiter(self, client: AsyncClient):
        """Docs/openapi endpoints are exempt from rate limiting."""
        # /docs is exempt
        r_docs = await client.get("/docs")
        assert r_docs.status_code in (200, 307, 308)  # ASGI may redirect to /docs/
        # /openapi.json is exempt
        r_openapi = await client.get("/openapi.json")
        assert r_openapi.status_code == 200
        # Headers should not be present on exempt responses
        for r in (r_docs, r_openapi):
            assert "X-RateLimit-Limit" not in r.headers
            assert "X-RateLimit-Remaining" not in r.headers
            assert "X-RateLimit-Reset" not in r.headers
