import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Get database URL from environment
_env_test = os.getenv("TEST_DATABASE_URL")

if _env_test is not None:
    # Test mode: use TEST_DATABASE_URL directly
    DATABASE_URL: str = _env_test
else:
    # Production/Development mode: try Docker secrets first, then env vars
    use_docker_secrets = os.getenv("USE_DOCKER_SECRETS", "").lower() in (
        "true",
        "1",
        "yes",
    )

    if use_docker_secrets:
        # Import secrets module only when needed
        from app.core.secrets import get_database_url

        DATABASE_URL = get_database_url()
    else:
        # Fall back to DATABASE_URL environment variable
        DATABASE_URL = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://fitfolio_user:supersecret@db:5432/fitfolio",
        )

# Convert to async URL if needed
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("sqlite://"):
    # Ensure async driver for SQLite when used under tests
    # e.g., sqlite:// -> sqlite+aiosqlite://
    if not DATABASE_URL.startswith("sqlite+aiosqlite://"):
        DATABASE_URL = DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://", 1)

# Create async engine
_base_engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    pool_pre_ping=True,
    pool_recycle=300,
)


class _EngineWrapper:
    """Lightweight wrapper to allow test monkeypatching of dispose()."""

    def __init__(self, inner):
        self._inner = inner

    async def dispose(self):
        await self._inner.dispose()

    def begin(self):
        return self._inner.begin()

    def __getattr__(self, name):
        return getattr(self._inner, name)


# Public engine reference used by init/close code and tests
engine = _EngineWrapper(_base_engine)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    _base_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    from .base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections."""
    await engine.dispose()
