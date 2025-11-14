"""Happy path tests for WebAuthn authentication."""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.db.models.auth import User, WebAuthnCredential

pytestmark = [pytest.mark.security, pytest.mark.integration]


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


class TestWebAuthnAuthenticationHappyPaths:
    """Test successful WebAuthn authentication flows."""

    @pytest.mark.asyncio
    @patch("app.core.challenge_storage.store_challenge")
    @patch("app.api.v1.auth.get_webauthn_manager")
    async def test_authentication_start_with_credentials(
        self,
        mock_get_webauthn_manager,
        mock_store_challenge,
        client: AsyncClient,
        csrf_token,
        user_with_credential,
    ):
        """Should start authentication with allowCredentials list."""
        user, credential = user_with_credential
        mock_manager = Mock()
        mock_options = Mock()
        mock_options.challenge = b"\xde\xad\xbe\xef"
        mock_manager.generate_authentication_options.return_value = mock_options
        mock_get_webauthn_manager.return_value = mock_manager
        mock_store_challenge.return_value = "auth-challenge-123"

        with patch("app.api.v1.auth.options_to_json_dict") as mock_json:
            mock_json.return_value = {
                "challenge": "deadbeef",
                "allowCredentials": [{"id": "deadbeef", "type": "public-key"}],
            }
            response = await client.post(
                "/api/v1/auth/webauthn/authenticate/start",
                json={"email": user.email},
                cookies={"csrf_token": csrf_token},
                headers={"X-CSRF-Token": csrf_token},
            )
        assert response.status_code == 200
        data = response.json()
        assert (
            "options" in data
            and "challenge_id" in data
            and data["challenge_id"] == "auth-challenge-123"
        )
        call_kwargs = mock_manager.generate_authentication_options.call_args.kwargs
        assert "allow_credentials" in call_kwargs

    @pytest.mark.asyncio
    @patch("app.core.challenge_storage.retrieve_and_delete_challenge")
    @patch("app.api.v1.auth.get_webauthn_manager")
    async def test_authentication_finish_creates_session(
        self,
        mock_get_webauthn_manager,
        mock_retrieve_challenge,
        client: AsyncClient,
        csrf_token,
        user_with_credential,
        db_session,
    ):
        """Should create session on successful authentication."""
        user, credential = user_with_credential
        mock_retrieve_challenge.return_value = (user.email, "deadbeef")
        mock_manager = Mock()
        mock_manager.rp_id = "localhost"
        mock_manager.origin = "http://localhost:3000"
        mock_manager.verify_authentication_response.return_value = {"new_sign_count": 1}
        mock_get_webauthn_manager.return_value = mock_manager
        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/finish",
            json={
                "email": user.email,
                "credential": {
                    "id": "deadbeef",
                    "response": {"clientDataJSON": "fake", "authenticatorData": "fake"},
                    "type": "public-key",
                },
                "challenge_id": "auth-challenge-123",
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "successful" in data["message"].lower() and "session_token" in data
        from sqlalchemy import select

        from app.db.models.auth import Session

        stmt = select(Session).where(Session.user_id == user.id)
        result = await db_session.execute(stmt)
        sessions = result.scalars().all()
        assert len(sessions) == 1
        assert "ff_sess" in response.cookies
        # Validate cookie flags
        set_cookie = response.headers.get("set-cookie", "")
        assert "HttpOnly" in set_cookie
        assert "SameSite=lax" in set_cookie
        # In dev config, Secure may be false

    @pytest.mark.asyncio
    @patch("app.core.challenge_storage.retrieve_and_delete_challenge")
    @patch("app.api.v1.auth.get_webauthn_manager")
    async def test_authentication_updates_sign_count(
        self,
        mock_get_webauthn_manager,
        mock_retrieve_challenge,
        client: AsyncClient,
        csrf_token,
        user_with_credential,
        db_session,
    ):
        """Should update credential sign count after authentication."""
        user, credential = user_with_credential
        original_sign_count = credential.sign_count
        mock_retrieve_challenge.return_value = (user.email, "deadbeef")
        mock_manager = Mock()
        mock_manager.rp_id = "localhost"
        mock_manager.origin = "http://localhost:3000"
        mock_manager.verify_authentication_response.return_value = {"new_sign_count": 5}
        mock_get_webauthn_manager.return_value = mock_manager
        response = await client.post(
            "/api/v1/auth/webauthn/authenticate/finish",
            json={
                "email": user.email,
                "credential": {"id": "deadbeef", "response": {}, "type": "public-key"},
                "challenge_id": "auth-challenge-123",
            },
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 200
        await db_session.refresh(credential)
        assert (
            credential.sign_count == 5 and credential.sign_count != original_sign_count
        )
