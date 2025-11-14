import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from app.api.v1.auth import WebAuthnRegisterFinishRequest, finish_webauthn_registration
from app.db.models.auth import User

pytestmark = [pytest.mark.security, pytest.mark.integration]


def make_request() -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/webauthn/register/finish",
        "headers": [],
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_register_finish_missing_challenge_returns_400(db_session):
    now = datetime.now(UTC)
    email = f"finish-{uuid.uuid4().hex}@test.com"
    user = User(
        email=email,
        is_active=True,
        is_email_verified=False,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()

    req = WebAuthnRegisterFinishRequest(
        email=email,
        challenge_id="ch-missing",
        credential={"id": "cred", "rawId": "raw", "response": {}, "type": "public-key"},
    )
    http_req = make_request()
    resp = Response()

    async def _return_none(**_kw):
        return None

    target = "app.core.challenge_storage.retrieve_and_delete_challenge"
    with patch(target, _return_none):
        with pytest.raises(HTTPException) as ei:
            await finish_webauthn_registration(req, resp, http_req, db_session)
    assert ei.value.status_code == 400


@pytest.mark.asyncio
async def test_register_finish_user_not_found_returns_404(db_session):
    # No user created for this email
    email = f"finish-missing-{uuid.uuid4().hex}@test.com"
    req = WebAuthnRegisterFinishRequest(
        email=email,
        challenge_id="ch-any",
        credential={"id": "cred", "rawId": "raw", "response": {}, "type": "public-key"},
    )
    http_req = make_request()
    resp = Response()
    with pytest.raises(HTTPException) as ei:
        await finish_webauthn_registration(req, resp, http_req, db_session)
    assert ei.value.status_code == 404


@pytest.mark.asyncio
async def test_register_finish_challenge_email_mismatch_returns_400(db_session):
    now = datetime.now(UTC)
    email = f"finish-mismatch-{uuid.uuid4().hex}@test.com"
    user = User(
        email=email,
        is_active=True,
        is_email_verified=False,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()

    req = WebAuthnRegisterFinishRequest(
        email=email,
        challenge_id="ch-id",
        credential={"id": "cred", "rawId": "raw", "response": {}, "type": "public-key"},
    )
    http_req = make_request()
    resp = Response()

    async def _return_other(**_kw):
        return ("other@example.com", "0a0b")

    with patch(
        "app.core.challenge_storage.retrieve_and_delete_challenge", _return_other
    ):
        with pytest.raises(HTTPException) as ei:
            await finish_webauthn_registration(req, resp, http_req, db_session)
    assert ei.value.status_code == 400


@pytest.mark.asyncio
async def test_register_finish_verify_error_returns_400(db_session):
    now = datetime.now(UTC)
    email = f"finish-verifyerr-{uuid.uuid4().hex}@test.com"
    user = User(
        email=email,
        is_active=True,
        is_email_verified=False,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()

    req = WebAuthnRegisterFinishRequest(
        email=email,
        challenge_id="ch-id",
        credential={"id": "cred", "rawId": "raw", "response": {}, "type": "public-key"},
    )
    http_req = make_request()
    resp = Response()

    async def _return_tuple(**_kw):
        return (email.lower(), "0a0b")

    class _Mgr:
        rp_id = "fitfolio.local"
        origin = "https://fitfolio.local"

        def verify_registration_response(self, **_kw):
            raise ValueError("bad attestation")

    with (
        patch(
            "app.core.challenge_storage.retrieve_and_delete_challenge", _return_tuple
        ),
        patch("app.api.v1.auth.get_webauthn_manager", lambda: _Mgr()),
    ):
        with pytest.raises(HTTPException) as ei:
            await finish_webauthn_registration(req, resp, http_req, db_session)
    assert ei.value.status_code == 400


@pytest.mark.asyncio
async def test_register_finish_success_rotates_cookie_when_session_present(
    monkeypatch, db_session
):
    now = datetime.now(UTC)
    email = f"finish-success-{uuid.uuid4().hex}@test.com"
    user = User(
        email=email,
        is_active=True,
        is_email_verified=False,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    req = WebAuthnRegisterFinishRequest(
        email=email,
        challenge_id="ch-id",
        credential={"id": "cred", "rawId": "raw", "response": {}, "type": "public-key"},
    )
    http_req = make_request()
    resp = Response()

    async def _return_tuple(**_kw):
        return (email.lower(), "0a0b")

    class _Mgr:
        rp_id = "fitfolio.local"
        origin = "https://fitfolio.local"

        def verify_registration_response(self, **_kw):
            return {
                "credential_id": "aabb",
                "public_key": b"\x01\x02",
                "sign_count": 0,
                "transports": ["usb"],
                "backed_up": False,
                "uv_available": True,
            }

    async def _get_opt_session(**_kw):
        return object(), None

    async def _rotate(_current_session, _db, force_reason=None):
        # mark arg as intentionally unused for linter
        del force_reason
        return object(), "newtoken123"

    monkeypatch.setenv("COOKIE_SECURE", "true")
    with (
        patch(
            "app.core.challenge_storage.retrieve_and_delete_challenge", _return_tuple
        ),
        patch("app.api.v1.auth.get_webauthn_manager", lambda: _Mgr()),
        patch("app.api.deps.get_optional_session_with_rotation", _get_opt_session),
        patch("app.core.session_rotation.check_and_rotate_if_needed", _rotate),
    ):
        res = await finish_webauthn_registration(req, resp, http_req, db_session)

    cookies = [
        c for c in resp.headers.getlist("set-cookie") if c.startswith("ff_sess=")
    ]
    assert cookies, "rotation cookie should be set"
    assert "Secure" in cookies[0]
    assert res.message.startswith("Passkey")
