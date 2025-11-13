"""Tests for RequestID middleware behavior."""

import re

import pytest
from httpx import AsyncClient

# Focus on security/integration behavior
pytestmark = [pytest.mark.security, pytest.mark.integration]


@pytest.mark.asyncio
async def test_generates_request_id_when_missing(client: AsyncClient):
    r = await client.get("/healthz")
    assert r.status_code == 200
    rid = r.headers.get("x-request-id")
    assert rid is not None and len(rid) > 0
    # Basic URL-safe token/uuid pattern
    assert re.match(r"^[A-Za-z0-9\-_]+$", rid) is not None


@pytest.mark.asyncio
async def test_echoes_incoming_request_id_header(client: AsyncClient):
    custom = "abc123-custom-id"
    r = await client.get("/healthz", headers={"x-request-id": custom})
    assert r.status_code == 200
    assert r.headers.get("x-request-id") == custom


@pytest.mark.asyncio
async def test_clears_context_after_request(monkeypatch, client: AsyncClient):
    # Patch clear_ctx to set a flag when called
    called = {"cleared": False}

    def fake_clear():
        called["cleared"] = True

    monkeypatch.setattr("app.observability.logging.clear_ctx", fake_clear)
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert called["cleared"] is True
