import importlib

import pytest


@pytest.mark.asyncio
async def test_lifespan_logs_redis_success(monkeypatch):
    import app.db.database as database
    import app.main as main
    import app.observability.logging as obs_logging

    # Disable optional subsystems
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    monkeypatch.setenv("ENABLE_CLEANUP_JOB", "false")

    # Stub out DB and Redis calls
    async def ok(*_, **__):
        return None

    monkeypatch.setattr(database, "init_db", ok, raising=True)
    # Patch dynamic import targets used inside lifespan
    import app.core.redis_client as rc

    monkeypatch.setattr(rc, "get_redis", ok, raising=True)
    monkeypatch.setattr(rc, "close_redis", ok, raising=True)
    monkeypatch.setattr(database, "close_db", ok, raising=True)
    monkeypatch.setenv("REDIS_URL", "redis://example:6379/0")

    # Capture logs via get_logger used at import time
    logs = {"info": [], "error": []}

    class _Logger:
        def info(self, msg, *_args, **kwargs):
            logs["info"].append((msg, kwargs))

        def error(self, msg, *_args, **kwargs):
            logs["error"].append((msg, kwargs))

    monkeypatch.setattr(obs_logging, "get_logger", lambda: _Logger(), raising=True)

    importlib.reload(main)
    async with main.lifespan(main.app):
        pass

    assert any(
        msg.startswith("Redis connection established") for msg, _ in logs["info"]
    )


@pytest.mark.asyncio
async def test_lifespan_logs_redis_failure(monkeypatch):
    import app.db.database as database
    import app.main as main
    import app.observability.logging as obs_logging

    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    monkeypatch.setenv("ENABLE_CLEANUP_JOB", "false")

    async def ok(*_, **__):
        return None

    async def boom(*_, **__):
        raise RuntimeError("boom")

    monkeypatch.setattr(database, "init_db", ok, raising=True)
    import app.core.redis_client as rc

    monkeypatch.setattr(rc, "get_redis", boom, raising=True)
    monkeypatch.setattr(rc, "close_redis", ok, raising=True)
    monkeypatch.setattr(database, "close_db", ok, raising=True)

    logs = {"info": [], "error": []}

    class _Logger:
        def info(self, msg, *_args, **kwargs):
            logs["info"].append((msg, kwargs))

        def error(self, msg, *_args, **kwargs):
            logs["error"].append((msg, kwargs))

    monkeypatch.setattr(obs_logging, "get_logger", lambda: _Logger(), raising=True)

    importlib.reload(main)
    async with main.lifespan(main.app):
        pass

    assert any(
        msg.startswith("Failed to connect to Redis:") for msg, _ in logs["error"]
    )


@pytest.mark.asyncio
async def test_lifespan_logs_db_init_failure(monkeypatch):
    import app.core.redis_client as rc
    import app.db.database as database
    import app.main as main
    import app.observability.logging as obs_logging

    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    monkeypatch.setenv("ENABLE_CLEANUP_JOB", "false")

    async def boom(*_, **__):
        raise RuntimeError("db-down")

    async def ok(*_, **__):
        return None

    monkeypatch.setattr(database, "init_db", boom, raising=True)
    monkeypatch.setattr(rc, "get_redis", ok, raising=True)
    monkeypatch.setattr(database, "close_db", ok, raising=True)
    monkeypatch.setattr(rc, "close_redis", ok, raising=True)

    logs = {"info": [], "error": []}

    class _Logger:
        def info(self, msg, *_args, **kwargs):
            logs["info"].append((msg, kwargs))

        def error(self, msg, *_args, **kwargs):
            logs["error"].append((msg, kwargs))

    monkeypatch.setattr(obs_logging, "get_logger", lambda: _Logger(), raising=True)

    importlib.reload(main)
    async with main.lifespan(main.app):
        pass

    assert any(
        msg.startswith("Failed to initialize database:") for msg, _ in logs["error"]
    )


@pytest.mark.asyncio
async def test_lifespan_schedules_cleanup_when_enabled(monkeypatch):
    import asyncio

    import app.core.cleanup as cleanup
    import app.db.database as database
    import app.main as main
    import app.observability.logging as obs_logging

    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    monkeypatch.setenv("ENABLE_CLEANUP_JOB", "true")

    async def ok(*_, **__):
        return None

    monkeypatch.setattr(database, "init_db", ok, raising=True)
    monkeypatch.setattr(database, "close_db", ok, raising=True)

    # Avoid running real looped task; prevent coroutine warnings
    def noop(*_, **__):
        return None

    monkeypatch.setattr(cleanup, "schedule_cleanup_job", noop, raising=True)

    scheduled = {"called": False}

    def fake_create_task(coro):
        scheduled["called"] = True
        # Immediately close coroutine-like to avoid 'never awaited' warnings
        try:
            close = getattr(coro, "close", None)
            if callable(close):
                close()
        except Exception:
            pass

        class _T:
            def cancel(self): ...

        return _T()

    logs = {"info": [], "error": []}

    class _Logger:
        def info(self, msg, *_args, **kwargs):
            logs["info"].append((msg, kwargs))

        def error(self, msg, *_args, **kwargs):
            logs["error"].append((msg, kwargs))

    monkeypatch.setattr(obs_logging, "get_logger", lambda: _Logger(), raising=True)

    importlib.reload(main)
    # Temporarily patch asyncio.create_task with a no-op that closes the coroutine
    monkeypatch.setattr(asyncio, "create_task", fake_create_task, raising=True)
    async with main.lifespan(main.app):
        pass

    assert scheduled["called"] is True
    assert any(
        msg.startswith("Background cleanup job scheduled") for msg, _ in logs["info"]
    )


@pytest.mark.asyncio
async def test_lifespan_shutdown_logs_error(monkeypatch):
    import app.core.redis_client as rc
    import app.db.database as database
    import app.main as main
    import app.observability.logging as obs_logging

    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    monkeypatch.setenv("ENABLE_CLEANUP_JOB", "false")

    async def ok(*_, **__):
        return None

    async def boom(*_, **__):
        raise RuntimeError("shutdown-fail")

    monkeypatch.setattr(main, "init_db", ok, raising=True)
    monkeypatch.setattr(rc, "get_redis", ok, raising=True)
    monkeypatch.setattr(database, "close_db", boom, raising=True)
    monkeypatch.setattr(rc, "close_redis", ok, raising=True)

    logs = {"info": [], "error": []}

    class _Logger:
        def info(self, msg, *_args, **kwargs):
            logs["info"].append((msg, kwargs))

        def error(self, msg, *_args, **kwargs):
            logs["error"].append((msg, kwargs))

    monkeypatch.setattr(obs_logging, "get_logger", lambda: _Logger(), raising=True)

    importlib.reload(main)
    async with main.lifespan(main.app):
        pass

    assert any(
        msg.startswith("Error during shutdown cleanup:") for msg, _ in logs["error"]
    )
