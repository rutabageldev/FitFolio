import asyncio

import pytest

from app.core import cleanup as cleanup_mod


class _DummySessionCtx:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_run_cleanup_job_happy_path(monkeypatch):
    async def fake_cleanup_sessions(_db):
        return 3

    async def fake_cleanup_tokens(_db):
        return 2

    # Provide a dummy AsyncSessionLocal context manager
    monkeypatch.setattr(
        cleanup_mod, "AsyncSessionLocal", _DummySessionCtx, raising=True
    )
    monkeypatch.setattr(
        cleanup_mod, "cleanup_expired_sessions", fake_cleanup_sessions, raising=True
    )
    monkeypatch.setattr(
        cleanup_mod,
        "cleanup_expired_magic_links",
        fake_cleanup_tokens,
        raising=True,
    )

    # Should complete without raising
    await cleanup_mod.run_cleanup_job()


@pytest.mark.asyncio
async def test_run_cleanup_job_error_path_re_raises(monkeypatch):
    async def failing_cleanup_sessions(_db):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        cleanup_mod, "AsyncSessionLocal", _DummySessionCtx, raising=True
    )
    monkeypatch.setattr(
        cleanup_mod, "cleanup_expired_sessions", failing_cleanup_sessions, raising=True
    )

    with pytest.raises(RuntimeError):
        await cleanup_mod.run_cleanup_job()


@pytest.mark.asyncio
async def test_schedule_cleanup_job_calls_run_once(monkeypatch):
    called = {"run": 0}

    async def fake_run():
        called["run"] += 1

    async def fake_sleep(_seconds):
        # Cancel after first iteration to stop the infinite loop
        raise asyncio.CancelledError()

    monkeypatch.setattr(cleanup_mod, "run_cleanup_job", fake_run, raising=True)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep, raising=True)

    with pytest.raises(asyncio.CancelledError):
        await cleanup_mod.schedule_cleanup_job(interval_hours=0)

    assert called["run"] == 1


@pytest.mark.asyncio
async def test_schedule_cleanup_job_logs_error_and_continues(monkeypatch):
    async def failing_run():
        raise RuntimeError("boom")

    async def fake_sleep(_seconds):
        # If we reached sleep, it means the loop continued after error
        raise asyncio.CancelledError()

    monkeypatch.setattr(cleanup_mod, "run_cleanup_job", failing_run, raising=True)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep, raising=True)

    with pytest.raises(asyncio.CancelledError):
        await cleanup_mod.schedule_cleanup_job(interval_hours=0)
