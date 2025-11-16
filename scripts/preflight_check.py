#!/usr/bin/env python3
"""
Preflight checks for deployment migrations.
Verifies database connectivity, secret reading, and import paths.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, "/app")


def main():
    """Run preflight checks."""
    print("=== Preflight: Environment Variables ===")
    print(f"[dbg] USE_DOCKER_SECRETS: {os.getenv('USE_DOCKER_SECRETS')}")
    for k in ("POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER"):
        print(f"[dbg] {k}= {os.getenv(k)}")

    print("\n=== Preflight: Database URL Construction ===")
    try:
        from app.core.secrets import get_database_url

        url = get_database_url()
        # Mask password in URL
        if "@" in url:
            parts = url.split("@")
            user_pass = parts[0].split("://")[1]
            if ":" in user_pass:
                user = user_pass.split(":")[0]
                masked_url = f"postgresql://{user}:****@{parts[1]}"
            else:
                masked_url = url
        else:
            masked_url = url
        print(f"[dbg] DB URL (masked): {masked_url}")
    except Exception as e:
        print(f"[err] get_database_url failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(2)

    print("\n=== Preflight: Database Connectivity ===")
    try:
        import psycopg

        test_url = url.replace("postgresql+psycopg://", "postgresql://", 1)
        with psycopg.connect(test_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                print("[dbg] DB connectivity OK")
    except Exception as e:
        print(f"[err] psycopg connect failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(3)

    print("\n=== Preflight: App Imports ===")
    try:
        from app.db.base import Base

        print("[dbg] app imports OK")
    except Exception as e:
        print(f"[err] app import failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(4)

    print("\n=== Preflight: All checks passed ===")


if __name__ == "__main__":
    main()
