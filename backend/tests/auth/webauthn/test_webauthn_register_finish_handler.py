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
