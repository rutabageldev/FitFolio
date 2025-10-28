import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import redis.asyncio as redis


def create_session_token() -> str:
    """Generate a secure random session token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> bytes:
    """Hash a token using SHA-256."""
    return hashlib.sha256(token.encode()).digest()


def verify_token_hash(token: str, token_hash: bytes) -> bool:
    """Verify a token against its hash."""
    return hash_token(token) == token_hash


def create_magic_link_token() -> str:
    """Generate a secure random magic link token."""
    return secrets.token_urlsafe(32)


def hash_magic_link_token(token: str) -> bytes:
    """Hash a magic link token using SHA-256."""
    return hashlib.sha256(token.encode()).digest()


# Account lockout constants
LOCKOUT_FAILED_ATTEMPTS_THRESHOLD = 5  # Lock after this many failures
LOCKOUT_DURATION_SECONDS = 900  # 15 minutes
LOCKOUT_WINDOW_SECONDS = 3600  # Track failures in 1-hour window


async def check_account_lockout(
    redis_client: redis.Redis, user_id: uuid.UUID
) -> tuple[bool, int | None]:
    """
    Check if an account is locked due to failed login attempts.

    Args:
        redis_client: Redis client instance
        user_id: User ID to check

    Returns:
        Tuple of (is_locked, seconds_remaining)
        - is_locked: True if account is currently locked
        - seconds_remaining: Seconds until lockout expires (None if not locked)
    """
    lockout_key = f"lockout:{user_id}"
    lockout_until = await redis_client.get(lockout_key)

    if lockout_until:
        # Account is locked, check if lockout has expired
        lockout_expiry = datetime.fromisoformat(lockout_until)
        now = datetime.now(UTC)

        if lockout_expiry > now:
            # Still locked
            seconds_remaining = int((lockout_expiry - now).total_seconds())
            return True, seconds_remaining

        # Lockout expired, clean up
        await redis_client.delete(lockout_key)

    return False, None


async def record_failed_login(
    redis_client: redis.Redis, user_id: uuid.UUID
) -> tuple[bool, int]:
    """
    Record a failed login attempt and check if account should be locked.

    Args:
        redis_client: Redis client instance
        user_id: User ID for the failed attempt

    Returns:
        Tuple of (should_lock, attempt_count)
        - should_lock: True if lockout threshold reached
        - attempt_count: Current number of failed attempts
    """
    attempts_key = f"failed_attempts:{user_id}"
    now = datetime.now(UTC)

    # Increment failed attempts counter
    attempt_count = await redis_client.incr(attempts_key)

    # Set expiry on first attempt (sliding window)
    if attempt_count == 1:
        await redis_client.expire(attempts_key, LOCKOUT_WINDOW_SECONDS)

    # Check if threshold reached
    if attempt_count >= LOCKOUT_FAILED_ATTEMPTS_THRESHOLD:
        # Lock the account
        lockout_key = f"lockout:{user_id}"
        lockout_until = now + timedelta(seconds=LOCKOUT_DURATION_SECONDS)
        await redis_client.set(
            lockout_key, lockout_until.isoformat(), ex=LOCKOUT_DURATION_SECONDS
        )

        # Reset failed attempts counter
        await redis_client.delete(attempts_key)

        return True, attempt_count

    return False, attempt_count


async def reset_failed_login_attempts(
    redis_client: redis.Redis, user_id: uuid.UUID
) -> None:
    """
    Reset failed login attempts counter after successful login.

    Args:
        redis_client: Redis client instance
        user_id: User ID to reset
    """
    attempts_key = f"failed_attempts:{user_id}"
    await redis_client.delete(attempts_key)
