"""WebAuthn challenge storage using Redis."""

import secrets

from app.core.redis_client import get_redis

# Challenge TTL in seconds (60 seconds for WebAuthn)
CHALLENGE_TTL = 60


def _generate_challenge_id() -> str:
    """Generate a unique, unguessable challenge ID."""
    return secrets.token_urlsafe(32)


async def store_challenge(
    user_email: str, challenge_hex: str, challenge_type: str
) -> str:
    """
    Store WebAuthn challenge in Redis with TTL.

    Args:
        user_email: User's email address (for key namespacing)
        challenge_hex: Challenge bytes as hex string
        challenge_type: Type of challenge ('registration' or 'authentication')

    Returns:
        str: Opaque challenge ID to return to client

    Raises:
        RuntimeError: If Redis storage fails
    """
    redis_client = await get_redis()
    challenge_id = _generate_challenge_id()

    # Store with composite key for easy debugging and cleanup
    redis_key = f"webauthn:challenge:{challenge_type}:{challenge_id}"

    # Store as JSON-like structure for potential future expansion
    value = f"{user_email}:{challenge_hex}"

    try:
        await redis_client.setex(redis_key, CHALLENGE_TTL, value)
    except Exception as e:
        raise RuntimeError(f"Failed to store challenge in Redis: {e}") from e

    return challenge_id


async def retrieve_and_delete_challenge(
    challenge_id: str, challenge_type: str
) -> tuple[str, str] | None:
    """
    Retrieve and delete challenge from Redis (single-use).

    Args:
        challenge_id: The opaque challenge ID
        challenge_type: Type of challenge ('registration' or 'authentication')

    Returns:
        Optional[tuple[str, str]]: (user_email, challenge_hex) if found,
            None if not found or expired

    Raises:
        RuntimeError: If Redis operation fails
    """
    redis_client = await get_redis()
    redis_key = f"webauthn:challenge:{challenge_type}:{challenge_id}"

    try:
        # Get and delete atomically using pipeline
        pipe = redis_client.pipeline()
        pipe.get(redis_key)
        pipe.delete(redis_key)
        results = await pipe.execute()

        value = results[0]
        if value is None:
            return None

        # Parse stored value
        parts = value.split(":", 1)
        if len(parts) != 2:
            return None

        user_email, challenge_hex = parts
        return (user_email, challenge_hex)

    except Exception as e:
        raise RuntimeError(f"Failed to retrieve challenge from Redis: {e}") from e


async def cleanup_expired_challenges(user_email: str, challenge_type: str) -> int:
    """
    Cleanup any expired challenges for a user (optional housekeeping).

    Args:
        user_email: User's email address
        challenge_type: Type of challenge ('registration' or 'authentication')

    Returns:
        int: Number of challenges deleted

    Note:
        This is optional since challenges have TTL and will auto-expire.
        Only use if you need explicit cleanup before TTL.
    """
    redis_client = await get_redis()
    pattern = f"webauthn:challenge:{challenge_type}:*"

    try:
        deleted = 0
        async for key in redis_client.scan_iter(match=pattern, count=100):
            value = await redis_client.get(key)
            if value and value.startswith(f"{user_email}:"):
                await redis_client.delete(key)
                deleted += 1
        return deleted
    except Exception as e:
        raise RuntimeError(f"Failed to cleanup challenges from Redis: {e}") from e
