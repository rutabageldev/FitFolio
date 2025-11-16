#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-https://fitfolio-staging.rutabagel.com}"
EXTENDED="${2:-false}"

echo "[smoke] Base URL: $BASE_URL"

echo "[smoke] Health check"
curl -fsS "$BASE_URL/healthz" >/dev/null

echo "[smoke] Frontend root (GET 200)"
curl -fsS "$BASE_URL/" >/dev/null

echo "[smoke] API root (GET 200)"
curl -fsS "$BASE_URL/api" >/dev/null

echo "[smoke] Auth me (GET 401)"
code="$(curl -s -o /dev/null -w "%{http_code}\n" "$BASE_URL/api/v1/auth/me")"
test "$code" = "401"

echo "[smoke] Auth me (HEAD 401)"
code="$(curl -s -I -o /dev/null -w "%{http_code}\n" "$BASE_URL/api/v1/auth/me")"
test "$code" = "401"

echo "[smoke] Header assertions (HSTS, CSP)"
curl -fsS -I "$BASE_URL/" | grep -qi "strict-transport-security"
curl -fsS -I "$BASE_URL/" | grep -qi "content-security-policy"

if [ "$EXTENDED" = "true" ]; then
  echo "[smoke] Extended: _debug mail endpoint (best-effort)"
  curl -fsS -X POST "$BASE_URL/_debug/mail?to=test@staging.local" || true
fi

echo "[smoke] OK"
