"""Unit tests for RateLimiter.get_identifier user strategies."""

from types import SimpleNamespace

import pytest

from app.core.rate_limiter import RateLimiter

pytestmark = [pytest.mark.security, pytest.mark.unit]


class DummyRequest:
    def __init__(self, xff: str | None, host: str | None, user_id: str | None):
        self.headers = {}
        if xff is not None:
            self.headers["X-Forwarded-For"] = xff
        # Client info
        self.client = SimpleNamespace(host=host) if host else None
        # Request state for user_id
        self.state = (
            SimpleNamespace(user_id=user_id)
            if user_id is not None
            else SimpleNamespace()
        )


def test_user_strategy_uses_request_state_user_id():
    req = DummyRequest(xff=None, host="10.0.0.1", user_id="user-123")
    # RateLimiter instance not used here; only method behavior is tested
    limiter = RateLimiter.__new__(RateLimiter)
    ident = limiter.get_identifier(req, strategy="user")
    assert ident == "user:user-123"


def test_user_strategy_without_user_id_raises():
    req = DummyRequest(xff=None, host="10.0.0.1", user_id=None)
    limiter = RateLimiter.__new__(RateLimiter)
    with pytest.raises(ValueError):
        limiter.get_identifier(req, strategy="user")


def test_ip_or_user_prefers_user_when_present():
    req = DummyRequest(xff="203.0.113.9, 70.0.0.1", host="10.0.0.1", user_id="abc")
    limiter = RateLimiter.__new__(RateLimiter)
    ident = limiter.get_identifier(req, strategy="ip_or_user")
    assert ident == "user:abc"
