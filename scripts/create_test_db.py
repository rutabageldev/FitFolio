import os
import sys

import psycopg


def main() -> int:
    host = os.getenv("PGHOST", "db")
    port = int(os.getenv("PGPORT", "5432"))
    user = os.getenv("PGUSER", "fitfolio_user")
    password = os.getenv("PGPASSWORD", "supersecret")
    dbname = os.getenv("TEST_DB", "fitfolio_test")

    try:
        with psycopg.connect(
            dbname="postgres", host=host, port=port, user=user, password=password
        ) as conn:
            conn.autocommit = True
            conn.execute("SET client_min_messages TO WARNING;")
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (dbname,))
                exists = cur.fetchone() is not None
                if not exists:
                    cur.execute(f'CREATE DATABASE "{dbname}"')
                    print(f"Created database '{dbname}'.")
                else:
                    print(f"Database '{dbname}' already exists.")
        return 0
    except Exception as e:
        print(f"Failed to create database '{dbname}': {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
