"""
Rate limiting middleware for FastAPI.

Applies rate limits based on endpoint patterns and returns HTTP 429 when exceeded.
"""

import os
import re
from collections.abc import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.rate_limiter import RateLimit, RateLimiter
from app.core.redis_client import get_redis

# Rate limit configurations per endpoint pattern (with API versioning)
RATE_LIMITS = {
    # Auth endpoints (per IP)
    r"^/api/v1/auth/magic-link/start$": RateLimit(
        requests=5,
        window=60,  # 5 requests per minute
        key_prefix="rl:magic_link_start",
    ),
    r"^/api/v1/auth/magic-link/verify$": RateLimit(
        requests=10,
        window=60,  # 10 requests per minute (allow retries)
        key_prefix="rl:magic_link_verify",
    ),
    r"^/api/v1/auth/webauthn/.*/start$": RateLimit(
        requests=10,
        window=60,  # 10 requests per minute
        key_prefix="rl:webauthn_start",
    ),
    r"^/api/v1/auth/webauthn/.*/finish$": RateLimit(
        requests=20,
        window=60,  # 20 requests per minute (allow failures/retries)
        key_prefix="rl:webauthn_finish",
    ),
    r"^/api/v1/auth/logout$": RateLimit(
        requests=10,
        window=60,
        key_prefix="rl:logout",
    ),
    # Global fallback (all endpoints)
    r"^/.*$": RateLimit(
        requests=1000,
        window=60,  # 1000 requests per minute (generous global limit)
        key_prefix="rl:global",
    ),
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to apply rate limiting to requests."""

    def __init__(self, app, exempt_paths: list[str] | None = None):
        super().__init__(app)
        self.exempt_paths = exempt_paths or []
        self.rate_limiter: RateLimiter | None = None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting to request."""
        # Check if rate limiting is enabled
        if os.getenv("RATE_LIMIT_ENABLED", "true").lower() != "true":
            return await call_next(request)

        # Skip rate limiting for exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)

        # Skip health checks
        if request.url.path in ["/healthz", "/healthz/live", "/healthz/ready"]:
            return await call_next(request)

        # Initialize rate limiter if needed
        if self.rate_limiter is None:
            redis_client = await get_redis()
            self.rate_limiter = RateLimiter(redis_client)

        # Find matching rate limit (first match wins)
        rate_limit = None
        for pattern, limit in RATE_LIMITS.items():
            if re.match(pattern, request.url.path):
                rate_limit = limit
                break

        if rate_limit is None:
            # No rate limit configured for this endpoint
            return await call_next(request)

        # Check rate limit
        identifier = self.rate_limiter.get_identifier(request, strategy="ip")
        result = await self.rate_limiter.check_rate_limit(identifier, rate_limit)

        if not result.allowed:
            # Rate limit exceeded
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please try again later.",
                        "retry_after": result.retry_after,
                    }
                },
                headers={
                    "Retry-After": str(result.retry_after),
                    "X-RateLimit-Limit": str(rate_limit.requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(result.reset_at.timestamp())),
                },
            )

        # Request allowed - proceed
        response: Response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(rate_limit.requests)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = str(int(result.reset_at.timestamp()))

        return response
