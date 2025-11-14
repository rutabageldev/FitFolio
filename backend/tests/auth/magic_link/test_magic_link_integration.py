"""Magic link start/verify integration tests (extracted)."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.db.models.auth import MagicLinkToken, User

pytestmark = [pytest.mark.security, pytest.mark.integration]


class TestMagicLinkVerifyIntegration:
    """Integration tests for magic link verify endpoint."""

    @pytest.mark.asyncio
    async def test_verify_invalid_token_format_returns_400(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/magic-link/verify", json={"token": "invalid"}
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_verify_nonexistent_token_returns_400(self, client: AsyncClient):
        fake_token = "a" * 43
        response = await client.post(
            "/api/v1/auth/magic-link/verify", json={"token": fake_token}
        )
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_verify_expired_token_returns_400(
        self, client: AsyncClient, db_session
    ):
        now = datetime.now(UTC)
        user = User(
            email="expired@test.com",
            is_active=True,
            is_email_verified=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        from app.core.security import hash_token

        token_value = "expired_token_value_123"
        expired_token = MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(token_value),
            purpose="email_verification",
            created_at=now - timedelta(hours=48),
            expires_at=now - timedelta(hours=24),
        )
        db_session.add(expired_token)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/magic-link/verify", json={"token": token_value}
        )
        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()
