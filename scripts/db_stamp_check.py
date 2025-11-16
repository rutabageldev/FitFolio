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
    """Get the head revision by finding the migration with no children."""
    migrations_dir = Path("/app/migrations/versions")
    migration_files = list(migrations_dir.glob("*.py"))

    if not migration_files:
        print("[warn] No migration files found in /app/migrations/versions")
        return None

    # Build a map of revisions and what they revise
    revisions = {}
    revises = set()

    for migration_file in migration_files:
        with open(migration_file) as f:
            content = f.read()
            current_revision = None
            current_down_rev = None

            # Extract both revision and down_revision from this file
            for line in content.split("\n"):
                line_stripped = line.strip()
                if line_stripped.startswith("revision") and "=" in line:
                    # Parse: revision = "abc123" or revision: str = "abc123"
                    current_revision = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line_stripped.startswith("down_revision") and "=" in line:
                    # Parse: down_revision = "xyz789" or None
                    down_rev_part = line.split("=", 1)[1].strip()
                    if "None" not in down_rev_part and down_rev_part not in ("None", ""):
                        current_down_rev = down_rev_part.strip().strip('"').strip("'")

            if current_revision:
                revisions[migration_file.name] = current_revision
                if current_down_rev:
                    revises.add(current_down_rev)

    print(f"[dbg] Found {len(revisions)} migrations: {list(revisions.values())}")
    print(f"[dbg] Revisions that are parents: {list(revises)}")

    # Head is the revision that no other migration revises
    for revision in revisions.values():
        if revision not in revises:
            print(f"[dbg] Head revision (not revised by others): {revision}")
            return revision

    print("[warn] Could not determine head revision")
    return None


def main():
    db_url = get_database_url()
    # Convert SQLAlchemy URL to psycopg format
    db_url = db_url.replace("postgresql+psycopg://", "postgresql://")

    # Log masked URL for debugging (hide password)
    masked_url = db_url
    if "@" in db_url:
        # Mask password: postgres://user:XXXXX@host/db
        parts = db_url.split("@")
        user_pass = parts[0].split("://")[1]
        if ":" in user_pass:
            user = user_pass.split(":")[0]
            masked_url = f"postgresql://{user}:****@{parts[1]}"
    print(f"Database URL resolved: {masked_url}")

    head_revision = get_head_revision()
    print(f"Head revision determined: {head_revision}")

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
                    current_version = result[0] if result else None

                    if current_version != head_revision:
                        print(
                            f"Database at wrong version: {current_version}, "
                            f"expected: {head_revision}"
                        )
                        print(f"Re-stamping to {head_revision}...")
                        cur.execute(
                            "UPDATE alembic_version SET version_num = %s",
                            (head_revision,),
                        )
                        conn.commit()
                        print("Database re-stamped successfully via SQL")
                    else:
                        print(f"Database already at correct version: {current_version}")
                else:
                    print("Fresh database - ready for migrations")

    except Exception as e:
        print(f"Error during version check/stamp: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
