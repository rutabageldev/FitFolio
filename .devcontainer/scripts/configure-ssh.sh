set -euo pipefail

ensure_agent() {
  # Reuse existing agent if possible
  if [ -f ~/.ssh/agent.env ]; then
    # shellcheck disable=SC1090
    source ~/.ssh/agent.env >/dev/null 2>&1 || true
    if ssh-add -l >/dev/null 2>&1; then
      return 0
    else
      rm -f ~/.ssh/agent.env
    fi
  fi

  eval "$(ssh-agent -s)" >/dev/null
  {
    echo "export SSH_AUTH_SOCK=$SSH_AUTH_SOCK"
    echo "export SSH_AGENT_PID=$SSH_AGENT_PID"
  } > ~/.ssh/agent.env
  chmod 600 ~/.ssh/agent.env
}

ensure_base() {
  mkdir -p ~/.ssh
  chmod 700 ~/.ssh
  touch ~/.ssh/known_hosts
  ssh-keyscan -H github.com >> ~/.ssh/known_hosts 2>/dev/null || true

  cat > ~/.ssh/config <<'CFG'
Host github.com
  User git
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
  StrictHostKeyChecking accept-new
CFG
  chmod 600 ~/.ssh/config ~/.ssh/known_hosts
}

create_key_interactive() {
  echo "🔐 No SSH key found. Generating a new ED25519 key."
  echo "You will be prompted for a passphrase (recommended)."
  ssh-keygen -t ed25519 -C "fitfolio-devcontainer" -f ~/.ssh/id_ed25519
  chmod 600 ~/.ssh/id_ed25519 ~/.ssh/id_ed25519.pub
}

maybe_add_key_to_agent() {
  ensure_agent
  # Will prompt for passphrase once per container start if not cached
  ssh-add -l >/dev/null 2>&1 || ssh-add ~/.ssh/id_ed25519
}

print_pubkey_instructions() {
  echo "📎 Public key (add to GitHub → Settings → SSH and GPG keys):"
  echo
  cat ~/.ssh/id_ed25519.pub
  echo
}

main() {
  ensure_base

  # If flag --noninteractive is passed, create empty-pass key (not recommended)
  MODE="${1:-}"
  if [ ! -f ~/.ssh/id_ed25519 ]; then
    if [ "$MODE" = "--noninteractive" ]; then
      ssh-keygen -t ed25519 -N "" -C "fitfolio-devcontainer" -f ~/.ssh/id_ed25519
      chmod 600 ~/.ssh/id_ed25519 ~/.ssh/id_ed25519.pub
    else
      create_key_interactive
    fi
    print_pubkey_instructions
  fi

  maybe_add_key_to_agent
}

main "$@"