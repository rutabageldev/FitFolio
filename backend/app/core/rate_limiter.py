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

        # Use Lua script to ensure atomicity under concurrency:
        # 1) ZREMRANGEBYSCORE key 0 window_start
        # 2) ZCARD key
        # 3) If count < limit: ZADD key now now; allowed=1 else allowed=0
        # 4) EXPIRE key window
        # Returns: {allowed, remaining_after_this}
        lua = """
        local key        = KEYS[1]
        local now        = tonumber(ARGV[1])
        local window     = tonumber(ARGV[2])
        local lim        = tonumber(ARGV[3])
        local window_start = now - window
        redis.call('ZREMRANGEBYSCORE', key, 0, window_start)
        local count = redis.call('ZCARD', key)
        local allowed = 0
        if count < lim then
          local seq_key = key .. ':seq'
          local seq = redis.call('INCR', seq_key)
          redis.call('EXPIRE', seq_key, window)
          redis.call('ZADD', key, now, tostring(now) .. ':' .. tostring(seq))
          allowed = 1
          count = count + 1
        end
        redis.call('EXPIRE', key, window)
        local remaining = lim - count
        if remaining < 0 then remaining = 0 end
        return {allowed, remaining}
        """
        # redis-py expects: eval(script, numkeys, key1, ..., arg1, arg2, ...)
        allowed_flag, remaining = await self.redis.eval(
            lua, 1, key, now, limit.window, limit.requests
        )
        # Decode (redis may return strings when decode_responses=True)
        try:
            allowed = bool(int(allowed_flag))
        except (TypeError, ValueError):
            allowed = bool(allowed_flag)
        try:
            remaining = int(remaining)
        except (TypeError, ValueError):
            remaining = max(0, limit.requests - 1)

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
