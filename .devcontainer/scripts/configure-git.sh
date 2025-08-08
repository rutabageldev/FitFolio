#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

CONF="$ROOT/.devcontainer/.gitconfig.dev"

git config --global --add safe.directory "$ROOT" || true

if [[ -f "$CONF" ]]; then
  source "$CONF"
  [[ -n "${GIT_USER_NAME:-}"  ]] && git config --local user.name  "$GIT_USER_NAME"
  [[ -n "${GIT_USER_EMAIL:-}" ]] && git config --local user.email "$GIT_USER_EMAIL"
  if [[ -n "${GIT_REMOTE_SSH:-}" ]] && ! git remote get-url origin >/dev/null 2>&1; then
    git remote add origin "$GIT_REMOTE_SSH"
  fi
  echo "✅ Git configured for this repo at $ROOT"
else
  echo "ℹ️  No .devcontainer/.gitconfig.dev found. Skipping."
fi
