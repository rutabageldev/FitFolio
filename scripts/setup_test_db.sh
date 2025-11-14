#!/usr/bin/env bash
set -euo pipefail

# Idempotently create the Postgres test database if it doesn't exist.
# Usage:
#   scripts/setup_test_db.sh
# Honors env vars (with sensible defaults for devcontainer/compose):
#   PGHOST=db
#   PGPORT=5432
#   PGUSER=fitfolio_user
#   PGPASSWORD=supersecret
#   TEST_DB=fitfolio_test

PGHOST="${PGHOST:-db}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-fitfolio_user}"
PGPASSWORD="${PGPASSWORD:-supersecret}"
export PGPASSWORD
TEST_DB="${TEST_DB:-fitfolio_test}"

if ! command -v psql >/dev/null 2>&1; then
  echo "psql not found. Please install the Postgres client or run inside the dev container."
  exit 1
fi

echo "Checking Postgres connectivity at ${PGUSER}@${PGHOST}:${PGPORT} ..."
psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d postgres -tc "SELECT 1;" >/dev/null

echo "Ensuring test database '${TEST_DB}' exists..."
DB_EXISTS=$(psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d postgres -tc "SELECT 1 FROM pg_database WHERE datname='${TEST_DB}';" | tr -d '[:space:]')
if [[ "${DB_EXISTS}" != "1" ]]; then
  psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d postgres -c "CREATE DATABASE ${TEST_DB};"
  echo "Created database '${TEST_DB}'."
else
  echo "Database '${TEST_DB}' already exists."
fi

echo "Done."
