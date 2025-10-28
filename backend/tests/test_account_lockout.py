"""Tests for account lockout functionality."""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from app.core.redis_client import get_redis
from app.core.security import (
    LOCKOUT_DURATION_SECONDS,
    LOCKOUT_FAILED_ATTEMPTS_THRESHOLD,
    check_account_lockout,
    record_failed_login,
    reset_failed_login_attempts,
)
from app.db.models.auth import MagicLinkToken, User


class TestAccountLockoutHelpers:
    """Test account lockout helper functions."""

    @pytest.mark.asyncio
    async def test_check_account_lockout_not_locked(self):
        """Should return False when account is not locked."""

        redis_client = await get_redis()
        test_user_id = uuid.uuid4()

        is_locked, seconds_remaining = await check_account_lockout(
            redis_client, test_user_id
        )

        assert not is_locked
        assert seconds_remaining is None

    @pytest.mark.asyncio
    async def test_record_failed_login_below_threshold(self):
        """Should not lock account below threshold."""

        redis_client = await get_redis()
        test_user_id = uuid.uuid4()

        # Record 4 failed attempts (threshold is 5)
        for i in range(4):
            should_lock, attempt_count = await record_failed_login(
                redis_client, test_user_id
            )
            assert not should_lock
            assert attempt_count == i + 1

    @pytest.mark.asyncio
    async def test_record_failed_login_at_threshold(self):
        """Should lock account at threshold."""

        redis_client = await get_redis()
        test_user_id = uuid.uuid4()

        # Record attempts up to threshold
        for _ in range(LOCKOUT_FAILED_ATTEMPTS_THRESHOLD - 1):
            should_lock, _ = await record_failed_login(redis_client, test_user_id)
            assert not should_lock

        # This one should trigger lockout
        should_lock, attempt_count = await record_failed_login(
            redis_client, test_user_id
        )
        assert should_lock
        assert attempt_count == LOCKOUT_FAILED_ATTEMPTS_THRESHOLD

        # Verify account is now locked
        is_locked, seconds_remaining = await check_account_lockout(
            redis_client, test_user_id
        )
        assert is_locked
        assert seconds_remaining is not None
        assert 0 < seconds_remaining <= LOCKOUT_DURATION_SECONDS

    @pytest.mark.asyncio
    async def test_reset_failed_login_attempts(self):
        """Should reset failed attempts counter."""

        redis_client = await get_redis()
        test_user_id = uuid.uuid4()

        # Record some failed attempts
        for _ in range(3):
            await record_failed_login(redis_client, test_user_id)

        # Reset
        await reset_failed_login_attempts(redis_client, test_user_id)

        # Next attempt should be count=1 (reset worked)
        _, attempt_count = await record_failed_login(redis_client, test_user_id)
        assert attempt_count == 1

    @pytest.mark.asyncio
    async def test_different_users_independent_lockouts(self):
        """Different users should have independent lockout counters."""

        redis_client = await get_redis()
        user1_id = uuid.uuid4()
        user2_id = uuid.uuid4()

        # Lock user1
        for _ in range(LOCKOUT_FAILED_ATTEMPTS_THRESHOLD):
            await record_failed_login(redis_client, user1_id)

        # Verify user1 is locked
        is_locked, _ = await check_account_lockout(redis_client, user1_id)
        assert is_locked

        # Verify user2 is NOT locked
        is_locked, _ = await check_account_lockout(redis_client, user2_id)
        assert not is_locked


class TestMagicLinkLockout:
    """Test magic link authentication with account lockout."""

    @pytest.mark.asyncio
    async def test_magic_link_verify_when_locked(self, client: AsyncClient, db_session):
        """Should reject login attempt when account is locked."""
        from datetime import timedelta

        from app.core.security import hash_token

        # Create test user
        now = datetime.now(UTC)
        user = User(
            email="locked@test.com",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create valid magic link token
        token = "test_token_for_locked_user"
        magic_link = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        db_session.add(magic_link)
        await db_session.commit()

        # Lock the account
        redis_client = await get_redis()
        for _ in range(LOCKOUT_FAILED_ATTEMPTS_THRESHOLD):
            await record_failed_login(redis_client, user.id)

        # Try to verify magic link
        response = await client.post(
            "/auth/magic-link/verify",
            json={"token": token},
        )

        # Should be rejected with 429 (Too Many Requests)
        assert response.status_code == 429
        assert "locked" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_successful_login_resets_attempts(
        self, client: AsyncClient, db_session
    ):
        """Successful login should reset failed attempts counter."""
        from datetime import timedelta

        from app.core.security import hash_token

        # Create test user
        now = datetime.now(UTC)
        user = User(
            email="reset@test.com",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Record some failed attempts (but not enough to lock)
        redis_client = await get_redis()
        for _ in range(3):
            await record_failed_login(redis_client, user.id)

        # Create valid magic link token
        token = "test_token_for_reset"
        magic_link = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        db_session.add(magic_link)
        await db_session.commit()

        # Successful login
        response = await client.post(
            "/auth/magic-link/verify",
            json={"token": token},
        )

        # Should succeed
        assert response.status_code == 200

        # Verify failed attempts were reset
        # (Try recording new failures - should start from 1)
        _, attempt_count = await record_failed_login(redis_client, user.id)
        assert attempt_count == 1
