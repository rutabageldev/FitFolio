"""Shared test fixtures for backend tests.

Only contains truly shared fixtures that all tests need.
Test-specific fixtures should be in their respective test files.
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.main import app

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
        """Store timezone-aware datetimes in SQLite."""

        impl = DateTime
        cache_ok = True

        def process_bind_param(self, value, _dialect):
            # Store as UTC timestamp
            if value is not None and value.tzinfo is not None:
                return value.replace(tzinfo=None)
            return value

        def process_result_value(self, value, _dialect):
            # Read back as UTC-aware
            if value is not None:
                from datetime import UTC

                return value.replace(tzinfo=UTC)
            return value

    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    def create_tables_without_pg_defaults(_target, _connection, **_kw):
        """Create tables with server_default removed for SQLite compatibility."""
        from sqlalchemy import BigInteger, Integer

        # Remove PostgreSQL-specific server defaults and replace types
        for table in Base.metadata.tables.values():
            for column in table.columns:
                # Clear server defaults (SQLite doesn't support now(), true, etc.)
                if column.server_default is not None:
                    column.server_default = None

                # Replace PostgreSQL-specific types with SQLite-compatible ones
                if isinstance(column.type, UUID):
                    column.type = UUIDAsString(36)  # UUIDs as strings with conversion
                elif isinstance(column.type, BYTEA):
                    column.type = LargeBinary()  # Binary data
                elif isinstance(column.type, INET):
                    column.type = SQLAString(45)  # IP addresses as strings
                elif isinstance(column.type, JSONB):
                    column.type = JSONBAsString()  # JSON as text with conversion
                elif isinstance(column.type, TIMESTAMP):
                    column.type = TZAwareDateTime()  # DateTime with TZ awareness
                elif isinstance(column.type, BigInteger):
                    # SQLite uses INTEGER for autoincrement compatibility
                    column.type = Integer()  # Use regular Integer for SQLite

    # Listen for before_create event to strip server defaults
    from sqlalchemy import event

    event.listen(Base.metadata, "before_create", create_tables_without_pg_defaults)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

    # Clean up the event listener
    event.remove(Base.metadata, "before_create", create_tables_without_pg_defaults)


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
