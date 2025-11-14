import uuid
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from app.api.v1.auth import MagicLinkVerifyRequest, verify_magic_link

pytestmark = [pytest.mark.security, pytest.mark.integration]


def make_request(headers: dict[str, str] | None = None) -> Request:
    raw_headers = []
    for k, v in (headers or {}).items():
        raw_headers.append((k.lower().encode("latin-1"), v.encode("latin-1")))
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/magic-link/verify",
        "headers": raw_headers,
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_invalid_token_returns_429_when_any_lockout_key_exists(db_session):
    http_req = make_request({"User-Agent": "ua-test"})
    response = Response()
    request_model = MagicLinkVerifyRequest(token=f"bad-{uuid.uuid4().hex}")

    class _FakeRedis:
        async def keys(self, _pattern):
            return ["lockout:123"]

    async def _fake_get_redis():
        return _FakeRedis()

    with patch("app.api.v1.auth.get_redis", _fake_get_redis):
        with pytest.raises(HTTPException) as ei:
            await verify_magic_link(request_model, response, http_req, db_session)
    assert ei.value.status_code == 429


@pytest.mark.asyncio
async def test_invalid_token_redis_error_fallback_returns_400(db_session):
    http_req = make_request({"User-Agent": "ua-test"})
    response = Response()
    request_model = MagicLinkVerifyRequest(token=f"bad-{uuid.uuid4().hex}")

    async def _raise():
        raise RuntimeError("redis down")

    with patch("app.api.v1.auth.get_redis", _raise):
        with pytest.raises(HTTPException) as ei:
            await verify_magic_link(request_model, response, http_req, db_session)
    assert ei.value.status_code == 400
