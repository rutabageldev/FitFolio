"""Redis client initialization and connection management."""

import os

import redis.asyncio as redis

_redis_client: redis.Redis | None = None
_redis_url_cache: str | None = None


async def get_redis() -> redis.Redis:
    """
    Get Redis client instance (singleton).

    Returns:
        redis.Redis: Async Redis client instance

    Raises:
        RuntimeError: If Redis connection fails
    """
    global _redis_client, _redis_url_cache

    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    # Recreate client if URL changed (e.g., tests override REDIS_URL after import)
    if _redis_client is None or _redis_url_cache != redis_url:
        try:
            _redis_client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Test connection
            await _redis_client.ping()
            _redis_url_cache = redis_url
        except Exception as e:
            # Ensure we don't cache a bad client on failure
            _redis_client = None
            raise RuntimeError(f"Failed to connect to Redis at {redis_url}: {e}") from e

    return _redis_client


async def close_redis() -> None:
    """Close Redis connection (call on app shutdown)."""
    global _redis_client
    if _redis_client is not None:
        # redis-py 5.x deprecates close() in favor of aclose() for asyncio
        try:
            await _redis_client.aclose()  # type: ignore[attr-defined]
        except AttributeError:
            await _redis_client.close()  # Backwards compatibility
        _redis_client = None
