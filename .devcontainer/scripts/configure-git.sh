set -euo pipefail

# First, add safe.directory for the current directory before any git commands
# This prevents "dubious ownership" errors when workspace is mounted from host
ROOT="${PWD}"
git config --global --add safe.directory "$ROOT" 2>/dev/null || true

# Now we can safely use git commands to find the repo root
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

# Add safe.directory again for the repo root (in case it's different from PWD)
if ! git config --global --get-all safe.directory 2>/dev/null | grep -qx "$ROOT"; then
  git config --global --add safe.directory "$ROOT" || true
fi

CONF="$ROOT/.devcontainer/.gitconfig.dev"

if [[ -f "$CONF" ]]; then
  # shellcheck disable=SC1090
  source "$CONF"
  strip_cr() { printf '%s' "$1" | tr -d '\r'; }
  GIT_USER_NAME="$(strip_cr "${GIT_USER_NAME:-}")"
  GIT_USER_EMAIL="$(strip_cr "${GIT_USER_EMAIL:-}")"
  GIT_REMOTE_SSH="$(strip_cr "${GIT_REMOTE_SSH:-}")"

  [[ -n "$GIT_USER_NAME"  ]] && git config --local user.name  "$GIT_USER_NAME"
  [[ -n "$GIT_USER_EMAIL" ]] && git config --local user.email "$GIT_USER_EMAIL"

  if [[ -n "$GIT_REMOTE_SSH" ]] && ! git remote get-url origin >/dev/null 2>&1; then
    git remote add origin "$GIT_REMOTE_SSH"
  fi

  echo "✅ Git configured for $ROOT"
else
  echo "ℹ️  No .devcontainer/.gitconfig.dev found. Skipping."
fi
