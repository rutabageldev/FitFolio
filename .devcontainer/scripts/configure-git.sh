# .devcontainer/scripts/configure-git.sh
#!/usr/bin/env bash
set -euo pipefail

WORKDIR="/workspaces/fitfolio"   # adjust if your workspace path differs
CONF="$WORKDIR/.devcontainer/.gitconfig.dev"

# Make sure we're in the repo
cd "$WORKDIR"

# Trust this path for “safe directory” complaints
git config --global --add safe.directory "$WORKDIR" || true

if [[ -f "$CONF" ]]; then
  # shellcheck disable=SC1090
  source "$CONF"

  # Set identity LOCALLY so it never bleeds into other repos
  [[ -n "${GIT_USER_NAME:-}"  ]] && git config --local user.name  "$GIT_USER_NAME"
  [[ -n "${GIT_USER_EMAIL:-}" ]] && git config --local user.email "$GIT_USER_EMAIL"

  # Optionally (idempotent) set remote if not present
  if [[ -n "${GIT_REMOTE_SSH:-}" ]]; then
    if git remote get-url origin >/dev/null 2>&1; then
      echo "origin already set -> $(git remote get-url origin)"
    else
      git remote add origin "$GIT_REMOTE_SSH"
      echo "origin set -> $GIT_REMOTE_SSH"
    fi
  fi

  echo "Git (local) configured for this repo."
else
  echo "No .gitconfig.dev found. Skipping local git identity."
fi
