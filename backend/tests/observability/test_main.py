import importlib

import pytest


@pytest.mark.asyncio
async def test_configure_logging_called_on_import(monkeypatch):
    # Avoid side effects during import
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    monkeypatch.setenv("ENABLE_CLEANUP_JOB", "false")

    import app.main as main
    import app.observability.logging as obs_logging

    called = {"count": 0}

    def fake_configure_logging():
        called["count"] += 1

    # Patch source of the imported symbol before reload
    monkeypatch.setattr(
        obs_logging, "configure_logging", fake_configure_logging, raising=True
    )
    importlib.reload(main)

    assert called["count"] == 1


@pytest.mark.asyncio
async def test_lifespan_logs_otel_setup_error(monkeypatch):
    import app.main as main
    import app.observability.logging as obs_logging
    import app.observability.otel as otel_mod

    # Ensure OTEL not disabled
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
    monkeypatch.setenv("ENABLE_CLEANUP_JOB", "false")

    async def ok(*_, **__):
        return None

    # Avoid DB/Redis interactions
    monkeypatch.setattr(main, "init_db", ok, raising=True)
    import app.core.redis_client as rc
    import app.db.database as database

    monkeypatch.setattr(rc, "get_redis", ok, raising=True)
    monkeypatch.setattr(database, "close_db", ok, raising=True)
    monkeypatch.setattr(rc, "close_redis", ok, raising=True)

    # Force setup_otel to raise from source module imported by main
    def boom(*_, **__):
        raise RuntimeError("otel-fail")

    monkeypatch.setattr(otel_mod, "setup_otel", boom, raising=True)

    logs = {"error": []}

    class _Logger:
        def info(self, msg, *args, **kwargs):
            pass

        def error(self, msg, *_args, **kwargs):
            logs["error"].append((msg, kwargs))

    monkeypatch.setattr(obs_logging, "get_logger", lambda: _Logger(), raising=True)

    importlib.reload(main)
    async with main.lifespan(main.app):
        pass

    assert any(
        msg.startswith("Failed to initialize OpenTelemetry:")
        for msg, _ in logs["error"]
    )
