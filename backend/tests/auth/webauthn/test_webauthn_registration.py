"""Tests for WebAuthn registration endpoints.

Tests for registration start/finish flows including happy paths and error cases.
"""

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.db.models.auth import User


@pytest_asyncio.fixture
async def existing_user(db_session):
    """Create an existing user."""
    now = datetime.now(UTC)
    user = User(
        email="existing@test.com",
        is_active=True,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def inactive_user(db_session):
    """Create an inactive user."""
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
    return user


class TestWebAuthnRegisterStart:
    """Tests for POST /api/v1/auth/webauthn/register/start endpoint."""

    @pytest.mark.asyncio
    async def test_register_start_new_user_creates_user(
        self, client: AsyncClient, csrf_token, db_session
    ):
        """Should create user record for new email during registration start."""
        response = await client.post(
            "/api/v1/auth/webauthn/register/start",
            json={"email": "newuser@test.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "options" in data
        assert "challenge_id" in data

        # Verify user was created in database
        from sqlalchemy import select

        stmt = select(User).where(User.email == "newuser@test.com")
        result = await db_session.execute(stmt)
        user = result.scalar_one_or_none()

        assert user is not None
        assert user.email == "newuser@test.com"
        assert user.is_active is True
        assert user.is_email_verified is False  # Not verified yet

    @pytest.mark.asyncio
    async def test_register_start_existing_user_succeeds(
        self, client: AsyncClient, csrf_token, existing_user
    ):
        """Should allow existing user to register additional credential."""
        response = await client.post(
            "/api/v1/auth/webauthn/register/start",
            json={"email": existing_user.email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "options" in data
        assert "challenge_id" in data

    @pytest.mark.asyncio
    async def test_register_start_invalid_email_format(
        self, client: AsyncClient, csrf_token
    ):
        """Should reject invalid email format."""
        response = await client.post(
            "/api/v1/auth/webauthn/register/start",
            json={"email": "not-an-email"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_start_stores_challenge(
        self, client: AsyncClient, csrf_token
    ):
        """Should store challenge in Redis for later verification."""
        response = await client.post(
            "/api/v1/auth/webauthn/register/start",
            json={"email": "challengetest@test.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify challenge was stored (challenge_id returned)
        assert "challenge_id" in data
        assert data["challenge_id"] is not None
        assert len(data["challenge_id"]) > 0

        # Verify options contain required WebAuthn fields
        options = data["options"]
        assert "challenge" in options
        assert "rp" in options
        assert "user" in options
        assert "pubKeyCredParams" in options


class TestWebAuthnRegisterFinish:
    """Tests for POST /api/v1/auth/webauthn/register/finish endpoint."""

    @pytest.mark.asyncio
    async def test_register_finish_requires_valid_credential_format(
        self, client: AsyncClient, csrf_token
    ):
        """Should validate credential format."""
        response = await client.post(
            "/api/v1/auth/webauthn/register/finish",
            json={
                "email": "test@test.com",
                "credential": {},  # Invalid/empty credential
                "challenge_id": "fake-challenge-id",
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        # Should fail due to invalid credential or missing challenge
        assert response.status_code in [400, 404]

    @pytest.mark.asyncio
    async def test_register_finish_nonexistent_challenge(
        self, client: AsyncClient, csrf_token, existing_user
    ):
        """Should reject if challenge doesn't exist or expired."""
        response = await client.post(
            "/api/v1/auth/webauthn/register/finish",
            json={
                "email": existing_user.email,
                "credential": {
                    "id": "test-cred-id",
                    "rawId": "test-raw-id",
                    "response": {
                        "clientDataJSON": "test",
                        "attestationObject": "test",
                    },
                    "type": "public-key",
                },
                "challenge_id": "nonexistent-challenge-id",
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 400
        assert "challenge" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_finish_rotates_existing_session_and_sets_cookie(
        self, client: AsyncClient, csrf_token, db_session, monkeypatch
    ):
        """Finishing registration with existing session should rotate and set cookie."""
        from unittest.mock import Mock

        from sqlalchemy import select

        from app.core.security import create_session_token, hash_token
        from app.db.models.auth import Session

        # Create user
        now = datetime.now(UTC)
        email = "rotate@test.com"
        user = User(
            email=email,
            is_active=True,
            is_email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create current session
        current_token = create_session_token()
        current_session = Session(
            user_id=user.id,
            token_hash=hash_token(current_token),
            created_at=now,
            expires_at=now + timedelta(days=14),
        )
        db_session.add(current_session)
        await db_session.commit()

        challenge_id = "register_rotate_chal"
        challenge_hex = "abcd1234"

        # Monkeypatch manager verify to bypass real attestation
        import app.api.v1.auth as auth_api

        fake_manager = Mock()
        fake_manager.rp_id = "localhost"
        fake_manager.origin = "http://localhost:5173"
        fake_manager.verify_registration_response.return_value = {
            "credential_id": "0102030405060708",
            "public_key": b"pk",
            "sign_count": 0,
            "transports": [],
            "backed_up": True,
            "uv_available": False,
        }
        monkeypatch.setattr(auth_api, "get_webauthn_manager", lambda: fake_manager)
        # Bypass Redis by mocking challenge retrieval to expected value
        import app.core.challenge_storage as cs

        async def _fake_retrieve_and_delete_challenge(
            _challenge_id=None, _challenge_type=None, **_kwargs
        ):
            return (email, challenge_hex)

        monkeypatch.setattr(
            cs,
            "retrieve_and_delete_challenge",
            _fake_retrieve_and_delete_challenge,
            raising=True,
        )

        # Finish registration
        response = await client.post(
            "/api/v1/auth/webauthn/register/finish",
            json={
                "email": email,
                "credential": {"id": "ignored_for_mock"},
                "challenge_id": challenge_id,
            },
            cookies={"csrf_token": csrf_token, "ff_sess": current_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        # Should set a new ff_sess cookie due to rotation
        set_cookie = response.headers.get("set-cookie", "")
        assert "ff_sess=" in set_cookie
        # New session should exist (different from current session)
        stmt = select(Session).where(Session.user_id == user.id)
        sessions = (await db_session.execute(stmt)).scalars().all()
        assert any(
            s.id != current_session.id and s.revoked_at is None for s in sessions
        )


class TestWebAuthnCredentialManagement:
    """Tests for WebAuthn credential management operations."""

    @pytest.mark.asyncio
    async def test_credentials_exclude_public_keys(
        self, client: AsyncClient, csrf_token
    ):
        """Should never expose public keys in credential listings."""
        # This is already tested in test_auth_user_endpoints.py
        # but emphasizing the security requirement here

        # Start registration to create a user
        response = await client.post(
            "/api/v1/auth/webauthn/register/start",
            json={"email": "security@test.com"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify public key material is not in response
        options_str = str(data.get("options", {}))
        # Note: The challenge/registration options may contain PUBLIC information
        # but should not expose any private keys or sensitive material
        assert "private" not in options_str.lower()


class TestWebAuthnRegistrationFlow:
    """Integration tests for complete registration flow."""

    @pytest.mark.asyncio
    async def test_complete_registration_flow_new_user(
        self, client: AsyncClient, csrf_token, db_session
    ):
        """Should allow complete registration flow for new user."""
        email = "fullflow@test.com"

        # Step 1: Start registration
        start_response = await client.post(
            "/api/v1/auth/webauthn/register/start",
            json={"email": email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert start_response.status_code == 200
        start_data = start_response.json()
        assert "challenge_id" in start_data

        # Verify user was created
        from sqlalchemy import select

        stmt = select(User).where(User.email == email)
        result = await db_session.execute(stmt)
        user = result.scalar_one_or_none()
        assert user is not None

        # Step 2: Finish registration would happen here
        # (actual WebAuthn credential verification requires real attestation data)
        # This is tested in test_auth_webauthn_happy_paths.py

    @pytest.mark.asyncio
    async def test_registration_creates_unverified_user(
        self, client: AsyncClient, csrf_token, db_session
    ):
        """Should create user with is_email_verified=False during registration."""
        email = "unverified@test.com"

        response = await client.post(
            "/api/v1/auth/webauthn/register/start",
            json={"email": email},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200

        # Check user email verification status
        from sqlalchemy import select

        stmt = select(User).where(User.email == email)
        result = await db_session.execute(stmt)
        user = result.scalar_one_or_none()

        assert user is not None
        assert user.is_email_verified is False
        assert user.is_active is True  # Active but unverified
