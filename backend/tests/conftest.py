"""Shared test fixtures for backend tests.

Only contains truly shared fixtures that all tests need.
Test-specific fixtures should be in their respective test files.
"""

import os
import subprocess
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base

# Ensure OTEL is disabled before importing app unless explicitly enabled
if os.getenv("TEST_OTEL", "").lower() not in {"1", "true", "yes"}:
    os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from app.main import app

# Disable rate limiting for most tests (rate limiting tests will override)
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")


# Use separate Redis database for tests to avoid conflicts with dev data
# In WSL2/devcontainer environments, localhost may not work for Docker containers
# Try to get Redis container IP dynamically, fall back to localhost
def get_redis_url() -> str:
    """Get Redis URL for tests, handling WSL2/Docker networking."""
    try:
        # Try to get Redis container IP (works in WSL2/devcontainer)
        result = subprocess.run(
            [
                "docker",
                "inspect",
                "fitfolio-redis",
                "--format={{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
            ],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0 and result.stdout.strip():
            container_ip = result.stdout.strip()
            return f"redis://{container_ip}:6379/1"
    except Exception:
        pass
    # Fallback to localhost (works in most environments)
    return "redis://localhost:6379/1"


os.environ.setdefault("REDIS_URL", get_redis_url())

# Test database URL (Postgres strongly recommended for representative testing)
# Defaults to the dev Postgres instance's test DB.
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://fitfolio_user:supersecret@db:5432/fitfolio_test",
)


@pytest.fixture(scope="session")
def anyio_backend():
    """Use asyncio backend for pytest-asyncio."""
    return "asyncio"


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """Create test database engine (Postgres)."""

    if not TEST_DATABASE_URL.startswith("postgresql"):
        raise RuntimeError(
            "TEST_DATABASE_URL must point to Postgres for representative testing. "
            "Set TEST_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/fitfolio_test"
        )

    engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)

    # Ensure tables exist in public schema
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables at the end of the session to keep DB tidy
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    # Ensure a clean database state before each test
    async with db_engine.begin() as conn:
        # Use ordered deletes to avoid taking AccessExclusiveLock from TRUNCATE,
        # which can deadlock with concurrent transactions.
        for table in (
            "login_events",
            "magic_link_tokens",
            "webauthn_credentials",
            "sessions",
            "users",
        ):
            await conn.execute(text(f"DELETE FROM {table}"))

    async_session_factory = sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_factory() as session:  # type: ignore[attr-defined]
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with database override."""

    async def override_get_db():
        yield db_session

    from app.db.database import get_db

    app.dependency_overrides[get_db] = override_get_db

    class TestAsyncClient(AsyncClient):
        async def request(self, method, url, **kwargs):
            # Avoid httpx per-request cookies deprecation by moving them to the jar
            cookies = kwargs.pop("cookies", None)
            if cookies:
                self.cookies.update(cookies)
            return await super().request(method, url, **kwargs)

    async with TestAsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def csrf_token(client: AsyncClient) -> str:
    """Fetch CSRF token cookie via health endpoint."""
    response = await client.get("/healthz")
    return response.cookies["csrf_token"]


@pytest_asyncio.fixture(scope="function", autouse=True)
async def cleanup_redis():
    """Flush Redis database before each test to prevent state leakage."""
    from app.core.redis_client import get_redis

    # Flush Redis before test to start clean
    try:
        redis = await get_redis()
        await redis.flushdb()  # Clear all keys in current database (db=1 for tests)
    except Exception:
        pass  # Ignore if Redis is not available

    yield
    # No cleanup after - let Redis connection persist across tests for performance


@pytest.fixture(scope="session", autouse=True)
def disable_otel():
    """Disable OpenTelemetry SDK during tests to avoid noisy teardown logging."""
    # Allow opt-in tracing in tests via TEST_OTEL=1/true, otherwise disable SDK.
    test_otel = os.getenv("TEST_OTEL", "").lower() in {"1", "true", "yes"}
    if not test_otel:
        os.environ.setdefault("OTEL_SDK_DISABLED", "true")
        yield
        return
    # If tracing is enabled for tests, ensure we cleanly shut down
    # the provider to avoid warnings.
    try:
        yield
    finally:
        try:
            from opentelemetry import trace

            provider = trace.get_tracer_provider()
            shutdown = getattr(provider, "shutdown", None)
            if callable(shutdown):
                shutdown()
        except Exception:
            # Never let tracing teardown break tests
            pass


@pytest.fixture(scope="session", autouse=True)
def close_redis_session():
    """Ensure Redis connection is closed at the end of the test session."""
    import asyncio

    from app.core.redis_client import close_redis

    yield
    try:
        asyncio.run(close_redis())
    except Exception:
        pass
