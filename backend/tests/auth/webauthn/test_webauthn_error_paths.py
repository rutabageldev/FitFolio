"""WebAuthn error-path tests for registration and authentication."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from app.db.models.auth import User

pytestmark = [pytest.mark.security, pytest.mark.integration]


@pytest.fixture
async def csrf_token(client: AsyncClient):
    resp = await client.get("/healthz")
    return resp.cookies["csrf_token"]


class TestWebAuthnRegisterErrorPaths:
    """Error handling in registration finish."""

    @pytest.mark.asyncio
    async def test_webauthn_register_finish_user_not_found(
        self, client: AsyncClient, csrf_token
    ):
        response = await client.post(
            "/api/v1/auth/webauthn/register/finish",
            json={
                "email": "nonexistent@test.com",
                "credential": {"id": "fake_cred_id"},
                "challenge_id": "fake_challenge",
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_webauthn_register_finish_invalid_challenge(
        self, client: AsyncClient, db_session
    ):
        csrf_response = await client.get("/healthz")
        csrf_token = csrf_response.cookies["csrf_token"]
        now = datetime.now(UTC)
        user = User(
            email="webauthn@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        response = await client.post(
            "/api/v1/auth/webauthn/register/finish",
            json={
                "email": "webauthn@test.com",
                "credential": {"id": "fake_cred_id"},
                "challenge_id": "invalid_challenge_id",
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 400
        assert "Invalid or expired challenge" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_webauthn_register_finish_challenge_email_mismatch(
        self, client: AsyncClient, db_session, csrf_token
    ):
        now = datetime.now(UTC)
        user1 = User(
            email="user1@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        user2 = User(
            email="user2@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user1)
        db_session.add(user2)
        await db_session.commit()
        from app.core.redis_client import get_redis

        redis = await get_redis()
        challenge_id = "test_challenge_123"
        challenge_hex = "abcd1234"
        challenge_key = f"webauthn_challenge:{challenge_id}:registration"
        await redis.setex(challenge_key, 300, f"user1@test.com|{challenge_hex}")
        response = await client.post(
            "/api/v1/auth/webauthn/register/finish",
            json={
                "email": "user2@test.com",
                "credential": {"id": "fake_cred_id"},
                "challenge_id": challenge_id,
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 400
        assert ("different user" in response.json()["detail"]) or (
            "Invalid or expired challenge" in response.json()["detail"]
        )


class TestWebAuthnAuthenticateErrorPaths:
    """Error handling in authentication."""

    @pytest.mark.asyncio
    async def test_webauthn_authenticate_start_user_not_found(
        self, client: AsyncClient, csrf_token
    ):
        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/start",
            json={"email": "nonexistent@test.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_webauthn_authenticate_start_no_credentials(
        self, client: AsyncClient, db_session, csrf_token
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
        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/start",
            json={"email": "nocreds@test.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 400
        assert "No passkeys registered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_authenticate_finish_user_not_found(
        self, client: AsyncClient, csrf_token
    ):
        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/finish",
            json={
                "email": "nonexistent@test.com",
                "credential": {"id": "fake_id"},
                "challenge_id": "fake_challenge",
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_authenticate_finish_invalid_challenge(
        self, client: AsyncClient, db_session, csrf_token
    ):
        now = datetime.now(UTC)
        user = User(
            email="authtest@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/finish",
            json={
                "email": user.email,
                "credential": {"id": "fake_id"},
                "challenge_id": "invalid_challenge",
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 400
        assert "Invalid or expired challenge" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_authenticate_finish_missing_credential_id(
        self, client: AsyncClient, db_session, csrf_token
    ):
        now = datetime.now(UTC)
        user = User(
            email="missingcred@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        from app.core.redis_client import get_redis

        redis = await get_redis()
        challenge_id = "test_auth_challenge"
        await redis.setex(
            f"webauthn_challenge:{challenge_id}:authentication",
            300,
            "missingcred@test.com|abcd1234",
        )
        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/finish",
            json={
                "email": "missingcred@test.com",
                "credential": {},
                "challenge_id": challenge_id,
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 400
        assert ("Credential ID is required" in response.json()["detail"]) or (
            "Invalid or expired challenge" in response.json()["detail"]
        )

    @pytest.mark.asyncio
    async def test_authenticate_finish_credential_not_found(
        self, client: AsyncClient, db_session, csrf_token
    ):
        now = datetime.now(UTC)
        user = User(
            email="badcred@test.com",
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        from app.core.redis_client import get_redis

        redis = await get_redis()
        challenge_id = "test_badcred_challenge"
        await redis.setex(
            f"webauthn_challenge:{challenge_id}:authentication",
            300,
            "badcred@test.com|abcd1234",
        )
        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/finish",
            json={
                "email": "badcred@test.com",
                "credential": {"id": "0102030405060708"},
                "challenge_id": challenge_id,
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 400
        assert ("Invalid credential" in response.json()["detail"]) or (
            "Invalid or expired challenge" in response.json()["detail"]
        )
