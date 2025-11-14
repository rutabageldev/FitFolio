import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.v1.auth import WebAuthnRegisterStartRequest, start_webauthn_registration
from app.db.models.auth import User, WebAuthnCredential

pytestmark = [pytest.mark.security, pytest.mark.integration]


def make_request() -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/webauthn/register/start",
        "headers": [],
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_register_start_success_creates_user_and_stores_challenge(db_session):
    email = f"start-{uuid.uuid4().hex}@test.com"
    req = WebAuthnRegisterStartRequest(email=email)

    # Fake manager with options that includes a bytes challenge with hex()
    def _fake_mgr():
        return SimpleNamespace(
            rp_id="fitfolio.local",
            origin="https://fitfolio.local",
            generate_registration_options=lambda **_kw: SimpleNamespace(
                challenge=b"\x01\x02\x03"
            ),
        )

    async def _fake_store_challenge(user_email, challenge_hex, challenge_type):
        assert user_email == email.lower()
        assert challenge_hex == "010203"
        assert challenge_type == "registration"
        return "ch-123"

    with (
        patch("app.api.v1.auth.get_webauthn_manager", _fake_mgr),
        patch("app.core.challenge_storage.store_challenge", _fake_store_challenge),
        patch(
            "app.api.v1.auth.options_to_json_dict",
            lambda options: {"challenge": options.challenge.hex()},
        ),
    ):
        res = await start_webauthn_registration(req, db_session)

    assert res.challenge_id == "ch-123"
    assert res.options  # options serialized
    # User should exist now
    u = await db_session.execute(
        User.__table__.select().where(User.email == email.lower())
    )
    assert u.first() is not None


@pytest.mark.asyncio
async def test_register_start_store_challenge_failure_returns_500(db_session):
    email = f"start-fail-{uuid.uuid4().hex}@test.com"
    req = WebAuthnRegisterStartRequest(email=email)

    def _fake_mgr():
        return SimpleNamespace(
            rp_id="fitfolio.local",
            origin="https://fitfolio.local",
            generate_registration_options=lambda **_kw: SimpleNamespace(
                challenge=b"\x0a"
            ),
        )

    async def _raise_store(*_a, **_k):
        raise RuntimeError("redis down")

    with (
        patch("app.api.v1.auth.get_webauthn_manager", _fake_mgr),
        patch("app.core.challenge_storage.store_challenge", _raise_store),
        patch(
            "app.api.v1.auth.options_to_json_dict",
            lambda options: {"challenge": options.challenge.hex()},
        ),
    ):
        with pytest.raises(HTTPException) as ei:
            await start_webauthn_registration(req, db_session)
    assert ei.value.status_code == 500


@pytest.mark.asyncio
async def test_register_start_includes_exclude_credentials_when_existing(db_session):
    # Create existing user and a credential
    email = f"start-exists-{uuid.uuid4().hex}@test.com"
    user = User(
        email=email,
        is_active=True,
        is_email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    cred = WebAuthnCredential(
        user_id=user.id,
        credential_id=b"\xaa\xbb",  # bytes so .hex() works
        public_key=b"\x01\x02",
        transports=["usb"],
        sign_count=0,
    )
    db_session.add(cred)
    await db_session.commit()

    req = WebAuthnRegisterStartRequest(email=email)

    captured = {"exclude_len": 0}

    def _fake_mgr():
        # Assert exclude_credentials contains our single entry
        def _gen(**kw):
            captured["exclude_len"] = len(kw.get("exclude_credentials", []))
            return SimpleNamespace(challenge=b"\x04")

        return SimpleNamespace(
            rp_id="fitfolio.local",
            origin="https://fitfolio.local",
            generate_registration_options=_gen,
        )

    async def _fake_store_challenge(**_kw):
        return "ch-x"

    with (
        patch("app.api.v1.auth.get_webauthn_manager", _fake_mgr),
        patch("app.core.challenge_storage.store_challenge", _fake_store_challenge),
        patch(
            "app.api.v1.auth.options_to_json_dict",
            lambda options: {"challenge": options.challenge.hex()},
        ),
    ):
        res = await start_webauthn_registration(req, db_session)

    assert res.challenge_id == "ch-x"
    assert captured["exclude_len"] == 1
