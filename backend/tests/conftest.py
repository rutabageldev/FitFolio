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
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
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

# Test database URL (in-memory SQLite for speed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def anyio_backend():
    """Use asyncio backend for pytest-asyncio."""
    return "asyncio"


@pytest_asyncio.fixture
async def db_engine():
    """Create test database engine with SQLite compatibility.

    Note: Removes PostgreSQL-specific server defaults since SQLite doesn't
    support functions like now() or true in DEFAULT clauses. Tests handle
    object creation explicitly so server defaults aren't needed.
    """
    import json
    import uuid

    from sqlalchemy import DateTime, LargeBinary, TypeDecorator
    from sqlalchemy import String as SQLAString
    from sqlalchemy.dialects.postgresql import BYTEA, INET, JSONB, TIMESTAMP, UUID

    # Create type decorators for proper value conversion
    class UUIDAsString(TypeDecorator):
        """Convert UUID to string for SQLite."""

        impl = SQLAString
        cache_ok = True

        def process_bind_param(self, value, _dialect):
            if value is not None:
                return str(value)
            return value

        def process_result_value(self, value, _dialect):
            if value is not None:
                # Handle both string and UUID inputs (PostgreSQL returns UUID objects)
                if isinstance(value, uuid.UUID):
                    return value
                return uuid.UUID(value)
            return value

    class JSONBAsString(TypeDecorator):
        """Convert JSON to string for SQLite."""

        impl = SQLAString
        cache_ok = True

        def process_bind_param(self, value, _dialect):
            if value is not None:
                return json.dumps(value)
            return value

        def process_result_value(self, value, _dialect):
            if value is not None:
                return json.loads(value)
            return value

    class TZAwareDateTime(TypeDecorator):
        """Store timezone-aware datetimes in SQLite with automatic UTC timezone."""

        impl = DateTime
        cache_ok = True

        def process_bind_param(self, value, _dialect):
            # Store as UTC timestamp (remove timezone for SQLite)
            if value is not None:
                if hasattr(value, "tzinfo") and value.tzinfo is not None:
                    # SQLite doesn't support timezones, store as naive UTC
                    return value.replace(tzinfo=None)
            return value

        def process_result_value(self, value, _dialect):
            # Read back as UTC-aware (SQLite returns naive datetimes)
            if value is not None:
                from datetime import UTC
                from datetime import datetime as dt

                # Always treat naive datetimes from SQLite as UTC
                if isinstance(value, dt):
                    if value.tzinfo is None:
                        # Naive datetime from SQLite - make it UTC-aware
                        return value.replace(tzinfo=UTC)
                    else:
                        # Already has timezone (shouldn't happen with SQLite)
                        return value
            return value

    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Save original column types so we can restore them after tests complete
    original_types = {}
    original_defaults = {}

    def setup_sqlite_types():
        """Replace PostgreSQL types with SQLite-compatible ones.

        IMPORTANT: This modifies column types IN-PLACE on Base.metadata, which is
        shared globally. We save the original types to restore after testing.
        """
        from sqlalchemy import BigInteger, Integer

        # Save and replace types for all tables
        for table in Base.metadata.tables.values():
            for column in table.columns:
                key = (table.name, column.name)

                # Save originals (only once)
                if key not in original_types:
                    original_types[key] = column.type
                    original_defaults[key] = column.server_default

                # Clear server defaults (SQLite doesn't support now(), true, etc.)
                column.server_default = None

                # Replace PostgreSQL-specific types with SQLite-compatible ones
                if isinstance(original_types[key], UUID):
                    column.type = UUIDAsString(36)
                elif isinstance(original_types[key], BYTEA):
                    column.type = LargeBinary()
                elif isinstance(original_types[key], INET):
                    column.type = SQLAString(45)
                elif isinstance(original_types[key], JSONB):
                    column.type = JSONBAsString()
                elif isinstance(original_types[key], TIMESTAMP):
                    column.type = TZAwareDateTime()
                elif isinstance(original_types[key], BigInteger):
                    column.type = Integer()

    def restore_original_types():
        """Restore original PostgreSQL types after tests complete."""
        for table in Base.metadata.tables.values():
            for column in table.columns:
                key = (table.name, column.name)
                if key in original_types:
                    column.type = original_types[key]
                    column.server_default = original_defaults[key]

    # Setup SQLite-compatible types
    setup_sqlite_types()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

    # Restore original types for production use
    restore_original_types()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
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

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


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
