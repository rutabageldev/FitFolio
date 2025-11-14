import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from app.api.v1.auth import (
    WebAuthnAuthenticateFinishRequest,
    finish_webauthn_authentication,
)
from app.db.models.auth import User

pytestmark = [pytest.mark.security, pytest.mark.integration]


def make_request() -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/webauthn/authenticate/finish",
        "headers": [],
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_auth_finish_missing_credential_id_returns_400(db_session):
    now = datetime.now(UTC)
    email = f"authfinish-{uuid.uuid4().hex}@test.com"
    user = User(
        email=email,
        is_active=True,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()

    req = WebAuthnAuthenticateFinishRequest(
        email=email,
        challenge_id="ch-id",
        credential={"type": "public-key"},  # no 'id'
    )
    http_req = make_request()
    resp = Response()

    async def _return_tuple(**_kw):
        return (email.lower(), "0102")

    with patch(
        "app.core.challenge_storage.retrieve_and_delete_challenge", _return_tuple
    ):
        with pytest.raises(HTTPException) as ei:
            await finish_webauthn_authentication(req, resp, http_req, db_session)
    assert ei.value.status_code == 400


@pytest.mark.asyncio
async def test_auth_finish_user_not_found_returns_404(db_session):
    email = f"authfinish-missing-{uuid.uuid4().hex}@test.com"
    req = WebAuthnAuthenticateFinishRequest(
        email=email,
        challenge_id="ch-id",
        credential={"id": "aabb", "type": "public-key"},
    )
    http_req = make_request()
    resp = Response()

    async def _return_tuple(**_kw):
        return (email.lower(), "0102")

    with patch(
        "app.core.challenge_storage.retrieve_and_delete_challenge", _return_tuple
    ):
        with pytest.raises(HTTPException) as ei:
            await finish_webauthn_authentication(req, resp, http_req, db_session)
    assert ei.value.status_code == 404


@pytest.mark.asyncio
async def test_auth_finish_challenge_email_mismatch_returns_400(db_session):
    now = datetime.now(UTC)
    email = f"authfinish-mismatch-{uuid.uuid4().hex}@test.com"
    user = User(
        email=email,
        is_active=True,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()

    req = WebAuthnAuthenticateFinishRequest(
        email=email,
        challenge_id="ch-id",
        credential={"id": "aabb", "type": "public-key"},
    )
    http_req = make_request()
    resp = Response()

    async def _return_tuple(**_kw):
        return ("different@example.com", "0102")

    with patch(
        "app.core.challenge_storage.retrieve_and_delete_challenge", _return_tuple
    ):
        with pytest.raises(HTTPException) as ei:
            await finish_webauthn_authentication(req, resp, http_req, db_session)
    assert ei.value.status_code == 400


@pytest.mark.asyncio
async def test_auth_finish_credential_not_found_returns_400(db_session):
    now = datetime.now(UTC)
    email = f"authfinish-nocred-{uuid.uuid4().hex}@test.com"
    user = User(
        email=email,
        is_active=True,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()

    req = WebAuthnAuthenticateFinishRequest(
        email=email,
        challenge_id="ch-id",
        credential={"id": "aabb", "type": "public-key"},
    )
    http_req = make_request()
    resp = Response()

    async def _return_tuple(**_kw):
        return (email.lower(), "0102")

    with patch(
        "app.core.challenge_storage.retrieve_and_delete_challenge", _return_tuple
    ):
        with pytest.raises(HTTPException) as ei:
            await finish_webauthn_authentication(req, resp, http_req, db_session)
    assert ei.value.status_code == 400


@pytest.mark.asyncio
async def test_auth_finish_verify_error_returns_400(db_session):
    from app.db.models.auth import WebAuthnCredential

    now = datetime.now(UTC)
    email = f"authfinish-verifyerr-{uuid.uuid4().hex}@test.com"
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

    # Seed a credential matching the incoming ID
    cred_id_hex = "aabb"
    credential = WebAuthnCredential(
        user_id=user.id,
        credential_id=bytes.fromhex(cred_id_hex),
        public_key=b"\x01\x02",
        sign_count=0,
        created_at=now,
        updated_at=now,
    )
    db_session.add(credential)
    await db_session.commit()

    req = WebAuthnAuthenticateFinishRequest(
        email=email,
        challenge_id="ch-id",
        credential={"id": cred_id_hex, "type": "public-key"},
    )
    http_req = make_request()
    resp = Response()

    async def _return_tuple(**_kw):
        return (email.lower(), "0102")

    class _FakeManager:
        rp_id = "localhost"
        origin = "http://localhost:5173"

        def verify_authentication_response(self, **_kw):
            raise ValueError("bad assertion")

    with patch(
        "app.core.challenge_storage.retrieve_and_delete_challenge", _return_tuple
    ):
        with patch("app.api.v1.auth.get_webauthn_manager", return_value=_FakeManager()):
            with pytest.raises(HTTPException) as ei:
                await finish_webauthn_authentication(req, resp, http_req, db_session)
    assert ei.value.status_code == 400


@pytest.mark.asyncio
async def test_auth_finish_success_creates_session_updates_sign_count_and_sets_cookie(
    db_session,
):
    from sqlalchemy import select

    from app.db.models.auth import Session, WebAuthnCredential

    now = datetime.now(UTC)
    email = f"authfinish-success-{uuid.uuid4().hex}@test.com"
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

    # Seed existing credential for the user
    cred_id_hex = "aabb"
    credential = WebAuthnCredential(
        user_id=user.id,
        credential_id=bytes.fromhex(cred_id_hex),
        public_key=b"\x01\x02",
        sign_count=5,
        created_at=now,
        updated_at=now,
    )
    db_session.add(credential)
    await db_session.commit()
    await db_session.refresh(credential)

    req = WebAuthnAuthenticateFinishRequest(
        email=email,
        challenge_id="ch-id",
        credential={"id": cred_id_hex, "type": "public-key"},
    )
    http_req = make_request()
    resp = Response()

    async def _return_tuple(**_kw):
        return (email.lower(), "0102")

    class _FakeManager:
        rp_id = "localhost"
        origin = "http://localhost:5173"

        def verify_authentication_response(self, **_kw):
            return {"new_sign_count": 6}

    with patch(
        "app.core.challenge_storage.retrieve_and_delete_challenge", _return_tuple
    ):
        with patch("app.api.v1.auth.get_webauthn_manager", return_value=_FakeManager()):
            result = await finish_webauthn_authentication(
                req, resp, http_req, db_session
            )

    # Session cookie set
    set_cookie = resp.headers.get("set-cookie", "")
    assert "ff_sess=" in set_cookie
    # Result message
    assert "successful" in result.message.lower()
    # Sign count updated
    await db_session.refresh(credential)
    assert credential.sign_count == 6
    # Session created
    stmt = select(Session).where(Session.user_id == user.id)
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
