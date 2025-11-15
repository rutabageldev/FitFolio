from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path
from typing import Any, cast

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.db.base import Base

BASE_DIR = Path(__file__).resolve().parents[1]  # .../backend
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

# ruff: noqa: E402
from app.db import models  # noqa: F401  <-- important: loads submodules via __init__.py

# Alembic Config
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# Construct DATABASE_URL using the same logic as the app
def get_alembic_database_url() -> str:
    """Get database URL for migrations, respecting Docker secrets."""
    import os

    use_docker_secrets = os.getenv("USE_DOCKER_SECRETS", "").lower() in (
        "true",
        "1",
        "yes",
    )

    if use_docker_secrets:
        from app.core.secrets import get_database_url

        return get_database_url()
    else:
        return os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://fitfolio_user:supersecret@db:5432/fitfolio",
        )


config.set_main_option("sqlalchemy.url", get_alembic_database_url())

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section)
    if section is None:
        raise RuntimeError("Alembic config section missing")
    connectable = engine_from_config(
        cast(dict[str, Any], section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
