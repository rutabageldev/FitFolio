"""Tests for listing user's WebAuthn credentials."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.core.security import create_session_token, hash_token
from app.db.models.auth import Session, User, WebAuthnCredential

pytestmark = [pytest.mark.security, pytest.mark.integration]


class TestWebAuthnCredentialsList:
    """Test WebAuthn credentials listing endpoint."""

    @pytest.mark.asyncio
    async def test_list_credentials_unauthorized(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/webauthn/credentials")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_credentials_invalid_session(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/auth/webauthn/credentials",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_credentials_expired_session(
        self, client: AsyncClient, db_session
    ):
        now = datetime.now(UTC)
        user = User(
            email="expiredsess@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        token = create_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now - timedelta(days=15),
            expires_at=now - timedelta(days=1),
            ip="127.0.0.1",
            user_agent="test",
        )
        db_session.add(session)
        await db_session.commit()

        response = await client.get(
            "/api/v1/auth/webauthn/credentials",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_credentials_success_empty(
        self, client: AsyncClient, db_session
    ):
        now = datetime.now(UTC)
        user = User(
            email="nocreds@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        token = create_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + timedelta(days=14),
            ip="127.0.0.1",
            user_agent="test",
        )
        db_session.add(session)
        await db_session.commit()

        response = await client.get(
            "/api/v1/auth/webauthn/credentials",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_credentials_success_with_credentials(
        self, client: AsyncClient, db_session
    ):
        now = datetime.now(UTC)
        user = User(
            email="hascreds@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        cred1 = WebAuthnCredential(
            user_id=user.id,
            credential_id=bytes.fromhex("0102030405060708"),
            public_key=b"fake_public_key_1",
            sign_count=0,
            created_at=now,
            updated_at=now,
        )
        cred2 = WebAuthnCredential(
            user_id=user.id,
            credential_id=bytes.fromhex("0908070605040302"),
            public_key=b"fake_public_key_2",
            sign_count=5,
            nickname="My Phone",
            created_at=now,
            updated_at=now + timedelta(days=1),
        )
        db_session.add(cred1)
        db_session.add(cred2)

        token = create_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + timedelta(days=14),
            ip="127.0.0.1",
            user_agent="test",
        )
        db_session.add(session)
        await db_session.commit()

        response = await client.get(
            "/api/v1/auth/webauthn/credentials",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        credentials = response.json()
        assert len(credentials) == 2
        cred_ids = [c["id"] for c in credentials]
        assert "0102030405060708" in cred_ids and "0908070605040302" in cred_ids
        nicknamed = [c for c in credentials if c.get("nickname") == "My Phone"]
        assert len(nicknamed) == 1 and nicknamed[0]["last_used_at"] is not None
