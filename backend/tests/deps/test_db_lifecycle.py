"""Tests for database lifecycle utilities in app.db.database."""

import importlib
import os

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_get_db_yields_async_session():
    from app.db.database import get_db

    gen = get_db()
    session = await gen.__anext__()
    try:
        assert isinstance(session, AsyncSession)
    finally:
        # Close generator to trigger session.close()
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()


@pytest.mark.asyncio
async def test_get_db_closes_on_normal_exit(monkeypatch):
    from app.db.database import get_db

    gen = get_db()
    session = await gen.__anext__()
    closed = {"called": False}

    async def fake_close():
        closed["called"] = True

    monkeypatch.setattr(session, "close", fake_close, raising=False)
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()
    assert closed["called"] is True


@pytest.mark.asyncio
async def test_get_db_closes_on_exception(monkeypatch):
    from app.db.database import get_db

    gen = get_db()
    session = await gen.__anext__()
    closed = {"called": False}

    async def fake_close():
        closed["called"] = True

    monkeypatch.setattr(session, "close", fake_close, raising=False)
    with pytest.raises(RuntimeError):
        await gen.athrow(RuntimeError("boom"))
    assert closed["called"] is True


@pytest.mark.asyncio
async def test_init_db_calls_create_all(monkeypatch):
    import app.db.database as database

    class FakeConn:
        def __init__(self):
            self.called = False

        async def run_sync(self, _fn):
            # Expect Base.metadata.create_all
            self.called = True

    class FakeBeginCtx:
        async def __aenter__(self):
            return fake_conn

        async def __aexit__(self, exc_type, exc, tb):
            return False

    fake_conn = FakeConn()

    # Replace engine.begin with a method returning FakeBeginCtx
    class _Engine:
        def begin(self):
            return FakeBeginCtx()

    monkeypatch.setattr(database, "engine", _Engine(), raising=False)
    await database.init_db()
    assert fake_conn.called is True


@pytest.mark.asyncio
async def test_close_db_disposes_engine(monkeypatch):
    import app.db.database as database

    called = {"dispose": False}

    async def fake_dispose():
        called["dispose"] = True

    monkeypatch.setattr(database.engine, "dispose", fake_dispose, raising=False)
    await database.close_db()
    assert called["dispose"] is True


@pytest.mark.asyncio
async def test_database_url_conversion(monkeypatch):
    # Save original env and module
    import app.db.database as database

    original_url = os.getenv("DATABASE_URL")
    try:
        monkeypatch.setenv(
            "DATABASE_URL", "postgresql://user:pass@localhost:5432/dbname"
        )
        importlib.reload(database)
        assert database.DATABASE_URL.startswith("postgresql+psycopg://")
    finally:
        if original_url is not None:
            monkeypatch.setenv("DATABASE_URL", original_url)
        else:
            monkeypatch.delenv("DATABASE_URL", raising=False)
        importlib.reload(database)
