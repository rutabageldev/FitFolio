#!/usr/bin/env python3
"""
Lightweight script to check if database has schema but no version tracking,
and stamp it if needed. This avoids OOM from loading Alembic models.
"""
import os
import sys
from pathlib import Path

import psycopg


def get_database_url():
    """Get database URL respecting Docker secrets."""
    use_docker_secrets = os.getenv("USE_DOCKER_SECRETS", "").lower() in (
        "true",
        "1",
        "yes",
    )

    if use_docker_secrets:
        sys.path.insert(0, "/app")
        from app.core.secrets import get_database_url as get_url
        return get_url()
    else:
        return os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://fitfolio_user:supersecret@db:5432/fitfolio",
        )


def get_head_revision():
    """Get the head revision from migration files without loading Alembic."""
    migrations_dir = Path("/app/migrations/versions")
    migration_files = sorted(migrations_dir.glob("*.py"), reverse=True)

    if not migration_files:
        return None

    # Extract revision from the latest migration file
    with open(migration_files[0]) as f:
        for line in f:
            if "Revision ID:" in line:
                return line.split(":")[1].strip()
    return None


def main():
    db_url = get_database_url()
    # Convert SQLAlchemy URL to psycopg format
    db_url = db_url.replace("postgresql+psycopg://", "postgresql://")

    head_revision = get_head_revision()

    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                # Check if alembic_version table exists
                cur.execute(
                    "SELECT EXISTS(SELECT FROM information_schema.tables "
                    "WHERE table_name='alembic_version')"
                )
                version_table_exists = cur.fetchone()[0]

                # Check if users table exists (indicates schema is present)
                cur.execute(
                    "SELECT EXISTS(SELECT FROM information_schema.tables "
                    "WHERE table_name='users')"
                )
                users_table_exists = cur.fetchone()[0]

                if users_table_exists and not version_table_exists and head_revision:
                    # Schema exists but no version tracking - stamp with SQL
                    print(f"Stamping database to {head_revision} using direct SQL...")
                    cur.execute(
                        "CREATE TABLE alembic_version ("
                        "version_num VARCHAR(32) NOT NULL, "
                        "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
                    )
                    cur.execute(
                        "INSERT INTO alembic_version (version_num) VALUES (%s)",
                        (head_revision,),
                    )
                    conn.commit()
                    print("Database stamped successfully via SQL")
                elif users_table_exists and version_table_exists:
                    cur.execute("SELECT version_num FROM alembic_version")
                    result = cur.fetchone()
                    version = result[0] if result else "empty"
                    print(f"Database already tracked at version: {version}")
                else:
                    print("Fresh database - ready for migrations")

    except Exception as e:
        print(f"Error during version check/stamp: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
