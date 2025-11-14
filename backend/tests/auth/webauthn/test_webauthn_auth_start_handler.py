import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.v1.auth import (
    WebAuthnAuthenticateStartRequest,
    start_webauthn_authentication,
)
from app.db.models.auth import User, WebAuthnCredential

pytestmark = [pytest.mark.security, pytest.mark.integration]


def make_request() -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/webauthn/authenticate/start",
        "headers": [],
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_auth_start_success_stores_challenge_and_returns_options(db_session):
    email = f"authstart-{uuid.uuid4().hex}@test.com"
    user = User(email=email, is_active=True, is_email_verified=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    cred = WebAuthnCredential(
        user_id=user.id, credential_id=b"\xaa\xbb", public_key=b"\x01\x02", sign_count=0
    )
    db_session.add(cred)
    await db_session.commit()

    req = WebAuthnAuthenticateStartRequest(email=email)

    def _mgr():
        return SimpleNamespace(
            generate_authentication_options=lambda **_kw: SimpleNamespace(
                challenge=b"\x01\x02"
            )
        )

    async def _store(**_kw):
        return "ch-auth"

    with (
        patch("app.api.v1.auth.get_webauthn_manager", _mgr),
        patch("app.core.challenge_storage.store_challenge", _store),
        patch(
            "app.api.v1.auth.options_to_json_dict",
            lambda options: {"challenge": options.challenge.hex()},
        ),
    ):
        res = await start_webauthn_authentication(req, db_session)

    assert res.challenge_id == "ch-auth"
    assert res.options["challenge"] == "0102"


@pytest.mark.asyncio
async def test_auth_start_no_credentials_400(db_session):
    email = f"authstart-nocreds-{uuid.uuid4().hex}@test.com"
    user = User(email=email, is_active=True, is_email_verified=True)
    db_session.add(user)
    await db_session.commit()

    req = WebAuthnAuthenticateStartRequest(email=email)
    with pytest.raises(HTTPException) as ei:
        await start_webauthn_authentication(req, db_session)
    assert ei.value.status_code == 400


@pytest.mark.asyncio
async def test_auth_start_store_challenge_failure_returns_500(db_session):
    email = f"authstart-fail-{uuid.uuid4().hex}@test.com"
    user = User(email=email, is_active=True, is_email_verified=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    cred = WebAuthnCredential(
        user_id=user.id, credential_id=b"\xaa\xcc", public_key=b"\x01\x02", sign_count=0
    )
    db_session.add(cred)
    await db_session.commit()

    req = WebAuthnAuthenticateStartRequest(email=email)

    def _mgr():
        return SimpleNamespace(
            generate_authentication_options=lambda **_kw: SimpleNamespace(
                challenge=b"\x09"
            )
        )

    async def _raise(**_kw):
        raise RuntimeError("redis down")

    with (
        patch("app.api.v1.auth.get_webauthn_manager", _mgr),
        patch("app.core.challenge_storage.store_challenge", _raise),
        patch(
            "app.api.v1.auth.options_to_json_dict",
            lambda options: {"challenge": options.challenge.hex()},
        ),
    ):
        with pytest.raises(HTTPException) as ei:
            await start_webauthn_authentication(req, db_session)
    assert ei.value.status_code == 500
