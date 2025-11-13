"""Magic link verify error-path tests (extracted from mixed endpoints file)."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.core.security import hash_token
from app.db.models.auth import MagicLinkToken, User

pytestmark = [pytest.mark.security, pytest.mark.integration]


class TestMagicLinkVerifyErrorPaths:
    """Test error handling in magic link verification."""

    @pytest.mark.asyncio
    async def test_magic_link_verify_user_not_found(
        self, client: AsyncClient, csrf_token
    ):
        """Should reject token if user no longer exists or token not found."""
        response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": "nonexistent_token_12345"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 400
        assert "Invalid or expired magic link token" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_magic_link_verify_inactive_user(
        self, client: AsyncClient, db_session, csrf_token
    ):
        """Should reject token for inactive user."""
        now = datetime.now(UTC)
        user = User(
            email="inactive@test.com",
            is_active=False,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        token = "token_inactive_user"
        magic_token = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token),
            purpose="login",
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        db_session.add(magic_token)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 400
        assert "User account is inactive or not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_magic_link_verify_unverified_email(
        self, client: AsyncClient, db_session, csrf_token
    ):
        """Should reject login if email not verified."""
        now = datetime.now(UTC)
        user = User(
            email="unverified@test.com",
            is_active=True,
            is_email_verified=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        token = "token_unverified_email"
        magic_token = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token),
            purpose="login",
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        db_session.add(magic_token)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 403
        assert "verify your email address" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_magic_link_verify_account_locked(
        self, client: AsyncClient, db_session, csrf_token
    ):
        """Should reject login if account is locked."""
        now = datetime.now(UTC)
        user = User(
            email="locked@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        token = "token_locked_account"
        magic_token = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token),
            purpose="login",
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        db_session.add(magic_token)
        await db_session.commit()

        from app.core.redis_client import get_redis

        redis = await get_redis()
        lockout_key = f"lockout:{user.id}"
        lockout_until = (now + timedelta(minutes=15)).isoformat()
        await redis.setex(lockout_key, 900, lockout_until)

        response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 429
        assert "Account temporarily locked" in response.json()["detail"]
