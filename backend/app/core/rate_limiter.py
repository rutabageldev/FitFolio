"""
Rate limiting using token bucket algorithm with Redis backend.

Features:
- Token bucket algorithm (allows bursts)
- Atomic Redis operations (MULTI/EXEC)
- Configurable limits per endpoint
- Support for both IP-based and user-based limits
- Automatic key expiration (TTL)
"""

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

import redis.asyncio as redis
from fastapi import Request


@dataclass
class RateLimit:
    """Rate limit configuration."""

    requests: int  # Max requests allowed
    window: int  # Time window in seconds
    key_prefix: str  # Redis key prefix (e.g., "rl:magic_link")


@dataclass
class RateLimitResult:
    """Result of rate limit check."""

    allowed: bool
    remaining: int
    reset_at: datetime
    retry_after: int | None  # Seconds until next request allowed


class RateLimiter:
    """Redis-backed token bucket rate limiter."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def check_rate_limit(
        self,
        identifier: str,
        limit: RateLimit,
    ) -> RateLimitResult:
        """
        Check if request is within rate limit using token bucket algorithm.

        Uses Redis sorted set with timestamps as scores for sliding window.

        Args:
            identifier: Unique identifier (IP or user_id)
            limit: Rate limit configuration

        Returns:
            RateLimitResult with allow/deny decision
        """
        key = f"{limit.key_prefix}:{identifier}"
        now = time.time()
        window_start = now - limit.window

        # Use Redis pipeline for atomic operations
        pipe = self.redis.pipeline()

        # Remove old requests outside the window
        pipe.zremrangebyscore(key, 0, window_start)

        # Count requests in current window (before adding new one)
        pipe.zcard(key)

        # Set expiration (cleanup old keys)
        pipe.expire(key, limit.window)

        results = await pipe.execute()

        # results[1] is the count BEFORE adding current request
        current_requests = results[1]

        # Check if we're within limit
        allowed = current_requests < limit.requests

        # Only add current request if allowed
        if allowed:
            await self.redis.zadd(key, {str(now): now})
            await self.redis.expire(key, limit.window)

        remaining = max(0, limit.requests - current_requests - 1)

        # Calculate reset time (when oldest request expires)
        reset_at = datetime.fromtimestamp(now + limit.window, tz=UTC)

        # If denied, calculate retry_after (when next slot becomes available)
        retry_after = None
        if not allowed:
            # Get oldest request timestamp
            oldest = await self.redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                oldest_timestamp = oldest[0][1]
                retry_after = int(oldest_timestamp + limit.window - now) + 1

        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_at=reset_at,
            retry_after=retry_after,
        )

    def get_identifier(
        self,
        request: Request,
        strategy: Literal["ip", "user", "ip_or_user"] = "ip",
    ) -> str:
        """
        Extract rate limit identifier from request.

        Args:
            request: FastAPI Request object
            strategy: Identification strategy
                - "ip": Use client IP only
                - "user": Use user_id only (requires authentication)
                - "ip_or_user": Use user_id if authenticated, else IP

        Returns:
            Identifier string for rate limiting
        """
        if strategy == "user":
            # Requires authentication - get from request.state
            user_id = getattr(request.state, "user_id", None)
            if not user_id:
                raise ValueError("User strategy requires authenticated request")
            return f"user:{user_id}"

        # Get client IP (handle proxy headers)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take first IP in chain
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        if strategy == "ip":
            return f"ip:{ip}"

        # ip_or_user: prefer user_id if available
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"
        return f"ip:{ip}"
