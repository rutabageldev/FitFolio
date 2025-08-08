# .devcontainer/scripts/configure-git.sh
#!/usr/bin/env bash
set -euo pipefail

# Find the real repo root even if workspaceFolder is /app (backend subfolder)
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

CONF="$ROOT/.devcontainer/.gitconfig.dev"

# Trust this repo path for “safe directory” (global is fine; that's how Git expects it)
git config --global --add safe.directory "$ROOT" || true

if [[ -f "$CONF" ]]; then
  # shellcheck disable=SC1090
  source "$CONF"

  # Set identity for THIS repo only
  [[ -n "${GIT_USER_NAME:-}"  ]] && git config --local user.name  "$GIT_USER_NAME"
  [[ -n "${GIT_USER_EMAIL:-}" ]] && git config --local user.email "$GIT_USER_EMAIL"

  # Optionally set 'origin' once
  if [[ -n "${GIT_REMOTE_SSH:-}" ]]; then
    if git remote get-url origin >/dev/null 2>&1; then
      echo "origin already set -> $(git remote get-url origin)"
    else
      git remote add origin "$GIT_REMOTE_SSH"
      echo "origin set -> $GIT_REMOTE_SSH"
    fi
  fi

  echo "✅ Git (local) configured for this repo at $ROOT"
else
  echo "ℹ️  No .devcontainer/.gitconfig.dev found. Skipping local git identity."
fi
