"""Happy path tests for WebAuthn registration."""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.db.models.auth import User, WebAuthnCredential

pytestmark = [pytest.mark.security, pytest.mark.integration]


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create a test user."""
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
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def user_with_credential(db_session):
    """Create a user with an existing WebAuthn credential."""
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

    credential = WebAuthnCredential(
        user_id=user.id,
        credential_id=bytes.fromhex("deadbeef"),
        public_key=b"fake_public_key",
        sign_count=0,
        transports=["internal"],
        created_at=now,
        updated_at=now,
    )
    db_session.add(credential)
    await db_session.commit()
    await db_session.refresh(credential)
    return user, credential


class TestWebAuthnRegistrationHappyPaths:
    """Test successful WebAuthn registration flows."""

    @pytest.mark.asyncio
    @patch("app.core.challenge_storage.store_challenge")
    @patch("app.api.v1.auth.get_webauthn_manager")
    async def test_new_user_registration_start(
        self,
        mock_get_webauthn_manager,
        mock_store_challenge,
        client: AsyncClient,
        csrf_token,
        db_session,
    ):
        """Should successfully start registration for new user."""
        mock_manager = Mock()
        mock_options = Mock()
        mock_options.challenge = b"\xde\xad\xbe\xef"
        mock_manager.generate_registration_options.return_value = mock_options
        mock_get_webauthn_manager.return_value = mock_manager

        mock_store_challenge.return_value = "challenge-123"

        with patch("app.api.v1.auth.options_to_json_dict") as mock_json:
            mock_json.return_value = {
                "challenge": "deadbeef",
                "rp": {"name": "FitFolio", "id": "localhost"},
                "user": {
                    "id": "user-123",
                    "name": "newuser@test.com",
                    "displayName": "newuser@test.com",
                },
                "pubKeyCredParams": [{"type": "public-key", "alg": -7}],
            }
            response = await client.post(
                "/api/v1/auth/webauthn/register/start",
                json={"email": "newuser@test.com"},
                cookies={"csrf_token": csrf_token},
                headers={"X-CSRF-Token": csrf_token},
            )

        assert response.status_code == 200
        data = response.json()
        assert "options" in data and "challenge_id" in data
        assert data["challenge_id"] == "challenge-123"

        from sqlalchemy import select

        stmt = select(User).where(User.email == "newuser@test.com")
        result = await db_session.execute(stmt)
        user = result.scalar_one_or_none()
        assert (
            user is not None
            and user.is_active is True
            and user.is_email_verified is False
        )

    @pytest.mark.asyncio
    @patch("app.core.challenge_storage.store_challenge")
    @patch("app.api.v1.auth.get_webauthn_manager")
    async def test_existing_user_registration_start(
        self,
        mock_get_webauthn_manager,
        mock_store_challenge,
        client: AsyncClient,
        csrf_token,
        test_user,
    ):
        """Should successfully start registration for existing user."""
        mock_manager = Mock()
        mock_options = Mock()
        mock_options.challenge = b"\xde\xad\xbe\xef"
        mock_manager.generate_registration_options.return_value = mock_options
        mock_get_webauthn_manager.return_value = mock_manager

        mock_store_challenge.return_value = "challenge-456"
        with patch("app.api.v1.auth.options_to_json_dict") as mock_json:
            mock_json.return_value = {"challenge": "deadbeef"}
            response = await client.post(
                "/api/v1/auth/webauthn/register/start",
                json={"email": test_user.email},
                cookies={"csrf_token": csrf_token},
                headers={"X-CSRF-Token": csrf_token},
            )
        assert response.status_code == 200
        assert response.json()["challenge_id"] == "challenge-456"

    @pytest.mark.asyncio
    @patch("app.core.challenge_storage.store_challenge")
    @patch("app.api.v1.auth.get_webauthn_manager")
    async def test_registration_excludes_existing_credentials(
        self,
        mock_get_webauthn_manager,
        mock_store_challenge,
        client: AsyncClient,
        csrf_token,
        user_with_credential,
    ):
        """Should exclude existing credentials in registration options."""
        user, credential = user_with_credential
        mock_manager = Mock()
        mock_options = Mock()
        mock_options.challenge = b"\xde\xad\xbe\xef"
        mock_manager.generate_registration_options.return_value = mock_options
        mock_get_webauthn_manager.return_value = mock_manager
        mock_store_challenge.return_value = "challenge-789"

        with patch("app.api.v1.auth.options_to_json_dict") as mock_json:
            mock_json.return_value = {"challenge": "deadbeef"}
            response = await client.post(
                "/api/v1/auth/webauthn/register/start",
                json={"email": user.email},
                cookies={"csrf_token": csrf_token},
                headers={"X-CSRF-Token": csrf_token},
            )
        assert response.status_code == 200
        call_kwargs = mock_manager.generate_registration_options.call_args.kwargs
        assert "exclude_credentials" in call_kwargs
        exclude_list = call_kwargs["exclude_credentials"]
        assert len(exclude_list) == 1 and exclude_list[0]["id"] == "deadbeef"

    @pytest.mark.asyncio
    @patch("app.core.challenge_storage.retrieve_and_delete_challenge")
    @patch("app.api.v1.auth.get_webauthn_manager")
    async def test_registration_finish_creates_credential(
        self,
        mock_get_webauthn_manager,
        mock_retrieve_challenge,
        client: AsyncClient,
        csrf_token,
        test_user,
        db_session,
    ):
        """Should create credential on successful registration finish."""
        mock_retrieve_challenge.return_value = (test_user.email, "deadbeef")
        mock_manager = Mock()
        mock_manager.rp_id = "localhost"
        mock_manager.origin = "http://localhost:3000"
        mock_manager.verify_registration_response.return_value = {
            "credential_id": "abc123",
            "public_key": b"fake_key",
            "sign_count": 0,
            "transports": ["internal"],
            "backed_up": False,
            "uv_available": True,
        }
        mock_get_webauthn_manager.return_value = mock_manager
        response = await client.post(
            "/api/v1/auth/webauthn/register/finish",
            json={
                "email": test_user.email,
                "credential": {"id": "abc123", "response": {}, "type": "public-key"},
                "challenge_id": "challenge-123",
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "Passkey registered successfully" in data["message"]
        assert data["credential_id"] == "abc123"

        from sqlalchemy import select

        stmt = select(WebAuthnCredential).where(
            WebAuthnCredential.user_id == test_user.id
        )
        result = await db_session.execute(stmt)
        credentials = result.scalars().all()
        assert len(credentials) == 1 and credentials[0].credential_id == bytes.fromhex(
            "abc123"
        )
